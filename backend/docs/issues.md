# NetScope Backend Issues Log

**Generated:** November 18, 2026  
**Total Issues:** 20

---

## Critical (Immediate Action Required)

| ID | Severity | Category | Description | File | Status |
|----|----------|----------|-------------|------|--------|
| ISS-001 | CRITICAL | Security | Missing CVE ID validation in `/app/core/validators.py` | `app/core/validators.py:232-321` | Open |
| ISS-002 | CRITICAL | Security | No input sanitization on IP addresses in API endpoints | `app/api/v1/scans.py:253` | Open |
| ISS-003 | CRITICAL | Database | Missing foreign key constraints on association tables | `app/models/scan.py:44-62` | Open |
| ISS-004 | CRITICAL | API | No API version negotiation mechanism (Accept-Version, deprecation headers) | `app/api/__init__.py:12` | Open |
| ISS-005 | CRITICAL | Missing | No vulnerability CRUD endpoints (POST, PUT, DELETE for vulnerabilities) | `app/api/v1/vulnerabilities.py:33-202` | Open |

### Critical Issue Details

#### ISS-001: CVE ID Validation Missing
**Severity:** CRITICAL  
**File:** `app/core/validators.py:232-321`

```python
# Current code does not validate CVE IDs before database queries
@router.get("/vulnerabilities/{cve_id}")
async def get_vulnerability(cve_id: str, db: AsyncSession = Depends(get_async_session)):
    # No input validation on cve_id - potential injection vector
```

**Impact:** Potential SQL injection attacks through CVE ID parameter  
**Fix Required:**
```python
def validate_cve_id(cve_id: str) -> Tuple[bool, str]:
    """Validate CVE ID format."""
    import re
    pattern = r'^CVE-(1999|20\d{2})-\d{4,}$'
    if not re.match(pattern, cve_id):
        return False, f"Invalid CVE ID format: {cve_id}"
    return True, "Valid"
```

---

#### ISS-002: IP Address Input Sanitization Missing
**Severity:** CRITICAL  
**File:** `app/api/v1/scans.py:253`

```python
# Current code accepts CIDR without sanitization
validation_result = auth_service.validate_target(scan.target_cidr)
```

**Impact:** Potential command injection or bypass of network restrictions  
**Fix Required:**
```python
def sanitize_cidr(cidr: str) -> str:
    """Sanitize and validate CIDR input."""
    cidr = cidr.strip()
    
    # Reject malformed inputs
    if not re.match(r'^[0-9a-fA-F.:]+/\d{1,3}$', cidr):
        raise ValueError("Invalid CIDR format")
    
    # Normalize using ipaddress module
    network = ipaddress.ip_network(cidr, strict=False)
    return str(network)
```

---

#### ISS-003: Missing Foreign Key Constraints
**Severity:** CRITICAL  
**File:** `app/models/scan.py:44-62`

```python
class ScanTarget(Base):
    __tablename__ = "scan_targets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ip_address = Column(String(45), nullable=False, index=True)
    hostname = Column(String(255), nullable=True)
    # MISSING: scan_id foreign key
```

**Impact:** Data integrity issues, orphaned records, potential security vulnerabilities  
**Fix Required:**
```python
class ScanTarget(Base):
    __tablename__ = "scan_targets"
    
    scan_id = Column(Integer, ForeignKey("scans.id", ondelete="CASCADE"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True)
```

---

#### ISS-004: No API Version Negotiation
**Severity:** CRITICAL  
**File:** `app/api/__init__.py:12`

```python
# Hardcoded version in multiple places
router = APIRouter(prefix="/api/v1", tags=["v1"])
```

**Impact:** Cannot safely evolve API without breaking clients  
**Fix Required:**
```python
# Add version negotiation middleware
async def get_api_version(request: Request) -> str:
    # Check URL path, query param, or header
    if "v2" in request.url.path:
        return "v2"
    return request.query_params.get("api_version", "v1")
```

---

#### ISS-005: Missing Vulnerability CRUD
**Severity:** CRITICAL  
**File:** `app/api/v1/vulnerabilities.py:33-202`

```python
# Current implementation only supports read operations
@router.get("/vulnerabilities/{cve_id}")
async def get_vulnerability(...):
    # No POST, PUT, DELETE endpoints
```

**Impact:** Users cannot manually manage vulnerability database entries  
**Fix Required:**
```python
@router.post("/vulnerabilities", status_code=201)
async def create_vulnerability(vuln: VulnerabilityCreate):
    # Add vulnerability creation endpoint
```

---

## High (Address in Current Sprint)

| ID | Severity | Category | Description | File | Status |
|----|----------|----------|-------------|------|--------|
| ISS-006 | HIGH | API | Inconsistent endpoint naming (asset_id vs ip_address) | `app/api/v1/assets.py:51,81` | Open |
| ISS-007 | HIGH | Discovery | Missing SNMP discovery support | `app/engines/discovery/` | Open |
| ISS-008 | HIGH | Database | N+1 query issues in intelligence correlate endpoint | `app/api/v1/intelligence.py:376-400` | Open |
| ISS-009 | HIGH | Validation | Incomplete port range validation (no DoS protection) | `app/core/validators.py:232-321` | Open |
| ISS-010 | HIGH | Missing | No bulk operations for assets/vulnerabilities | Multiple files | Open |

### High Issue Details

#### ISS-006: Inconsistent Endpoint Naming
**Severity:** HIGH  
**File:** `app/api/v1/assets.py:51,81`

```python
# Inconsistent ID parameter naming
@router.get("/assets/{asset_id}")        # Integer ID
async def get_asset(asset_id: int, ...):

@router.get("/assets/{ip_address}")      # String IP address
async def get_asset_by_ip(ip_address: str, ...):
```

**Impact:** API confusion, inconsistent documentation  
**Fix Required:**
```python
# Standardize on /resources/{id}
@router.get("/assets/{asset_id}")       # Keep integer ID
@router.get("/assets/ip/{ip_address}")  # Use descriptive path for IP lookup
```

---

#### ISS-007: Missing SNMP Discovery
**Severity:** HIGH  
**File:** `app/engines/discovery/`

```python
# Only Nmap and ARP scan are available
class ActiveDiscoveryEngine:
    # No SNMP support
```

**Impact:** Cannot discover devices that don't respond to ICMP/ARP  
**Fix Required:**
```python
from pysnmp.hlapi import *

class SNMPDiscoveryEngine:
    async def discover_with_snmp(self, target: str, community: str):
        # Implement SNMP discovery
```

---

#### ISS-008: N+1 Query Issues
**Severity:** HIGH  
**File:** `app/api/v1/intelligence.py:376-400`

```python
# Loads all vulnerabilities without pagination
vuln_result = await db.execute(select(Vulnerability))
vulnerabilities = list(vuln_result.scalars().all())
```

**Impact:** Memory exhaustion with large vulnerability databases  
**Fix Required:**
```python
@router.get("/vulnerabilities")
async def list_vulnerabilities(skip: int = 0, limit: int = 100):
    result = await db.execute(
        select(Vulnerability).offset(skip).limit(limit)
    )
    return list(result.scalars().all())
```

---

#### ISS-009: Incomplete Port Range Validation
**Severity:** HIGH  
**File:** `app/core/validators.py:232-321`

```python
# Current validation allows any port range without DoS protection
if (end - start + 1) > 65535:
    return False, [], "Port range too large"
# But no limit on consecutive port scans
```

**Impact:** Potential DoS attacks through port scan enumeration  
**Fix Required:**
```python
def validate_port_range_safe(start: int, end: int) -> Tuple[bool, str]:
    """Safe port range validation with DoS protection."""
    # Limit single scan to 10,000 ports
    if (end - start + 1) > 10_000:
        return False, "Port range too large (max 10000 ports)"
    return True, "Valid"
```

---

#### ISS-010: Missing Bulk Operations
**Severity:** HIGH  
**File:** Multiple files

```python
# No bulk endpoints for efficient operations
POST /api/v1/assets/bulk        # Missing
PUT /api/v1/assets/bulk         # Missing  
DELETE /api/v1/assets/bulk      # Missing
```

**Impact:** Inefficient bulk asset management operations  
**Fix Required:**
```python
@router.post("/assets/bulk")
async def bulk_create_assets(assets: List[AssetCreate]):
    # Implement bulk asset creation
```

---

## Medium (Schedule for Next Sprint)

| ID | Severity | Category | Description | File | Status |
|----|----------|----------|-------------|------|--------|
| ISS-011 | MEDIUM | Database | Missing indexes for common queries | `app/models/` | Open |
| ISS-012 | MEDIUM | API | No deprecation headers on endpoints | `app/api/v1/` | Open |
| ISS-013 | MEDIUM | Discovery | Limited passive discovery methods (LLMNR, mDNS) | `app/engines/discovery/passive.py` | Open |
| ISS-014 | MEDIUM | Error Handling | Inconsistent error response format | Multiple files | Open |
| ISS-015 | MEDIUM | Validation | Missing IPv6 validation | `app/core/validators.py` | Open |

---

## Low (Technical Debt)

| ID | Severity | Category | Description | File | Status |
|----|----------|----------|-------------|------|--------|
| ISS-016 | LOW | Code Quality | Hardcoded API version strings in multiple places | `app/api/v1/` | Open |
| ISS-017 | LOW | Documentation | Missing docstrings for some Pydantic models | `app/schemas/` | Open |
| ISS-018 | LOW | Testing | Missing unit tests for validators | `app/core/validators.py` | Open |
| ISS-019 | LOW | Performance | No pagination on list endpoints (defaults to unlimited) | `app/api/v1/` | Open |
| ISS-020 | LOW | Code Quality | Duplicate error handling code across endpoints | Multiple files | Open |

---

## Issue Priority Matrix

```
┌─────────────────┬──────────────┬──────────────┐
│    Severity     │  Timeline    │  Effort      │
├─────────────────┼──────────────┼──────────────┤
│  CRITICAL       │  Immediate   │  Low-Medium  │
│  HIGH           │  Sprint 1    │  Medium      │
│  MEDIUM         │  Sprint 2    │  Low-Medium  │
│  LOW            │  Backlog     │  Low         │
└─────────────────┴──────────────┴──────────────┘
```

## Issue Resolution Checklist

### Critical Issues
- [ ] ISS-001: Implement CVE ID validation
- [ ] ISS-002: Add IP address input sanitization  
- [ ] ISS-003: Add foreign key constraints
- [ ] ISS-004: Implement API version negotiation
- [ ] ISS-005: Create vulnerability CRUD endpoints

### High Priority Issues
- [ ] ISS-006: Standardize endpoint naming conventions
- [ ] ISS-007: Implement SNMP discovery engine
- [ ] ISS-008: Fix N+1 query issues with pagination
- [ ] ISS-009: Add port range DoS protection
- [ ] ISS-010: Implement bulk operations

### Medium Priority Issues
- [ ] ISS-011: Add database indexes
- [ ] ISS-012: Add deprecation headers
- [ ] ISS-013: Implement enhanced passive discovery
- [ ] ISS-014: Standardize error responses
- [ ] ISS-015: Add IPv6 validation

### Low Priority Issues
- [ ] ISS-016: Externalize API version configuration
- [ ] ISS-017: Add missing docstrings
- [ ] ISS-018: Write validator unit tests
- [ ] ISS-019: Add pagination to all list endpoints
- [ ] ISS-020: Refactor duplicate error handling

---

*Issue log for NetScope API v1 codebase*
