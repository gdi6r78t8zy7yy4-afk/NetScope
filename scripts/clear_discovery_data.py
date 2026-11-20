#!/usr/bin/env python3
"""
Database Cleanup Script for NetScope

Clears all false/discovery items from the network database while preserving
system configuration data.

Usage:
    python scripts/clear_discovery_data.py [--preserve-system]
    
Options:
    --preserve-system  Keep system configuration data (networks, scan configs)
"""

import asyncio
import argparse
from datetime import datetime
from textwrap import dedent

# Add backend to path
import sys
import os
backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backend')
sys.path.insert(0, backend_path)

from sqlalchemy import text

# Create async engine with correct database path
db_path = os.path.join(backend_path, 'data', 'netscope.db')
DATABASE_URL = f"sqlite+aiosqlite:///{db_path}"

from sqlalchemy.ext.asyncio import create_async_engine
engine = create_async_engine(DATABASE_URL, echo=False)

from app.models.asset import Asset, Port, HostProfile, AssetVulnerability
from app.models.network import Network, Subnet
from app.models.scan import Scan, ScanTarget, ScanEvidence


async def clear_discovery_data(preserve_system: bool = True):
    """
    Clear discovery data from the database.
    
    Args:
        preserve_system: If True, keep network and scan configuration data
    """
    print("=" * 60)
    print("NetScope Database Cleanup")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Clear tables using SQLAlchemy async
    async with engine.begin() as conn:
        print("\n[Step 1] Clearing discovery-related tables...")
        
        # Define tables to clear
        tables_to_clear = [
            'asset_vulnerabilities',
            'host_profiles', 
            'ports',
            'assets',
            'scan_targets',
            'scan_evidence',
            'scans'
        ]
        
        if preserve_system:
            # Exclude networks and subnets
            exclude_tables = ['networks', 'subnets']
            print(f"Preserving system configuration tables: {exclude_tables}")
        else:
            print("WARNING: This will clear ALL data including network configurations!")
        
        # Clear each table
        for table in tables_to_clear:
            try:
                result = await conn.execute(text(f"DELETE FROM {table}"))
                print(f"  - Cleared {table}: {result.rowcount} rows deleted")
            except Exception as e:
                print(f"  - Error clearing {table}: {e}")
        
        # If not preserving, clear networks and subnets too
        if not preserve_system:
            system_tables = ['networks', 'subnets']
            for table in system_tables:
                try:
                    result = await conn.execute(text(f"DELETE FROM {table}"))
                    print(f"  - Cleared {table}: {result.rowcount} rows deleted")
                except Exception as e:
                    print(f"  - Error clearing {table}: {e}")
    
    # Reset autoincrement counters using direct connection
    async with engine.connect() as conn:
        print("\n[Step 2] Resetting autoincrement counters...")
        
        # SQLite doesn't support ALTER SEQUENCE, use sqlite_sequence table
        sequences = [
            'assets', 'ports', 'host_profiles',
            'asset_vulnerabilities', 'scans', 'scan_targets', 'scan_evidence'
        ]
        
        for seq in sequences:
            try:
                result = await conn.execute(text(f"DELETE FROM sqlite_sequence WHERE name='{seq}'"))
                await conn.commit()
                print(f"  - Reset sequence: {seq}")
            except Exception as e:
                print(f"  - Error resetting {seq}: {e}")
    
    print("\n" + "=" * 60)
    print("Cleanup Complete!")
    print("=" * 60)
    print("\nDatabase is now in a clean state.")
    if preserve_system:
        print("System configurations (networks, subnets) have been preserved.")
    else:
        print("WARNING: All data including configurations has been cleared.")
    
    return True


async def verify_cleanup():
    """Verify that the database has been properly cleared."""
    print("\n[Verification] Checking database state...")
    
    async with engine.connect() as conn:
        tables = ['assets', 'ports', 'scans', 'networks']
        for table in tables:
            try:
                result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"  - {table}: {count} records")
            except Exception as e:
                print(f"  - Error checking {table}: {e}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Clear discovery data from NetScope database'
    )
    parser.add_argument(
        '--preserve-system',
        action='store_true',
        default=False,
        help='Preserve system configuration data (default: False)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Skip confirmation prompt'
    )
    
    args = parser.parse_args()
    
    if not args.force:
        print("\n" + "=" * 60)
        print("WARNING: This will delete all discovery data!")
        print("=" * 60)
        
        if args.preserve_system:
            print("\nSystem configurations (networks, subnets) will be PRESERVED.")
        else:
            print("\nWARNING: ALL data will be deleted including network configurations!")
        
        response = input("\nAre you sure you want to proceed? (yes/no): ")
        if response.lower() != 'yes':
            print("Cleanup cancelled.")
            return 1
    
    # Run cleanup
    try:
        asyncio.run(clear_discovery_data(preserve_system=args.preserve_system))
        
        # Verify
        asyncio.run(verify_cleanup())
        
        return 0
    except Exception as e:
        print(f"\nError during cleanup: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
