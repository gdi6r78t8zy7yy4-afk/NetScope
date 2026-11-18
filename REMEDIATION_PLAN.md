# NetScope Technical Remediation Plan

## Overview

This document outlines the comprehensive technical remediation plan for the NetScope codebase, identifying critical defects and establishing a systematic approach to correction.

## Assessment Summary

**Total Backend Python Files:** 69 files  
**Current Test Status:** 54/54 passing (but database initialization missing)  
**Critical Issues Identified:** 12  

---

## Phase 1: Repository Assessment

### Critical Defects Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | Database initialization not called in tests | CRITICAL | `app/database/__init__.py` |
| 2 | Missing import for ScanTarget model | HIGH | `app/models/network.py` |
| 3 | Database models missing foreign key relationships | HIGH | Multiple model files |
| 4 | Async session leak in API endpoints | CRITICAL | `app/api/v1/*.py` |
| 5 | Nmap scan process not properly terminated on timeout | CRITICAL | `app/engines/port_scanner/nmap_engine.py` |
| 6 | Vulnerability correlation uses substring matching only | HIGH | `app/engines/correlation/service_correlator.py` |
| 7 | CISA KEV integration uses mock data | CRITICAL | `app/engines/vulnerability/intelligence.py` |
| 8 | NVD integration uses first page only | CRITICAL | `app/engines/vulnerability/intelligence.py` |
| 9 | Service detection fabricates confidence values | HIGH | `app/engines/service_detection/detector.py` |
| 10 | OS fingerprinting missing CPE extraction | MEDIUM | `app/engines/os_fingerprinting/fingerprinter.py` |
| 11 | Risk engine scoring boundaries untested | MEDIUM | `app/engines/risk_engine/analyzer.py` |
| 12 | Frontend uses hardcoded data instead of API responses | HIGH | Multiple frontend files |

---

## Phase 2: Network Discovery

### Requirements
1. Validate IPv4/IPv6/CIDR using Python `ipaddress` module
2. Implement authorized target scope validation
3. Fix ARP-scan invocation to use actual subnet parameter
4. Handle macOS network interfaces correctly
5. Improve ARP table parsing for passive discovery
6. Separate passive vs active observations
7. Use Nmap XML output (`-oX -`) instead of human-readable text
8. Preserve discovery source and timestamp for every observation
9. Deduplicate assets during network discovery
10. Handle timeouts and process termination properly

### Implementation Tasks

#### 2.1 IP Validation
- [ ] Create `app/core/validators.py` for network validation
- [ ] Implement IPv4 CIDR range validation
- [ ] Implement IPv6 CIDR range validation
- [ ] Add scope validation (private IPs only by default)

#### 2.2 ARP Discovery
- [ ] Review `app/engines/discovery/passive.py` for ARP table parsing
- [ ] Create separate passive observation models
- [ ] Fix ARP-scan subprocess invocation with proper arguments

#### 2.3 Active Discovery
- [ ] Review `app/engines/discovery/active.py`
- [ ] Implement ping sweep with configurable timeout
- [ ] Use Nmap XML output for active discovery

#### 2.4 Asset Deduplication
- [ ] Add unique constraint on IP address
- [ ] Implement merge logic for duplicate discovery
- [ ] Track discovery source and timestamp

---

## Phase 3: Port Scanner

### Requirements
1. TCP scanning (syn, connect)
2. UDP scanning with proper state detection
3. Single-port and custom port list scanning
4. Full TCP range 1-65535 support
5. Common port presets
6. Configurable timing and timeouts
7. Scan cancellation with process termination
8. Nmap XML parsing with Python XML parser

### Implementation Tasks

#### 3.1 Refactor NmapPortScanner
- [ ] Create `NmapScanner` class in `app/engines/port_scanner/nmap_engine.py`
- [ ] Parse Nmap XML output using `xml.etree.ElementTree`
- [ ] Implement scan process with subprocess and asyncio
- [ ] Add timeout handling with proper process termination

#### 3.2 Port State Parsing
- [ ] Support all Nmap port states: open, closed, filtered, open|filtered, unfiltered
- [ ] Never assume port states without explicit data
- [ ] Validate ports and protocols before invocation

#### 3.3 Scan Configuration
- [ ] TCP SYN scan mode
- [ ] TCP connect scan mode
- [ ] UDP scan mode
- [ ] Custom port range configuration
- [ ] Common ports preset (20, 21, 22, 23, 25, 53, 80, 110, etc.)
- [ ] Full range (1-65535) scan
- [ ] Timing presets (paranoid, sneaky, polite, normal, aggressive, insane)

---

## Phase 4: Service Detection and OS Fingerprinting

### Requirements
1. Extract service name, product, version from Nmap XML
2. Preserve confidence information
3. Handle tunnel information when available
4. Separate expected vs detected vs confirmed services
5. OS fingerprinting with CPE extraction

### Implementation Tasks

#### 4.1 Service Detection
- [ ] Parse Nmap service detection XML
- [ ] Extract product and version information
- [ ] Preserve confidence percentage
- [ ] Handle tunnel (ssl/tls) detection
- [ ] Differentiate expected service (port-based guess) from detected

#### 4.2 OS Fingerprinting
- [ ] Parse OS detection XML from Nmap
- [ ] Extract: name, family, generation, device type, vendor, CPE, accuracy
- [ ] Store raw evidence for reproducibility

---

## Phase 5: Database and API Corrections

### Requirements
1. Correct SQLAlchemy model relationships
2. Proper async session handling
3. No asyncio.run() in FastAPI event loop
4. Database migrations
5. Proper indexes and constraints
6. Scan job lifecycle management

### Implementation Tasks

#### 5.1 Model Relationships
- [ ] Add foreign keys: Asset -> Network, Port -> Asset, Vulnerability -> Asset
- [ ] Add relationship back-references
- [ ] Create association tables for many-to-many relationships

#### 5.2 Database Initialization
- [ ] Fix async session handling in tests
- [ ] Create database initialization script
- [ ] Add migration support (Alembic)

#### 5.3 API Session Management
- [ ] Fix all database session leaks
- [ ] Implement proper transaction handling
- [ ] Add error rollback

#### 5.4 Scan Cancellation
- [ ] Implement process-level scan cancellation
- [ ] Terminate actual scanner processes on cancel
- [ ] Clean up resources properly

---

## Phase 6: Vulnerability Intelligence - CISA KEV

### Requirements
1. Use official JSON feed from CISA
2. Parse official schema
3. Store all required fields
4. Update catalog version and release date

### Implementation Tasks

#### 6.1 KEV Integration
- [ ] Replace mock data with actual CISA API integration
- [ ] Fetch from: https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
- [ ] Store: catalog_version, release_date, all required fields

#### 6.2 Data Persistence
- [ ] Update Vulnerability model for KEV fields
- [ ] Create migration script

---

## Phase 7: Vulnerability Intelligence - NVD CVE

### Requirements
1. Use NVD CVE API 2.0
2. Implement pagination
3. Incremental updates
4. Rate limiting support
5. API key support
6. CVSS v3.1 and v4.0 support

### Implementation Tasks

#### 7.1 NVD Integration
- [ ] Replace incomplete implementation with full pagination support
- [ ] Use: https://services.nvd.nist.gov/rest/json/cves/2.0
- [ ] Implement rate limiting (1 per 6 seconds)
- [ ] Add API key support

#### 7.2 Data Normalization
- [ ] CPE applicability extraction
- [ ] CVSS v3.1 and v4.0 support
- [ ] Historical modification tracking

---

## Phase 8: Vulnerability Intelligence - FIRST EPSS

### Requirements
1. Use official EPSS API
2. Bulk synchronization from CSV
3. Individual CVE lookups

### Implementation Tasks

#### 8.1 EPSS Integration
- [ ] Use: https://api.first.org/data/v1/epss
- [ ] Implement bulk sync from daily CSV
- [ ] Store: CVE ID, EPSS score, percentile, date

---

## Phase 9: Vulnerability Correlation

### Requirements
1. Vendor normalization
2. Product normalization
3. CPE matching
4. Version range comparison
5. Multiple affected configurations

### Implementation Tasks

#### 9.1 Correlation Engine
- [ ] Replace substring matching with proper CPE matching
- [ ] Implement version range comparison
- [ ] Support confidence levels: confirmed, potential, unverified, not affected
- [ ] Separate KEV status from correlation

---

## Phase 10: Risk Engine

### Requirements
1. Separate CVSS severity from EPSS probability
2. CISA KEV status consideration
3. Asset importance scoring
4. Exposure scoring

### Implementation Tasks

#### 10.1 Risk Scoring
- [ ] Implement proper risk score calculation
- [ ] Add unit tests for scoring boundaries
- [ ] Handle missing data gracefully

---

## Phase 11: Frontend Data Integrity

### Requirements
1. Remove hardcoded dashboard statistics
2. Use backend API responses
3. Display empty state when no data
4. Distinguish between real, cached, and demonstration data

### Implementation Tasks

#### 11.1 Frontend Corrections
- [ ] Replace hardcoded data with API calls
- [ ] Implement loading states and empty states
- [ ] Add data source indicators in UI

---

## Phase 12: macOS and Tauri Integration

### Requirements
1. Tauri 2 compatibility
2. Proper process management
3. Localhost binding by default
4. Correct CORS configuration

### Implementation Tasks

#### 12.1 Tauri Configuration
- [ ] Update tauri.conf.json for version 2
- [ ] Fix Cargo.toml dependencies
- [ ] Set up proper backend process management

---

## Test Coverage Requirements

### Required Tests (20 total)
1. IPv4 and IPv6 validation
2. CIDR validation
3. Target authorization
4. ARP output parsing
5. Nmap XML parsing
6. TCP port state parsing
7. UDP port state parsing
8. Full TCP port range configuration
9. Service version extraction
10. OS fingerprint parsing
11. CISA KEV JSON parsing
12. NVD pagination
13. EPSS parsing
14. CPE matching
15. Version range comparisons
16. False-positive prevention
17. Database persistence
18. Asset deduplication
19. Scan cancellation
20. API integration tests

---

## Completion Criteria

This remediation phase is complete when:
- [ ] All backend tests pass (54+)
- [ ] Frontend production build succeeds
- [ ] Database initialization succeeds
- [ ] All API endpoints work with proper async handling
- [ ] Nmap scanners parse XML correctly
- [ ] Intelligence data is persisted to SQLite
- [ ] Vulnerability correlation passes boundary tests
- [ ] Scan cancellation terminates actual processes
- [ ] Tauri configuration verified on Apple Silicon

---

## Files to Create/Modify

### New Files
- `backend/app/core/validators.py` - IP/CIDR validation
- `backend/app/utils/migrations.py` - Database migrations
- `backend/tests/integration/test_api_complete.py` - Integration tests

### Modified Files
- `backend/app/database/base.py` - Add init_db() call
- `backend/app/models/*.py` - Fix relationships and constraints
- `backend/app/api/v1/*.py` - Fix async session handling
- `backend/app/engines/port_scanner/nmap_engine.py` - Complete rewrite
- `backend/app/engines/vulnerability/intelligence.py` - Real API integration

---

## Risk Assessment

| Phase | Complexity | Estimated Time |
|-------|-----------|----------------|
| 1-2: Assessment & Discovery | Low | 4 hours |
| 3: Port Scanner | High | 8 hours |
| 4-5: Service/OS & Database | High | 6 hours |
| 6-8: Vulnerability Intelligence | Medium | 8 hours |
| 9-10: Correlation & Risk | High | 6 hours |
| 11-12: Frontend & Desktop | Medium | 4 hours |

**Total Estimated Time:** 36 hours (9 days at 4 hours/day)
