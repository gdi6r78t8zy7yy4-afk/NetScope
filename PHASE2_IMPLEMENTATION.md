# Phase 2 Implementation Plan

## Overview
Phase 2 focuses on implementing the core scanning and intelligence capabilities of NetScope.

## Implementation Tasks

### Task 1: Enhanced Port Scanner (Day 1-2)

#### nmap_engine.py enhancements
```python
# Add async nmap subprocess execution
class NmapPortScanner:
    def __init__(self, timeout=60, max_retries=3):
        self.timeout = timeout
        self.max_retries = retries
        
    async def scan_host(self, ip: str, ports: List[int] = None) -> Dict:
        """Scan a single host for open ports using nmap"""
        
    async def scan_network(self, cidr: str) -> List[Dict]:
        """Scan entire network subnet"""
```

#### New Features:
- Port range scanning (1-65535 or custom ranges)
- Service version detection (-sV flag)
- OS detection (-O flag)
- Scan progress tracking
- Concurrent scanning support

### Task 2: Active Discovery Engine (Day 2)

#### active.py enhancements
```python
class ActiveDiscoveryEngine:
    async def icmp_ping_sweep(self, network: str) -> List[str]:
        """Ping sweep to discover active hosts"""
        
    async def arp_scan(self, network: str) -> List[Dict]:
        """ARP scan for local network hosts"""
        
    async def subnet_discovery(self, cidr: str) -> Dict:
        """Discover all hosts in a subnet"""
```

### Task 3: Vulnerability Intelligence (Day 2-3)

#### correlation.py enhancements
```python
class VulnerabilityCorrelator:
    async def fetch_cve_data(self, cve_id: str) -> Dict:
        """Fetch CVE data from NVD API"""
        
    async def correlate_assets_with_cves(self, assets: List[Asset]) -> Dict:
        """Match discovered assets with known vulnerabilities"""
        
    def calculate_risk_score(self, asset: Asset, vulnerabilities: List[Dict]) -> Dict:
        """Calculate risk score based on vulnerabilities"""
```

#### New API Endpoints:
- `POST /api/v1/scans/port` - Port scan a host
- `GET /api/v1/intelligence/cve/{cve_id}` - Get CVE details
- `POST /api/v1/intelligence/correlate` - Correlate assets with vulnerabilities

### Task 4: Enhanced Topology (Day 3)

#### topology_visualization enhancements
```typescript
interface NetworkNode {
  id: string;
  label: string;
  ip: string;
  type: 'router' | 'switch' | 'host' | 'server';
  vulnerability_count: number;
}

interface NetworkEdge {
  source: string;
  target: string;
  type: 'ethernet' | 'wifi' | 'wan';
}
```

## Testing Strategy

### Integration Tests
- Test nmap subprocess execution
- Verify CVE data fetching from NVD API
- Validate topology rendering with realistic data

### Manual Testing Checklist
- [ ] Run port scan on test network
- [ ] Verify active discovery finds live hosts
- [ ] Check vulnerability correlation with sample CVEs
- [ ] Validate topology visualization loads

## Success Criteria for Phase 2

1. ✅ Port scanner can detect open ports on hosts
2. ✅ Active discovery finds hosts via ICMP/ARP
3. ✅ Vulnerability correlation matches CVEs to assets
4. ✅ Topology visualization shows network structure

## Blocking Issues to Resolve

- Ensure nmap is installed on macOS (`brew install nmap`)
- NVD API rate limits (need API key for production)
- Handle network connectivity requirements
