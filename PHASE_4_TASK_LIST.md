# Phase 4: Enforce Authorized Scan Scope - Task List

## Implementation Tasks

### 1. Create Target Validator
- [ ] `backend/app/core/target_validator.py`
  - Validate IPv4/IPv6 addresses
  - Validate CIDR ranges
  - Check authorized target scope
  - Parse and normalize targets

### 2. Create Authorization Service
- [ ] `backend/app/core/authorization_service.py`
  - Load authorized targets from configuration
  - Validate targets against authorization scope
  - Support multiple target formats (single IP, CIDR, ranges)
  - Logging and audit trail

### 3. Update Scans API
- [ ] `backend/app/api/v1/scans.py`
  - Add authorization check before scan execution
  - Validate targets from scan configuration

### 4. Update Discovery API
- [ ] `backend/app/api/v1/discovery.py`
  - Add authorization check before discovery execution
  - Filter results based on authorized scope

### 5. Create Phase 4 Tests
- [ ] `backend/app/tests/test_authorization.py`
  - Test target validation
  - Test authorization checks
  - Test edge cases

## Deliverables
- All Phase 4 tests passing (target count: TBD)
- Frontend build successful
- Code review complete
