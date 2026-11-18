# Remediation Task List

## Phase 1: Repository Assessment ✅ COMPLETE
- [x] Code review completed
- [x] Database initialization fixed
- [x] IP/CIDR validators created
- [x] All documentation files created

## Phase 2: Network Discovery ✅ COMPLETE
- [x] Validate IPv4/IPv6/CIDR inputs using Python ipaddress
- [x] Implement authorized target scope validation
- [x] Fix ARP-scan invocation with actual subnet parameter
- [x] Handle macOS network interfaces correctly
- [x] Improve ARP table parsing for passive discovery
- [x] Separate passive vs active observations
- [x] Use Nmap XML output for discovery
- [x] Preserve discovery source and timestamp
- [x] Avoid duplicate assets during discovery
- [x] Handle timeouts and process termination

## Phase 3: Process Management ✅ COMPLETE
- [x] Correct timeout handling in all subprocess calls
- [x] Correct cancellation handling (await process.wait() after kill)
- [x] Terminate active processes on asyncio task cancellation
- [x] Avoid orphaned processes (ensure cleanup)
- [x] Capture stdout and stderr properly
- [x] Return structured errors for subprocess failures
- [x] Handle missing executables gracefully
- [x] Handle non-zero exit codes properly

### Phase 3 Implementation Details:
**Created Files:**
- `backend/app/core/process_manager.py` - ProcessManager class with comprehensive process lifecycle management

**Modified Files:**
- `backend/app/engines/port_scanner/nmap_engine.py` - Updated to use ProcessManager/run_command
- `backend/app/engines/discovery/active.py` - Updated to use ProcessManager/run_command
- `backend/app/engines/discovery/passive.py` - Updated to use ProcessManager/run_command

**Test Coverage:**
- Added `backend/app/tests/test_process_manager.py` with 27 comprehensive tests
- All test categories covered: success, timeout, cancellation, errors, concurrent execution
- All 109 tests passing

**Key Features:**
1. Timeout handling with proper process termination
2. Cancellation handling (process.kill() + await process.wait())
3. Process cleanup in finally blocks
4. Structured error reporting with detailed information
5. FileNotFoundError handling at process creation time
6. Concurrent execution support

## Phase 4: Enforce Authorized Scan Scope ✅ COMPLETE
- [x] Create shared target authorization service
- [x] Integrate validation into scanning flow
- [x] Validate every target before scan execution


### Phase 4 Implementation Details:
**Created Files:**
- `backend/app/core/target_validator.py` - Target validation for IPv4/IPv6/CIDR ranges
- `backend/app/core/authorization_service.py` - Authorization service with config loading and audit logging

**Modified Files:**
- `backend/app/api/v1/scans.py` - Added authorization checks in run_scan endpoint
- `backend/app/api/v1/discovery.py` - Added authorization checks in active_discovery endpoint

**Test Coverage:**
- Added `backend/app/tests/test_authorization.py` with 40 comprehensive tests
- All test categories covered: IPv4/IPv6/CIDR validation, authorization checks, singleton patterns, edge cases
- All 149 tests passing

**Key Features:**
1. IPv4/IPv6/CIDR validation with private/public IP classification
2. Network subnet and overlap detection
3. Load scopes from environment variable (NETSCOPE_AUTHORIZED_TARGETS)
4. Load scopes from config file (authorized_scopes.json)
5. Audit logging for authorization decisions
6. Strict mode support

**Production-Grade Features:**
1. Singleton pattern for consistent configuration
2. HTTP 403 responses with clear error messages
3. Early rejection of unauthorized targets before expensive operations
4. Structured logging with audit trail

## Phase 5: Consolidate Nmap Integration ✅ COMPLETE
- [x] All scans use structured XML output (`-oX -`)
- [x] Parse results using existing parser (`parse_nmap_xml`)
- [x] Preserve raw XML as scan evidence

## Phase 6: Vulnerability Intelligence ⏳ PENDING
- [ ] CISA KEV real JSON feed integration
- [ ] NVD CVE API 2.0 with pagination
- [ ] FIRST EPSS integration

## Phase 7: Vulnerability Correlation ⏳ PENDING
- [ ] Replace substring matching with CPE-based correlation
- [ ] Support version boundary comparisons

## Phase 8: Database Corrections ⏳ PENDING
- [ ] Add proper relationships and foreign keys
- [ ] Alembic migrations

## Phase 9: Tauri and macOS ⏳ PENDING
- [ ] Update tauri.conf.json for version 2
- [ ] Fix Cargo.toml dependencies
- [ ] Backend lifecycle management

## Phase 10: Security Corrections ⏳ PENDING
- [ ] Fix CORS configuration
- [ ] Localhost-only binding
- [ ] Subprocess argument sanitization

## Phase 11: Frontend Data Integrity ⏳ PENDING
- [ ] Replace hardcoded dashboard statistics with API calls

## Phase 12: Documentation ⏳ PENDING
- [ ] Update all documentation files
