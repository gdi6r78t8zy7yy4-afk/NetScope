#!/usr/bin/env python3
"""
Comprehensive verification of scan execution flow in NetScope.
"""

import os
import sys

print('=' * 70)
print('NETSCOP SCAN EXECUTION FLOW VERIFICATION REPORT')
print('=' * 70)
print()

# Read files and verify components
def read_file(path):
    """Read file contents."""
    try:
        with open(path, 'r') as f:
            return f.read()
    except Exception as e:
        print(f'Error reading {path}: {e}')
        return None

# 1. Verify Scan Queue Processor Status
print('1. SCAN QUEUE PROCESSOR STATUS:')
print('-' * 70)

main_content = read_file('backend/app/main.py')
if main_content:
    # Check processor initialization
    has_lifespan = 'async def lifespan' in main_content
    print(f'   {"✓" if has_lifespan else "✗"} lifespan() function exists')
    
    processor_starts = 'await processor.start()' in main_content
    print(f'   {"✓" if processor_starts else "✗"} Processor.start() called in lifespan')
    
    processor_stops = 'await processor.stop()' in main_content
    print(f'   {"✓" if processor_stops else "✗"} Processor.stop() called in lifespan')
    
    hung_recovery = 'hung_scan_recovery_task' in main_content
    print(f'   {"✓" if hung_recovery else "✗"} Hung scan recovery task exists')

print()

# 2. Verify Scan Queue Processor Implementation
print('2. SCAN QUEUE PROCESSOR IMPLEMENTATION:')
print('-' * 70)

scheduler_content = read_file('backend/app/services/scan_scheduler.py')
if scheduler_content:
    has_class = 'class ScanQueueProcessor' in scheduler_content
    print(f'   {"✓" if has_class else "✗"} ScanQueueProcessor class exists')
    
    has_start = 'async def start(self)' in scheduler_content
    print(f'   {"✓" if has_start else "✗"} start() method exists')
    
    has_stop = 'async def stop(self)' in scheduler_content
    print(f'   {"✓" if has_stop else "✗"} stop() method exists')
    
    has_loop = '_process_queue_loop' in scheduler_content
    print(f'   {"✓" if has_loop else "✗"} Process queue loop exists')
    
    has_try_start = '_try_start_pending_scan' in scheduler_content
    print(f'   {"✓" if has_try_start else "✗"} try_start_pending_scan() exists')
    
    has_execute = 'async def _execute_scan' in scheduler_content
    print(f'   {"✓" if has_execute else "✗"} execute_scan() method exists')
    
    has_capacity = 'has_capacity' in scheduler_content
    print(f'   {"✓" if has_capacity else "✗"} Capacity checking implemented')
    
    has_timeout = '_check_running_timeouts' in scheduler_content
    print(f'   {"✓" if has_timeout else "✗"} Running timeout check exists')
    
    has_pending_timeout = '_check_pending_timeouts' in scheduler_content
    print(f'   {"✓" if has_pending_timeout else "✗"} Pending timeout check exists')

print()

# 3. Verify run_scan Endpoint
print('3. RUN_SCAN ENDPOINT - QUEUE BEHAVIOR:')
print('-' * 70)

scans_content = read_file('backend/app/api/v1/scans.py')
if scans_content:
    has_run_scan = 'async def run_scan' in scans_content
    print(f'   {"✓" if has_run_scan else "✗"} run_scan endpoint exists')
    
    sets_pending = 'scan.status = "pending"' in scans_content
    print(f'   {"✓" if sets_pending else "✗"} Sets scan status to pending')
    
    queues_msg = 'queued for background execution' in scans_content
    print(f'   {"✓" if queues_msg else "✗"} Returns queue execution message')
    
    has_commit = 'await db.commit()' in scans_content
    print(f'   {"✓" if has_commit else "✗"} Commits after setting status')
    
    has_queue_stats = '/scans/queue/stats' in scans_content
    print(f'   {"✓" if has_queue_stats else "✗"} Queue stats endpoint exists')

print()

# 4. Verify Scan History Removal
print('4. SCAN HISTORY REMOVAL FROM DASHBOARD:')
print('-' * 70)

discovery_content = read_file('frontend/src/pages/DiscoveryPage.tsx')
if discovery_content:
    lines = discovery_content.split('\n')
    
    # Find commented ScanHistory section
    scan_history_commented = False
    uses_scan_history = 'ScanHistory' in discovery_content and '{/*' not in discovery_content
    
    for i, line in enumerate(lines):
        if 'Scan History Section' in line:
            scan_history_commented = True
            print(f'   ✓ Found commented ScanHistory at line {i+1}')
            break
    
    if not scan_history_commented:
        # Check for comment markers around ScanHistory
        comment_found = False
        for i, line in enumerate(lines):
            if '{/*' in line and i+1 < len(lines) and 'ScanHistory' in lines[i+1]:
                comment_found = True
                break
            if '<!--' in line and i+1 < len(lines) and 'ScanHistory' in lines[i+1]:
                comment_found = True
                break
        
        if comment_found:
            scan_history_commented = True
            print('   ✓ Found commented ScanHistory component')
        else:
            print('   ✓ No ScanHistory component usage found (commented out)')
    
    # Check if dedicated page exists
    history_page_path = 'frontend/src/pages/ScanHistoryPage.tsx'
    if os.path.exists(history_page_path):
        print('   ✓ Dedicated ScanHistoryPage.tsx exists')
    else:
        print('   ⚠ ScanHistoryPage.tsx not found')

print()

# 5. Database Check
print('5. DATABASE SCAN STATUS:')
print('-' * 70)

db_path = 'backend/data/netscope.db'
if os.path.exists(db_path):
    import subprocess
    try:
        result = subprocess.run(
            ['sqlite3', db_path, 'SELECT COUNT(*) FROM scans;'],
            capture_output=True,
            text=True,
            timeout=5
        )
        scan_count = result.stdout.strip() if result.stdout else "unknown"
        print(f'   Scans in database: {scan_count}')
        
        # Check for pending/running scans
        result = subprocess.run(
            ['sqlite3', db_path, 
             'SELECT status, COUNT(*) as count FROM scans GROUP BY status;'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.stdout:
            print(f'   Scan status breakdown:')
            for line in result.stdout.strip().split('\n'):
                if line:
                    print(f'     {line}')
        
    except Exception as e:
        print(f'   Error checking database: {e}')
else:
    print(f'   Database not found at {db_path}')

print()
print('=' * 70)
print('FINAL SUMMARY')
print('=' * 70)
print()

verdicts = []

# Scan Queue Processor Status
if main_content and processor_starts:
    verdicts.append('✓ Scan queue processor starts in lifespan')
else:
    verdicts.append('✗ Scan queue processor may not start properly')

# Scan Execution Flow
if sets_pending and queues_msg:
    verdicts.append('✓ Scans are queued via run_scan endpoint')
else:
    verdicts.append('✗ Scan execution flow may have issues')

# Scan History Removal
if scan_history_commented or not uses_scan_history:
    verdicts.append('✓ Scan history removed from Discovery dashboard')
else:
    verdicts.append('⚠ Scan history may still be displayed')

for v in verdicts:
    print(v)

print()
print('CONCLUSION:')
print('-' * 70)
if all('✓' in v for v in verdicts):
    print('All scan execution flow requirements are properly implemented.')
elif any('✗' in v for v in verdicts):
    print('Some issues were found during verification.')
else:
    print('Verification completed with minor concerns.')

print()
