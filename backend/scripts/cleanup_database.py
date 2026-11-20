#!/usr/bin/env python3
"""
Database Cleanup Script

This script removes false positives and cleans up the database.
Use with caution - it will delete data permanently.

Usage:
    python3 scripts/cleanup_database.py --dry-run
    python3 scripts/cleanup_database.py --yes

Options:
    --dry-run: Show what would be deleted without deleting
    --yes: Actually perform the cleanup
"""

import asyncio
import sys
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

# Add parent directory to path
sys.path.insert(0, __file__.rsplit('/', 2)[0])

from app.database import get_async_session
from app.models.asset import Asset, Port, HostProfile, AssetVulnerability


async def get_asset_stats() -> dict:
    """Get statistics about assets in the database."""
    try:
        async with get_async_session() as session:
            result = await session.execute(select(Asset))
            assets = result.scalars().all()
            
            result = await session.execute(select(Port))
            ports = result.scalars().all()
            
            return {
                "total_assets": len(assets),
                "total_ports": len(ports)
            }
    except Exception:
        return {"total_assets": 0, "total_ports": 0}


async def find_false_positives() -> list:
    """
    Find potential false positives in assets.
    
    Criteria for false positives:
    - Assets with very low confidence (below 0.3)
    - Assets with suspicious patterns (localhost, reserved IPs, etc.)
    
    Returns:
        List of assets that might be false positives
    """
    try:
        async with get_async_session() as session:
            # Find assets with low confidence
            result = await session.execute(
                select(Asset).where(Asset.confidence_level == "low")
            )
            low_conf_assets = result.scalars().all()
            
            # Find assets with suspicious hostnames
            suspicious_patterns = ["localhost", "unknown", "device", "computer"]
            
            result = await session.execute(
                select(Asset).where(
                    Asset.hostname.in_(suspicious_patterns)
                )
            )
            suspicious_hostname_assets = result.scalars().all()
            
            # Combine results
            false_positives = set(low_conf_assets) | set(suspicious_hostname_assets)
            
            return list(false_positives)
    except Exception:
        return []


async def cleanup_false_positives(dry_run: bool = True) -> dict:
    """
    Cleanup false positives from the database.
    
    Args:
        dry_run: If True, show what would be deleted without deleting
        
    Returns:
        Summary of cleanup actions
    """
    print("=" * 60)
    print("DATABASE CLEANUP SCRIPT")
    print("=" * 60)
    
    # Get stats before
    before_stats = await get_asset_stats()
    print(f"\nCurrent database state:")
    print(f"  - Total assets: {before_stats.get('total_assets', 'N/A')}")
    print(f"  - Total ports: {before_stats.get('total_ports', 'N/A')}")
    
    # Find false positives
    print(f"\nSearching for false positives...")
    false_positives = await find_false_positives()
    
    print(f"  - Found {len(false_positives)} potential false positives")
    
    if not dry_run:
        print("\n" + "=" * 60)
        print("DELETING FALSE POSITIVES...")
        print("=" * 60)
        
        async with get_async_session() as session:
            for asset in false_positives:
                # First delete associated ports and host profiles
                await session.execute(
                    delete(Port).where(Port.asset_id == asset.id)
                )
                
                await session.execute(
                    delete(HostProfile).where(HostProfile.asset_id == asset.id)
                )
                
                await session.execute(
                    delete(AssetVulnerability).where(AssetVulnerability.asset_id == asset.id)
                )
                
                # Delete the asset
                await session.delete(asset)
            
            await session.commit()
        
        print(f"  - Deleted {len(false_positives)} false positive assets")
    
    # Get stats after
    if not dry_run:
        after_stats = await get_asset_stats()
        print(f"\nFinal database state:")
        print(f"  - Total assets: {after_stats.get('total_assets', 'N/A')}")
        print(f"  - Total ports: {after_stats.get('total_ports', 'N/A')}")
        
        return {
            "status": "completed",
            "assets_deleted": len(false_positives),
            "before_assets": before_stats.get('total_assets', 0),
            "after_assets": after_stats.get('total_assets', 0)
        }
    else:
        print("\n[DRY RUN] No data was deleted.")
        return {
            "status": "dry_run",
            "assets_to_delete": len(false_positives),
            "before_assets": before_stats.get('total_assets', 0)
        }


async def cleanup_absent_hosts(max_absent_days: int = 3, dry_run: bool = True) -> dict:
    """
    Cleanup hosts that have been absent for multiple scans.
    
    Args:
        max_absent_days: Number of consecutive absent scans before removal
        dry_run: If True, show what would be deleted without deleting
        
    Returns:
        Summary of cleanup actions
    """
    print("\n" + "=" * 60)
    print("CLEANUP ABSENT HOSTS")
    print("=" * 60)
    
    try:
        async with get_async_session() as session:
            from app.models.asset import Asset
            
            # Find hosts that have been absent for max_absent_days consecutive scans
            result = await session.execute(
                select(Asset).where(
                    Asset.consecutive_absent_count >= max_absent_days
                )
            )
            hosts_to_remove = result.scalars().all()
            
            print(f"\nFound {len(hosts_to_remove)} hosts absent for {max_absent_days}+ scans")
            
            if not dry_run:
                print(f"\nRemoving {len(hosts_to_remove)} absent hosts...")
                
                removed_ips = []
                for host in hosts_to_remove:
                    await session.delete(host)
                    removed_ips.append(host.ip_address)
                
                await session.commit()
                
                print(f"  - Removed {len(hosts_to_remove)} hosts")
                
                return {
                    "status": "completed",
                    "hosts_removed": len(hosts_to_remove),
                    "max_absent_days": max_absent_days
                }
            else:
                print(f"\n[DRY RUN] Would remove {len(hosts_to_remove)} hosts")
                if hosts_to_remove:
                    print("  Sample IPs:")
                    for host in hosts_to_remove[:5]:
                        print(f"    - {host.ip_address} (absent_count: {host.consecutive_absent_count})")
                
                return {
                    "status": "dry_run",
                    "hosts_to_remove": len(hosts_to_remove),
                    "max_absent_days": max_absent_days
                }
    except Exception as e:
        print(f"Error: {e}")
        return {"status": "error", "message": str(e)}


async def main():
    """Main entry point."""
    dry_run = True
    cleanup_absent = False
    max_absent_days = 3
    
    # Parse arguments
    args = sys.argv[1:] if len(sys.argv) > 1 else ["--help"]
    
    for arg in args:
        if arg == "--yes":
            dry_run = False
        elif arg == "--dry-run":
            dry_run = True
        elif arg.startswith("--max-absent="):
            try:
                max_absent_days = int(arg.split("=")[1])
                cleanup_absent = True
            except ValueError:
                print("Error: Invalid max_absent value")
                sys.exit(1)
    
    if "--help" in args or (len(sys.argv) == 1):
        print(__doc__)
        sys.exit(0)
    
    if cleanup_absent:
        result = await cleanup_absent_hosts(max_absent_days, dry_run)
    else:
        result = await cleanup_false_positives(dry_run)
    
    print(f"\nCleanup result: {result['status']}")
    return 0 if result["status"] in ["completed", "dry_run"] else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
