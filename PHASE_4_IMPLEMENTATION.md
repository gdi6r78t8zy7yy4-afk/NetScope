# Phase 4: Vulnerability Intelligence Integration - Implementation Guide

## Overview
Phase 4 focuses on integrating vulnerability intelligence sources to provide context about security vulnerabilities found during scans.

## Key Components

### 1. CISA KEV API Client
**File:** `backend/app/engines/vulnerability/cisa_kev.py`

```python
class CISAKeyVulnerabilitiesAPI:
    """CISA Known Exploited Vulnerabilities API client."""
    
    BASE_URL = "https://www.cisa.gov/sites/default/files/feeds"
    
    async def get_kev_catalog(self) -> List[Dict]:
        """Fetch KEV catalog from CISA."""
        pass
    
    async def is_vulnerability_kev(self, cve_id: str) -> bool:
        """Check if a CVE is in the KEV catalog."""
        pass
    
    async def sync_kev_catalog(self) -> SyncResult:
        """Sync KEV catalog to local database."""
        pass
```

### 2. NVD CVE API Client
**File:** `backend/app/engines/vulnerability/nvd_cve.py`

```python
class NVIDBCVEAPI:
    """NVD CVE Database API client."""
    
    BASE_URL = "https://services.nvd.nist.gov/rest/json"
    
    async def get_cve(self, cve_id: str) -> Dict:
        """Get CVE details by ID."""
        pass
    
    async def search_cves(self, cpe_name: str) -> List[Dict]:
        """Search CVEs by CPE name."""
        pass
    
    async def sync_cves(self, start_date: datetime = None) -> SyncResult:
        """Sync CVEs from NVD."""
        pass
```

### 3. EPSS API Client
**File:** `backend/app/engines/vulnerability/epss.py`

```python
class EPSSAPI:
    """FIRST EPSS API client."""
    
    BASE_URL = "https://api.first.org/epss"
    
    async def get_epss(self, cve_id: str) -> Dict:
        """Get EPSS scores for a CVE."""
        pass
    
    async def get_top_cves(self, percentile: float = 0.95) -> List[Dict]:
        """Get top CVEs by EPSS percentile."""
        pass
```

### 4. Vulnerability Correlation Engine
**File:** `backend/app/engines/vulnerability/correlation.py`

```python
class VulnerabilityCorrelationEngine:
    """Correlate vulnerabilities with intelligence data."""
    
    async def correlate_vulnerability(self, vulnerability: Vulnerability) -> Dict:
        """Add intelligence data to a vulnerability."""
        pass
    
    async def calculate_risk_score(self, vuln: Vulnerability) -> float:
        """Calculate combined risk score."""
        pass
```

---

## Database Schema Changes

### Vulnerability Model Updates
```python
class Vulnerability(Base):
    # Existing fields
    cve_id: str
    description: str
    cvss_score: float
    
    # New fields for Phase 4
    epss_score: Optional[float] = None
    epss_percentile: Optional[float] = None
    
    is_kev: bool = False
    kev_date_added: Optional[datetime] = None
    kev_required_action: Optional[str] = None
    
    nvd_last_modified: Optional[datetime] = None
    nvd_cve_json: Optional[str] = None  # Store full NVD response
    
    last_synced: datetime
```

---

## API Endpoints

### Vulnerability Intelligence Endpoints
```python
# GET /api/v1/intelligence/cve/{cve_id}
async def get_cve_intelligence(cve_id: str):
    """Get CVE intelligence including EPSS and KEV status."""
    pass

# POST /api/v1/intelligence/sync/cves
async def sync_cves():
    """Trigger CVE synchronization from NVD."""
    pass

# POST /api/v1/intelligence/sync/kev
async def sync_kev():
    """Trigger KEV catalog synchronization."""
    pass

# GET /api/v1/intelligence/epss/{cve_id}
async def get_epss_scores(cve_id: str):
    """Get EPSS scores for a CVE."""
    pass
```

---

## Frontend Components

### Vulnerability Details Page
```tsx
interface VulnerabilityDetailsProps {
  cveId: string;
}

// Display KEV status badge
{vulnerability.is_kev && (
  <Badge variant="destructive">
    🚨 CISA KEV - Known Exploited
  </Badge>
)}

// Display EPSS risk score
<div className="text-sm">
  <strong>EPSS Risk Score:</strong> {vulnerability.epss_score}
</div>
```

### CVE Search Component
```tsx
async function searchCVEs(query: string) {
  const response = await fetch(`/api/v1/intelligence/cve/search?q=${query}`);
  return response.json();
}
```

---

## Implementation Tasks

### Phase 4.1: API Clients (Week 1)
- [ ] Implement CISA KEV API client
- [ ] Implement NVD CVE API client
- [ ] Implement EPSS API client
- [ ] Add rate limiting and error handling

### Phase 4.2: Data Synchronization (Week 1)
- [ ] Implement sync engines
- [ ] Add scheduled tasks for daily sync
- [ ] Create sync status tracking

### Phase 4.3: Frontend Integration (Week 2)
- [ ] Update vulnerability display pages
- [ ] Add KEV status badges
- [ ] Add EPSS risk indicators

### Phase 4.4: Testing (Week 2)
- [ ] Write API client tests
- [ ] Write sync workflow tests
- [ ] Integration tests for frontend

---

## Next Steps

1. Create `backend/app/engines/vulnerability/cisa_kev.py`
2. Create `backend/app/engines/vulnerability/nvd_cve.py`
3. Create `backend/app/engines/vulnerability/epss.py`
4. Implement API routes for vulnerability intelligence
5. Update frontend components with KEV/EPSS data
