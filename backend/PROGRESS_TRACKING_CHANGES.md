# Scan Progress Tracking Implementation

## Summary of Changes

This document describes the implementation of scan progress tracking for the NetScope scanning system.

## Overview

The Scan model has a `progress` field (integer 0-100) that is now updated throughout the scan execution lifecycle to provide real-time progress information.

## Progress Flow

### 1. Scan Start (Progress = 10)
When a scan begins execution in `_execute_scan()`:
```python
active_scan.progress = 10
await session.commit()
```

### 2. Discovery Scans (Progress = 10-95)
During discovery scans (`active_scan.scan_type == "discovery"`):
- Calculates total hosts based on CIDR range using `ipaddress.ip_network()`
- Updates progress as hosts are discovered
- Formula: `progress = min(10 + (hosts_discovered * progress_per_host), 95)`
- `progress_per_host = 90 / total_hosts`

### 3. Port Scans (Progress = 10-95)
During port scans (`active_scan.scan_type in ["common", "port_range", "full_tcp", "single_port"]`):
- Calculates total ports based on scan type:
  - `full_tcp`: 65535 ports
  - `port_range`: Range from start to end port
  - `single_port`: Number of ports in list
  - `common`: 20 common ports
- Updates progress as ports are scanned
- Progress is updated in the scanner methods themselves

### 4. Scan Completion (Progress = 100)
When a scan completes successfully:
```python
active_scan.progress = 100
active_scan.status = "completed"
await session.commit()
```

### 5. Scan Failure (Progress = 0 or current)
When a scan fails:
- If failure during validation: `progress = 0`
- Other failures maintain current progress value

## File Changes

### app/services/scan_scheduler.py
- Updated `_execute_scan()` method to:
  - Set progress = 10 when scan starts
  - Handle discovery scans with host-based progress tracking
  - Handle port scans with port-based progress tracking
  - Set progress = 100 on successful completion
  - Handle progress updates for failed scans

### app/engines/discovery/active.py
- Updated `discover_with_nmap()` method:
  - Added optional `scan` parameter for progress tracking
  - Calculates total hosts from CIDR range
  - Updates progress after parsing discovered hosts
  - Handles edge cases where host counting fails

### app/engines/port_scanner/nmap_engine.py
- Updated `scan_ports()` method:
  - Added optional `scan` parameter for progress tracking
  - Calculates progress based on ports scanned vs total
  
- Updated `scan_port_range()` method:
  - Added optional `scan` parameter for progress tracking
  - Calculates progress based on range completion

- Updated `full_scan()` method:
  - Added optional `scan` parameter for progress tracking
  - Calculates progress based on full port range completion

- Updated `scan_single_port()` method:
  - Added optional `scan` parameter for progress tracking
  - Increases progress by 85 per port (for single port scans)

- Updated `scan_common_ports()` method:
  - Added optional `scan` parameter for progress tracking
  - Passes scan object through to underlying methods

## Database Commits

Progress updates are committed to the database after each major step:
1. After initial scan start
2. After discovery scan completes (progress 10-95)
3. After port scan completes (progress 10-95)
4. On successful completion (progress = 100)

All commits use `await session.commit()` to ensure async compatibility.

## Error Handling

- If progress calculation fails, default values are used (0 or 95)
- Database commits wrap in try-except blocks
- Progress tracking doesn't prevent scan completion/failure handling

## Testing Recommendations

1. Test discovery scans with different CIDR ranges
2. Test port scans with various port lists and ranges
3. Test scan cancellation during progress tracking
4. Verify progress values are persisted in database
