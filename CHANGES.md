# Vulnerability Intelligence Sync Fixes

## Summary of Changes

This document describes the changes made to fix the vulnerability intelligence sync logic in NetScope.

## Issues Fixed

### 1. Missing `/api/v1/intelligence/sync` Endpoint
- **Problem**: The frontend was trying to call `/api/v1/intelligence/sync` but the endpoint didn't exist in intelligence.py
- **Solution**: Added a unified `/api/v1/intelligence/sync` endpoint that calls `sync_to_database()` to properly persist CVE/KEV/EPSS data

### 2. Startup Sync Not Implemented
- **Problem**: Vulnerabilities were not being synced on application startup when the database was empty
- **Solution**: Added startup hook in `main.py` that:
  - Starts the IntelligenceSyncWorker (24-hour interval)
  - Checks if vulnerabilities exist in database
  - Triggers initial sync if no vulns found

### 3. Database Disposal Issue
- **Problem**: The lifespan function was trying to call `engine.dispose()` but `engine` was shadowed by the IntelligenceSync object
- **Solution**: Created proper database engine disposal in `database/__init__.py` with `get_sync_engine()` and fixed lifespan to use it correctly

### 4. IntelligenceSync Endpoint Usage
- **Problem**: The `/api/v1/intelligence/sync` endpoint was calling `sync_all()` instead of `sync_to_database()`
- **Solution**: Updated `/api/v1/intelligence/sync` endpoint to properly call `sync_to_database(db)` which persists data to the database

### 5. Frontend Integration
- **Problem**: VulnerabilitiesPage.tsx was fetching from `/api/v1/vulnerabilities` without triggering intelligence sync
- **Solution**: Updated VulnerabilitiesPage.tsx to:
  - Check `/api/v1/intelligence/status` on load
  - Show sync status badge
  - Add "Sync Intelligence Data" button when no vulns exist
  - Call `/api/v1/intelligence/sync` with sources parameter

## Files Modified

### Backend Changes

1. **backend/app/main.py**
   - Fixed lifespan function to properly initialize and dispose database engine
   - Added startup hook for initial vulnerability sync if database is empty
   - Added IntelligenceSyncWorker startup with 24-hour interval

2. **backend/app/database/__init__.py**
   - Added `get_sync_engine()` function for proper engine disposal
   - Renamed internal engine variable to avoid conflicts

3. **backend/app/api/v1/intelligence.py**
   - Added `/api/v1/intelligence/sync` endpoint that calls `sync_to_database()`
   - Added sources query parameter for selective sync
   - Fixed missing endpoint to properly integrate with database

4. **backend/app/api/v1/vulnerabilities.py**
   - Updated `/api/v1/intelligence/sync` to use `sync_to_database(db)` instead of `sync_all()`
   - Properly passes database session for persistence

### Frontend Changes

5. **frontend/src/pages/VulnerabilitiesPage.tsx**
   - Added sync status badge showing sync progress
   - Added "Sync Intelligence Data" button when no vulnerabilities exist
   - Added `/api/v1/intelligence/status` check on load
   - Added `/api/v1/intelligence/sync` trigger with POST request
   - Added KEV and EPSS stats cards

## API Endpoints Added/Modified

### `/api/v1/intelligence/sync` (POST)
- Triggers full intelligence synchronization
- Calls `sync_to_database()` to persist data
- Accepts optional `sources` query parameter (default: ["all"])
- Sources: cisa_kev, nvd_cve, epss

### `/api/v1/intelligence/status` (GET)
- Returns intelligence sync status
- Shows last sync time and status for each source

### `/api/v1/intelligence/sync/cves` (POST)
- Syncs CVE data from NVD
- Calls `sync_nvd()` endpoint

### `/api/v1/intelligence/sync/kev` (POST)
- Syncs CISA KEV catalog
- Calls `sync_cisa_kev()` endpoint

### `/api/v1/intelligence/sync/epss` (POST)
- Syncs EPSS scores
- Calls `sync_epss()` endpoint

## Test Results

All 238 tests pass:
```
====================== 238 passed, 27 warnings in 11.72s =======================
```

Frontend builds successfully:
```
✓ built in 222ms
dist/index.html                   0.50 kB │ gzip:  0.33 kB
dist/assets/index-mdWqMGUZ.css   21.83 kB │ gzip:  5.01 kB
dist/assets/index-BOsrjdA5.js   253.40 kB │ gzip:  74.53 kB
```

## Verification Steps

1. **Clear database and trigger sync**:
```bash
python3 -c "from app.database import engine; from sqlalchemy import text; conn.execute(text('DELETE FROM vulnerabilities')); conn.commit()"
curl -X POST http://localhost:8000/api/v1/intelligence/sync
```

2. **Check vulns count**:
```bash
python3 -c "from app.database import engine; from sqlalchemy import text; result = conn.execute(text('SELECT COUNT(*) FROM vulnerabilities')); print(result.scalar())"
```

3. **Check KEV records**:
```bash
python3 -c "from app.database import engine; from sqlalchemy import text; result = conn.execute(text('SELECT COUNT(*) FROM vulnerability_kev')); print(result.scalar())"
```

4. **Check EPSS records**:
```bash
python3 -c "from app.database import engine; from sqlalchemy import text; result = conn.execute(text('SELECT COUNT(*) FROM vulnerability_epss_history')); print(result.scalar())"
```

## Scheduled Sync

The IntelligenceSyncWorker is configured to run every 24 hours (86400 seconds) and:
- Syncs all vulnerability intelligence sources
- Persists data to database via `sync_to_database()`
- Emits completion events via WebSocket

## Next Steps for Production

1. Ensure external APIs (NVD, CISA, EPSS) are accessible
2. Set up API keys in environment variables if needed
3. Configure Celery for production use (currently uses background worker)
4. Set up database migrations with Alembic
5. Add rate limiting for external API calls
