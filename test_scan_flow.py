#!/usr/bin/env python3
"""
Test script to verify scan execution flow.
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.database import engine, init_db
from sqlalchemy import select, update
from app.models.scan import Scan

async def test_scan_flow():
    print("=" * 60)
    print("SCAN EXECUTION FLOW VERIFICATION")
    print("=" * 60)
    
    # Initialize database
    await init_db()
    print("\n✓ Database initialized")
    
    # Create a test scan
    from app.database import get_async_session
    
    async for session in get_async_session():
        try:
            # Check if there are any scans
            result = await session.execute(select(Scan))
            existing_scans = list(result.scalars().all())
            
            print(f"\nExisting scans in database: {len(existing_scans)}")
            
            if len(existing_scans) == 0:
                # Create a test scan
                print("\n--- Creating Test Scan ---")
                test_scan = Scan(
                    name="Test Discovery Scan",
                    scan_type="discovery",
                    target_cidr="192.168.1.0/30",  # Small network for testing
                    rate_limit="medium"
                )
                session.add(test_scan)
                await session.commit()
                await session.refresh(test_scan)
                
                print(f"✓ Created scan ID {test_scan.id}")
                print(f"  Name: {test_scan.name}")
                print(f"  Type: {test_scan.scan_type}")
                print(f"  Target: {test_scan.target_cidr}")
                print(f"  Status: {test_scan.status}")
            
            # Get the scan (either existing or newly created)
            result = await session.execute(select(Scan))
            scans = list(result.scalars().all())
            
            print("\n--- Current Scans in Database ---")
            for scan in scans:
                print(f"  Scan ID {scan.id}:")
                print(f"    Name: {scan.name}")
                print(f"    Type: {scan.scan_type}")
                print(f"    Status: {scan.status}")
                print(f"    Target: {scan.target_cidr}")
                print(f"    Created: {scan.created_at}")
                print(f"    Started: {scan.started_at}")
                print(f"    Completed: {scan.completed_at}")
                print(f"    Hosts Found: {scan.hosts_found}")
            
            # Check scan queue processor status
            print("\n--- Queue Processor Status ---")
            from app.services.scan_scheduler import processor
            
            stats = processor.get_queue_stats()
            print(f"  Max Concurrent Scans: {stats['max_concurrent_scans']}")
            print(f"  Running: {stats['running']}")
            print(f"  Pending: {stats['pending']}")
            
            # Check database for pending/running scans
            result = await session.execute(select(Scan).where(Scan.status == "pending"))
            pending_scans = list(result.scalars().all())
            
            result = await session.execute(select(Scan).where(Scan.status == "running"))
            running_scans = list(result.scalars().all())
            
            result = await session.execute(select(Scan).where(Scan.status == "completed"))
            completed_scans = list(result.scalars().all())
            
            print(f"  Pending scans in DB: {len(pending_scans)}")
            print(f"  Running scans in DB: {len(running_scans)}")
            print(f"  Completed scans in DB: {len(completed_scans)}")
            
            # Test running a scan
            if len(scans) > 0:
                test_scan = scans[0]
                print(f"\n--- Testing Scan Execution for ID {test_scan.id} ---")
                
                # Update scan status to pending (simulating run_scan endpoint)
                stmt = (
                    update(Scan)
                    .where(Scan.id == test_scan.id)
                    .values(status="pending")
                )
                await session.execute(stmt)
                await session.commit()
                
                print(f"✓ Set scan {test_scan.id} to pending status")
                
                # Now simulate what the processor does
                from app.services.scan_scheduler import ScanQueueProcessor
                
                processor = ScanQueueProcessor()
                
                print(f"Max concurrent scans setting: {processor.max_concurrent_scans}")
                
                # Check if scan would be picked up
                result = await session.execute(select(Scan).where(Scan.status == "pending"))
                pending_scans = list(result.scalars().all())
                result = await session.execute(select(Scan).where(Scan.status == "running"))
                running_scans = list(result.scalars().all())
                
                has_capacity = len(running_scans) < processor.max_concurrent_scans
                print(f"Has capacity to run scans: {has_capacity}")
                print(f"Pending scans available: {len(pending_scans)}")
                
                if has_capacity and pending_scans:
                    print("✓ Scan WOULD be picked up by processor")
                else:
                    print("✗ Scan would NOT be picked up by processor")
                    if not has_capacity:
                        print(f"  Reason: Max concurrent scans reached ({len(running_scans)}/{processor.max_concurrent_scans})")
                    if not pending_scans:
                        print("  Reason: No pending scans")
            
            break
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            break
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_scan_flow())
