# NetScope Backend API Recommendations

**Date:** November 18, 2026  
**Author:** Code Analysis Agent

---

## Executive Summary

This document provides detailed recommendations for improving the NetScope backend API based on comprehensive code analysis. The recommendations are prioritized by criticality and include implementation details, file references, and estimated effort.

---

## 1. Security Recommendations

### 1.1 Input Validation Enhancement

**Current State:**
```python
# app/core/validators.py
def validate_cidr(cidr: str) -> bool:
    try:
        ipaddress.ip_network(cidr, strict=False)
        return True
    except (ValueError, TypeError):
        return False
```

**Issues:**
- No CIDR validation that network address matches provided IP
- No broadcast address calculation exposed
- No input sanitization before database queries

**Recommendations:**

1. **Add CVE ID Validation**
```python
# app/core/validators.py

def validate_cve_id(cve_id: str) -> Tuple[bool, str]:
    """Validate CVE ID format."""
    import re
    pattern = r'^CVE-(1999|20\d{2})-\d{4,}$'
    if not re.match(pattern, cve_id):
        return False, f"Invalid CVE ID format: {cve_id}"
    return True, "Valid"

def sanitize_cve_id(cve_id: str) -> str:
    """Sanitize CVE ID for database queries."""
    valid, message = validate_cve_id(cve_id)
    if not valid:
        raise ValueError(message)
    return cve_id
```

2. **Add IP Address Sanitization**
```python
def sanitize_cidr(cidr: str) -> Tuple[str, Dict]:
    """Sanitize and validate CIDR input."""
    import re
    
    # Remove whitespace
    cidr = cidr.strip()
    
    # Reject malformed inputs
    if not re.match(r'^[0-9a-fA-F.:]+/\d{1,3}$', cidr):
        raise ValueError("Invalid CIDR format")
    
    # Normalize using ipaddress module
    network = ipaddress.ip_network(cidr, strict=False)
    
    # Return normalized CIDR and additional info
    return str(network), {
        "network_address": str(network.network_address),
        "broadcast_address": str(network.broadcast_address),
        "usable_hosts": network.num_addresses - 2 if network.prefixlen < 31 else 0
    }
```

**Files to Modify:**
- `app/core/validators.py` (add functions)
- `app/api/v1/scans.py` (update input handling)

**Effort:** 4 hours  
**Risk:** Low

---

### 1.2 Error Response Standardization

**Current State:**
```python
# Inconsistent error formats across endpoints
raise HTTPException(status_code=403, detail=f"Target not authorized: {reason}")
raise HTTPException(status_code=404, detail="Asset not found")
raise HTTPException(status_code=500, detail=str(e))
```

**Recommendation:**
```python
# app/core/errors.py (NEW FILE)

from fastapi import Request, status
from pydantic import BaseModel
from datetime import datetime

class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[dict] = None
    code: str
    timestamp: datetime

class AppError(Exception):
    def __init__(self, message: str, code: str = "APP_ERROR", details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}

# Custom exception handler
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.code,
            "message": exc.message,
            "details": exc.details,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# Register in main app
app.add_exception_handler(AppError, app_error_handler)
```

**Files to Modify:**
- `app/core/errors.py` (new file)
- `app/main.py` (register exception handler)

**Effort:** 6 hours  
**Risk:** Medium

---

## 2. API Improvements

### 2.1 Endpoint Naming Standardization

**Current Issues:**
```python
# Inconsistent parameter naming
GET /assets/{asset_id}        # Integer ID
GET /assets/{ip_address}      # String IP address

# Verbs in paths
POST /scans/{scan_id}/cancel
POST /scans/{scan_id}/run
```

**Recommendation:**

```python
# Standardize endpoint patterns

# 1. Resource endpoints use resource name singular
GET /api/v1/asset/{id}         # Use 'id' for integer IDs
GET /api/v1/assets/ip/{ip}     # Use descriptive path for IP lookups

# 2. Use nouns, not verbs
POST /api/v1/scans/{id}/cancellations   # Instead of /cancel
POST /api/v1/scans/{id}/executions      # Instead of /run

# 3. Batch operations
POST /api/v1/assets/bulk               # Bulk asset creation
PUT /api/v1/assets/bulk                # Bulk update
DELETE /api/v1/assets/bulk             # Bulk deletion
```

**Files to Modify:**
- `app/api/v1/assets.py`
- `app/api/v1/scans.py`

**Effort:** 8 hours  
**Risk:** Medium (breaking changes)

---

### 2.2 API Versioning Implementation

**Current State:**
```python
# Hardcoded version strings in multiple places
router = APIRouter(prefix="/api/v1", tags=["v1"])
```

**Recommendation:**

```python
# app/api/__init__.py (NEW FILE)

from fastapi import Request, Depends

API_VERSIONS = {
    "v1": {"path": "/api/v1", "status": "stable"},
    "v2": {"path": "/api/v2", "status": "alpha"}  # Future version
}

def get_api_version(request: Request) -> str:
    """Determine API version from multiple sources."""
    # 1. URL path: /api/v1/...
    if "/v2/" in request.url.path:
        return "v2"
    
    # 2. Query param: ?api_version=v1
    if "api_version" in request.query_params:
        return request.query_params["api_version"]
    
    # 3. Header: X-API-Version: v1
    if "X-API-Version" in request.headers:
        return request.headers["X-API-Version"]
    
    # 4. Default to v1
    return "v1"

# Deprecation middleware
async def deprecation_header_middleware(request: Request, call_next):
    response = await call_next(request)
    
    # Add deprecation headers for v1
    if "v2" in API_VERSIONS and request.url.path.startswith("/api/v1"):
        response.headers["Deprecation"] = "true"
        response.headers["Sunset"] = "2025-12-31T23:59:59Z"
    
    return response
```

**Files to Modify:**
- `app/api/__init__.py` (new file)
- `app/main.py` (register middleware)

**Effort:** 8 hours  
**Risk:** Low

---

## 3. Database Improvements

### 3.1 Foreign Key Constraints

**Current Issues:**
```python
# app/models/scan.py - Missing foreign keys
class ScanTarget(Base):
    __tablename__ = "scan_targets"
    
    id = Column(Integer, primary_key=True)
    ip_address = Column(String(45), nullable=False)
    # MISSING: scan_id foreign key
```

**Recommendation:**

```python
# app/models/scan.py

class ScanTarget(Base):
    __tablename__ = "scan_targets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ip_address = Column(String(45), nullable=False, index=True)
    hostname = Column(String(255), nullable=True)
    
    # Foreign keys with cascade options
    scan_id = Column(Integer, ForeignKey("scans.id", ondelete="CASCADE"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    scan = relationship("Scan", back_populates="targets")
    asset = relationship("Asset", backref="scan_targets")

class Scan(Base):
    __tablename__ = "scans"
    
    id = Column(Integer, primary_key=True)
    
    # Relationships
    targets = relationship("ScanTarget", back_populates="scan")
    evidence = relationship("ScanEvidence", backref="scan")

# app/models/asset.py
class Asset(Base):
    __tablename__ = "assets"
    
    # Relationships
    scan_targets = relationship("ScanTarget", back_populates="asset")
```

**Files to Modify:**
- `app/models/scan.py`
- `app/models/asset.py`

**Effort:** 8 hours  
**Risk:** Medium (requires data migration)

---

### 3.2 Database Indexes

**Recommendation:**

```python
# app/models/__init__.py (add to model definitions)

from sqlalchemy import Index

class Asset(Base):
    __tablename__ = "assets"
    
    # ... existing columns ...
    
    __table_args__ = (
        Index('idx_asset_ip_created', 'ip_address', 'created_at'),
        Index('idx_asset_mac', 'mac_address'),
    )

class Scan(Base):
    __tablename__ = "scans"
    
    # ... existing columns ...
    
    __table_args__ = (
        Index('idx_scan_status_target', 'status', 'target_cidr'),
        Index('idx_scan_created', 'created_at'),
    )

class Vulnerability(Base):
    __tablename__ = "vulnerabilities"
    
    # ... existing columns ...
    
    __table_args__ = (
        Index('idx_vuln_cve_severity', 'cve_id', 'severity'),
        Index('idx_vuln_kev', 'is_kev'),
    )

class AssetHistory(Base):
    __tablename__ = "asset_history"
    
    # ... existing columns ...
    
    __table_args__ = (
        Index('idx_history_asset_type', 'asset_id', 'change_type'),
    )
```

**Files to Modify:**
- `app/models/asset.py`
- `app/models/scan.py`
- `app/models/vulnerability.py`
- `app/models/asset_history.py`

**Effort:** 4 hours  
**Risk:** Low

---

### 3.3 Connection Pooling

**Current State:**
```python
engine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
)
```

**Recommendation:**

```python
# app/database/__init__.py

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import QueuePool

# Async-safe connection pool
engine = create_async_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=20,           # Increased for async
    max_overflow=40,
    pool_timeout=30,
    pool_recycle=1800,      # 30 minutes
    pool_pre_ping=True,     # Validate connections
    echo_pool="debug" if settings.debug else False,
)

# Add connection pool monitoring
from sqlalchemy import event

@event.listens_for(engine.sync_engine, "checkout")
def on_checkout(dbapi_conn, conn_record, pool):
    if pool.checkedout() > 25:
        logger.warning("Connection pool near capacity", active=pool.checkedout())
```

**Files to Modify:**
- `app/database/__init__.py`

**Effort:** 4 hours  
**Risk:** Low

---

## 4. Discovery Engine Enhancements

### 4.1 SNMP Discovery Implementation

**Recommendation:**

```python
# app/engines/discovery/snmp.py (NEW FILE)

from pysnmp.hlapi import *
import asyncio

class SNMPDiscoveryEngine:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.logger = structlog.get_logger(__name__)
    
    async def discover_with_snmp(self, target: str, community: str) -> List[Dict]:
        """Discover hosts via SNMP polling."""
        engine = SnmpEngine()
        
        target = UdpTransportTarget((target, 161), timeout=self.timeout)
        
        error_indication, error_status, _, var_binds = next(
            getCmd(
                engine,
                CommunityData(community),
                target,
                ContextData(),
                ObjectType(ObjectIdentity('1.3.6.1.2.1.1.5')),  # sysName
                ObjectType(ObjectIdentity('1.3.6.1.2.1.4.20'))  # IP address table
            )
        )
        
        hosts = []
        if error_indication:
            self.logger.error("SNMP error", target=target, error=error_indication)
        elif error_status:
            self.logger.error("SNMP error status", target=target, error=error_status)
        else:
            for varBind in var_binds:
                ip_info = {}
                for name, val in varBind:
                    if 'sysName' in str(name):
                        ip_info['hostname'] = str(val)
                    elif 'ipAdEntAddr' in str(name):
                        ip_info['ip_address'] = str(val)
                
                if ip_info.get('ip_address'):
                    hosts.append(ip_info)
        
        return {"hosts_found": len(hosts), "hosts": hosts}
```

**Files to Create:**
- `app/engines/discovery/snmp.py`

**Effort:** 16 hours  
**Risk:** Medium

---

### 4.2 Enhanced Passive Discovery

**Recommendation:**

```python
# app/engines/discovery/passive.py

class PassiveDiscoveryEngine:
    async def discover_from_arp_table(self) -> List[Dict]:
        """Enhanced ARP table parsing with duplicate detection."""
        result = await run_command(["arp", "-a"], timeout=30)
        
        if result["returncode"] == 0:
            hosts = self._parse_arp_output(result["stdout"])
            
            # Deduplicate by IP
            unique_hosts = {}
            for host in hosts:
                ip = host.get("ip_address")
                if ip and ip not in unique_hosts:
                    unique_hosts[ip] = host
            
            return list(unique_hosts.values())
        return []
    
    async def discover_from_dns(self) -> List[Dict]:
        """Discover hosts via DNS monitoring."""
        # Implement DNS query analysis
        return []
    
    async def discover_from_netflow(self) -> List[Dict]:
        """Discover hosts via network flow analysis."""
        # Implement netflow analysis
        return []
```

**Files to Modify:**
- `app/engines/discovery/passive.py`

**Effort:** 12 hours  
**Risk:** Medium

---

## 5. Performance Optimizations

### 5.1 Pagination Implementation

**Current Issues:**
```python
# No pagination on list endpoints
@router.get("/vulnerabilities")
async def list_vulnerabilities(db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(select(Vulnerability))
    return list(result.scalars().all())  # Loads all records!
```

**Recommendation:**

```python
# app/api/v1/scans.py

from fastapi import Query

@router.get("/scans")
async def list_scans(
    db: AsyncSession = Depends(get_async_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=200)
):
    result = await db.execute(
        select(Scan).offset(skip).limit(limit)
    )
    return list(result.scalars().all())

@router.get("/scans", response_model=PaginatedResponse[ScanSchema])
async def list_scans_paginated(
    db: AsyncSession = Depends(get_async_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=200)
):
    query = select(func.count()).select_from(Scan)
    total = (await db.execute(query)).scalar()
    
    result = await db.execute(
        select(Scan).offset(skip).limit(limit)
    )
    items = list(result.scalars().all())
    
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit
    }
```

**Files to Modify:**
- `app/api/v1/scans.py`
- `app/api/v1/assets.py`
- `app/api/v1/vulnerabilities.py`

**Effort:** 12 hours  
**Risk:** Low

---

### 5.2 Bulk Operations Implementation

**Recommendation:**

```python
# app/api/v1/assets.py

@router.post("/assets/bulk", status_code=201)
async def bulk_create_assets(
    assets: List[AssetCreate],
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_async_session)
):
    if "write" not in (user.scopes or []):
        raise HTTPException(status_code=403, detail="Write permissions required")
    
    if len(assets) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 assets per bulk request")
    
    db_assets = []
    for asset in assets:
        db_asset = Asset(**asset.model_dump())
        db.add(db_asset)
        db_assets.append(db_asset)
    
    await db.commit()
    
    for asset in db_assets:
        await db.refresh(asset)
    
    return {
        "created_count": len(db_assets),
        "assets": db_assets
    }
```

**Files to Modify:**
- `app/api/v1/assets.py`
- `app/api/v1/vulnerabilities.py`

**Effort:** 8 hours  
**Risk:** Medium

---

## 6. Testing Recommendations

### 6.1 Validator Unit Tests

**Recommendation:**

```python
# app/core/test_validators.py (NEW FILE)

import pytest
from app.core.validators import (
    validate_cidr,
    validate_ipv4,
    validate_ipv6,
    parse_and_validate_ports
)

class TestCIDRValidation:
    def test_valid_ipv4_cidr(self):
        assert validate_cidr("192.168.1.0/24") is True
        assert validate_cidr("10.0.0.0/8") is True
    
    def test_invalid_cidr(self):
        assert validate_cidr("192.168.1.0/33") is False
        assert validate_cidr("invalid") is False

class TestIPv4Validation:
    def test_valid_ipv4(self):
        assert validate_ipv4("192.168.1.1") is True
    
    def test_invalid_ipv4(self):
        assert validate_ipv4("256.1.1.1") is False
        assert validate_ipv4("192.168.1") is False

class TestPortParsing:
    def test_single_port(self):
        valid, ports, msg = parse_and_validate_ports("80")
        assert valid is True
        assert ports == [80]
    
    def test_port_range(self):
        valid, ports, msg = parse_and_validate_ports("1-1024")
        assert valid is True
        assert len(ports) == 1024
    
    def test_sql_injection_detection(self):
        valid, ports, msg = parse_and_validate_ports("80; DROP TABLE users--")
        assert valid is False
```

**Files to Create:**
- `app/core/test_validators.py`
- `tests/` directory structure

**Effort:** 16 hours  
**Risk:** Low

---

## 7. Migration Plan

### Phase 1: Critical (Week 1-2)

| Week | Tasks |
|------|-------|
| Week 1 | ISS-001, ISS-002 (Security) |
| Week 2 | ISS-003 (Foreign Keys), ISS-004 (Versioning) |

### Phase 2: High Priority (Week 3-4)

| Week | Tasks |
|------|-------|
| Week 3 | ISS-005 (Vulnerability CRUD), ISS-006 (Naming) |
| Week 4 | ISS-007 (SNMP), ISS-008 (N+1 queries) |

### Phase 3: Medium Priority (Week 5-6)

| Week | Tasks |
|------|-------|
| Week 5 | ISS-011 (Indexes), ISS-012 (Deprecation headers) |
| Week 6 | ISS-013 (Passive discovery), ISS-014 (Error handling) |

### Phase 4: Low Priority (Week 7-8)

| Week | Tasks |
|------|-------|
| Week 7 | ISS-016 (Config), ISS-017 (Docs) |
| Week 8 | ISS-018 (Tests), ISS-019 (Pagination) |

---

## 8. Implementation Checklist

### Pre-Implementation
- [ ] Review all recommendations with team
- [ ] Create detailed implementation plan
- [ ] Set up development environment
- [ ] Configure testing framework

### Implementation
- [ ] Phase 1: Critical security issues
- [ ] Phase 2: High-priority features
- [ ] Phase 3: Medium-priority improvements
- [ ] Phase 4: Low-priority enhancements

### Post-Implementation
- [ ] Write comprehensive tests
- [ ] Update API documentation
- [ ] Create migration guides
- [ ] Deploy to staging environment

---

*Recommendations document for NetScope API v1*
