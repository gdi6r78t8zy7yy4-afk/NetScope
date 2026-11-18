# NetScope Development Roadmap

## Overview

This document outlines the development phases for NetScope, a comprehensive network discovery and vulnerability intelligence platform.

## Completed Phases

### Phase 1: Foundation & Project Structure ✅

**Status:** Complete  
**Date Completed:** November 2026  

#### Deliverables
- [x] Project structure and directory layout
- [x] Backend with FastAPI framework setup
- [x] Frontend with React + Vite setup  
- [x] Database schema and models
- [x] Development environment configuration
- [x] Testing infrastructure setup
- [x] Continuous integration setup

#### Key Features Implemented
- RESTful API with OpenAPI documentation
- SQLite database with SQLAlchemy ORM
- React frontend with TypeScript
- Basic authentication and authorization structure

#### Testing Coverage
- 7 API endpoint tests (100% passing)
- Engine tests for discovery and scanning
- Database model tests
- Pydantic schema validation tests

---

### Phase 2: Network Discovery & Asset Inventory ✅

**Status:** Complete  
**Date Completed:** November 2026  

#### Deliverables
- [x] Passive discovery engine (ARP, netstat)
- [x] Active discovery engine (ping sweep)
- [x] Port scanning engine with Nmap
- [x] Vulnerability correlation engine
- [x] Asset inventory management
- [x] Network topology tracking

#### Key Features Implemented
- Automated network discovery
- Service version detection
- Operating system fingerprinting
- Vulnerability correlation with CVE matching
- Risk scoring and prioritization

#### Testing Coverage
- 18 engine tests (passing)
- 7 API endpoint tests (passing)
- Database model validation tests
- Network topology relationship tests

---

## Completed Phases

### Phase 4: Vulnerability Intelligence Integration ✅

**Status:** Complete  
**Date Completed:** November 2026  

#### Deliverables
- [x] CISA KEV API integration
- [x] NVD CVE database sync
- [x] EPSS score retrieval
- [x] Vulnerability cache management

#### Key Features Implemented
1. **CISA KEV API Client** (`backend/app/engines/vulnerability/cisa_kev.py`)
   - Fetch complete KEV catalog
   - Check CVE status in KEV
   - Get entries by date range

2. **NVD CVE API Client** (`backend/app/engines/vulnerability/nvd_cve.py`)
   - Fetch CVE details by ID
   - Search CVEs by product
   - Get recent CVEs with pagination

3. **EPSS API Client** (`backend/app/engines/vulnerability/epss.py`)
   - Get EPSS scores for CVE
   - Get top CVEs by percentile

4. **Vulnerability Correlation Engine** (`backend/app/engines/vulnerability/correlation.py`)
   - Correlate vulnerabilities with assets
   - Calculate combined risk scores

5. **Intelligence Sync Engine** (`backend/app/engines/vulnerability/intelligence.py`)
   - Coordinate multiple API clients
   - Sync all intelligence sources

6. **API Endpoints** (`backend/app/api/v1/intelligence.py`)
   - 10 endpoints for CVE intelligence

#### Testing Coverage
- 3 CISA KEV client tests (100% passing)
- 3 NVD CVE client tests (100% passing)
- 2 EPSS client tests (100% passing)
- 6 correlation engine tests (100% passing)
- 2 intelligence sync tests (100% passing)
- 3 vulnerability model tests (100% passing)

#### API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/intelligence/cve/{cve_id} | Get complete CVE intelligence |
| POST | /api/v1/intelligence/sync/cves | Sync CVEs from NVD |
| POST | /api/v1/intelligence/sync/kev | Sync KEV catalog from CISA |
| POST | /api/v1/intelligence/sync/epss | Sync EPSS scores |
| GET | /api/v1/intelligence/status | Get sync status for all sources |
| GET | /api/v1/intelligence/epss/{cve_id} | Get EPSS scores for CVE |
| GET | /api/v1/intelligence/kev/catalog | Get complete KEV catalog |
| GET | /api/v1/intelligence/kev/entries | Get KEV entries with limit |
| GET | /api/v1/intelligence/kev/{cve_id} | Get KEV entry for CVE |
| GET | /api/v1/intelligence/correlate/{asset_id} | Correlate vulnerabilities for asset |

---

### Phase 5: Consolidate Nmap Integration ✅

**Status:** Complete  
**Date Completed:** November 2026  

#### Deliverables
- [x] Nmap integration and wrapper
- [x] Port scanning engine implementation
- [x] Service version detection
- [x] Scan scheduling capabilities
- [x] Export functionality (CSV, JSON, PDF)
- [x] Scan history and reporting

#### Key Features Implemented
1. **Scan Scheduling**
   - Cron-like scheduling API with parse_cron function
   - Recurring scans support via ScheduleParser class
   - Scan priority queue integration

2. **Export Functionality**
   - CSV export for asset lists and scan results
   - JSON export for structured data
   - PDF report generation for vulnerability findings

3. **Scan Results Processing**
   - Nmap XML parsing engine
   - Scan history storage
   - Summary statistics generation

#### Testing Coverage
- 5 scan scheduling tests (100% passing)
- 6 export functionality tests (100% passing)
- 8 Nmap output parsing and results aggregation tests (100% passing)

---

## Future Phases

### Phase 4: Vulnerability Intelligence Integration

**Status:** Planned  
**Target Start Date:** December 2026  

#### Deliverables
- [ ] CISA KEV API integration
- [ ] NVD CVE database sync
- [ ] EPSS score retrieval
- [ ] Vulnerability cache management

#### Key Features
- Automated CVE data collection
- KEV status highlighting
- Risk scoring with EPSS

---

### Phase 5: Correlation & Risk Analysis

**Status:** Planned  
**Target Start Date:** December 2026  

#### Deliverables
- [ ] CVE-to-service correlation
- [ ] Risk scoring engine
- [ ] Prioritization algorithms
- [ ] Remediation recommendations

---

### Phase 5: Correlation & Risk Analysis ✅

**Status:** Complete  
**Date Completed:** November 2026  

#### Deliverables
- [x] CVE-to-service correlation
- [x] Risk scoring engine
- [x] Prioritization algorithms
- [x] Remediation recommendations

#### Key Features Implemented
1. **Vulnerability Correlation Engine**
   - Asset-vulnerability correlation
   - Combined risk scoring (CVSS + EPSS + KEV)
   - Priority determination from risk score
   - Confidence-based matching

2. **Risk Scoring Algorithm**
   - Weighted combination of factors
   - Dynamic priority assignment
   - Risk factor extraction

3. **EPSS Integration**
   - Probability-based risk scoring
   - Percentile ranking
   - Top CVE identification

#### API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/intelligence/correlate/{asset_id} | Correlate vulnerabilities for asset |
| GET | /api/v1/risk/findings | List risk findings |
| GET | /api/v1/risk/findings/{finding_id} | Get specific risk finding |

#### Testing Coverage
- 6 correlation engine tests (100% passing)
- Risk scoring validation
- Priority determination tests

---

### Phase 6: Network Topology & Visualization

**Status:** Planned  
**Target Start Date:** January 2027  

#### Deliverables
- [ ] Interactive network map
- [ ] Asset grouping and filtering
- [ ] KEV status visualization
- [ ] Topology export

---

### Phase 7: Packaging & Polishing

**Status:** Planned  
**Target Start Date:** January 2027  

#### Deliverables
- [ ] Tauri desktop packaging
- [ ] Configuration management
- [ ] Update mechanism
- [ ] User documentation

---

## Testing Strategy

### Test Categories
1. **Unit Tests** - Individual components and functions
2. **Integration Tests** - API endpoints and database interactions
3. **Engine Tests** - Discovery, scanning, and correlation engines
4. **E2E Tests** - Full user workflows (TBD)

### Test Coverage Targets
- Unit tests: 80%+
- Integration tests: Critical paths only
- Engine tests: All major algorithms

---

## Timeline

| Phase | Estimated Duration |
|-------|-------------------|
| 1 - Foundation | Complete ✅ |
| 2 - Discovery & Inventory | Complete ✅ |
| 3 - Scanning & Export | ~1 week 🔄 |
| 4 - Vulnerability Intelligence | ~2 weeks |
| 5 - Correlation & Risk | ~1 week |
| 6 - Topology & Visualization | ~2 weeks |
| 7 - Packaging & Polish | ~1 week |

**Total Estimated Time:** ~8 weeks from Phase 3 completion

---

## Notes

- All tests are run with: `pytest app/tests/ -v`
- Frontend builds are verified with: `npm run build`
- Backend runs on port 8000
- Frontend runs on port 3000
