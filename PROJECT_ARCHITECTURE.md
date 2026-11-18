# NetScope – Project Architecture

## Overview

NetScope is a macOS desktop application for network discovery, vulnerability intelligence, and security assessment. This document outlines the technical architecture and component relationships.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        macOS Desktop Application                     │
│                    ┌──────────────────────────┐                     │
│                    │    Tauri 2 Application   │                     │
│                    └─────────────┬────────────┘                     │
└──────────────────────────────────┼──────────────────────────────────┘
                                   │
           ┌───────────────────────┴───────────────────────┐
           │              Frontend (React/TS)               │
           │  ┌─────────┐ ┌─────────┐ ┌───────────────────┐ │
           │  │  Pages  │ │Components│ │  Services/Hooks   │ │
           │  └─────────┘ └─────────┘ └───────────────────┘ │
           └───────────────────────┬───────────────────────┘
                                   │ WebSocket / REST API
           ┌───────────────────────┴───────────────────────┐
           │            Backend (FastAPI/Python)            │
           │  ┌─────────┐ ┌─────────┐ ┌───────────────────┐ │
           │  │  APIs   │ │Services │ │    Workers/Engine   │ │
           │  └─────────┘ └─────────┘ └───────────────────┘ │
           └───────────────────────┬───────────────────────┘
                                   │
                   ┌───────────────┴───────────────┐
                   │         Data Layer              │
                   │  ┌───────────┐ ┌─────────────┐ │
                   │  │ Database  │ │ Intelligence│ │
                   │  └───────────┘ └─────────────┘ │
                   └───────────────┬───────────────┘
                                   │
           ┌───────────────────────┴───────────────────────┐
           │         External Tools & APIs                 │
           │  ┌─────────┐ ┌───────────┐ ┌───────────────┐  │
           │  │ Nmap    │ │ ARP-scan  │ │ CISA/NVD/EPSS │  │
           │  └─────────┘ └───────────┘ └───────────────┘  │
           └───────────────────────────────────────────────┘
```

## Component Architecture

### Frontend (React + TypeScript)

**Technology Stack:**
- Vite - Build tool and dev server
- React 18+ with TypeScript
- Tailwind CSS for styling
- shadcn/ui for component primitives
- Apache ECharts for charts and visualizations
- Cytoscape.js for network topology visualization
- TanStack Query (React Query) for data fetching and caching
- Zustand for state management

**Module Structure:**

```
frontend/src/
├── components/           # Reusable UI components
│   ├── layout/          # Layout components (Sidebar, Header, etc.)
│   ├── ui/              # UI primitives (buttons, cards, tables)
│   └── charts/          # ECharts components
├── layouts/             # Page layouts
│   ├── DashboardLayout.tsx
│   └── ScanLayout.tsx
├── pages/               # Page components
│   ├── overview/
│   ├── discovery/
│   ├── scanning/
│   ├── assets/
│   ├── vulnerabilities/
│   └── settings/
├── features/            # Feature-specific components
│   ├── dashboard/
│   ├── discovery/
│   ├── scanning/
│   ├── host_analysis/
│   └── topology/
├── services/            # API clients and WebSocket handlers
│   ├── api.ts
│   └── websocket.ts
├── hooks/               # Custom React hooks
│   ├── useScan.ts
│   └── useVulnerabilities.ts
├── stores/              # Zustand state stores
│   ├── scanStore.ts
│   └── settingsStore.ts
├── types/               # TypeScript type definitions
│   ├── api.d.ts
│   ├── scan.d.ts
│   └── vulnerability.d.ts
├── lib/                 # Utility functions
│   ├── format.ts
│   └── validation.ts
└── main.tsx             # Application entry point
```

### Backend (FastAPI + Python)

**Technology Stack:**
- FastAPI - Async web framework
- Pydantic - Data validation and serialization
- SQLAlchemy 2.0+ with Async support
- SQLite for local storage
- WebSockets for real-time updates
- asyncio for concurrent operations

**Module Structure:**

```
backend/app/
├── api/                 # API endpoints
│   ├── v1/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── networks.py
│   │   ├── discovery.py
│   │   ├── scans.py
│   │   ├── assets.py
│   │   ├── vulnerabilities.py
│   │   └── intelligence.py
├── core/                # Core functionality
│   ├── config.py        # Application configuration
│   └── security.py      # Security utilities
├── database/            # Database layer
│   ├── __init__.py
│   ├── session.py       # Session management
│   └── base.py          # Base class, metadata, types
├── models/              # SQLAlchemy ORM models
│   ├── __init__.py
│   ├── network.py
│   ├── asset.py
│   ├── scan.py
│   ├── vulnerability.py
│   └── intelligence.py
├── schemas/             # Pydantic schemas
│   ├── __init__.py
│   ├── network.py
│   ├── asset.py
│   ├── scan.py
│   ├── vulnerability.py
│   └── intelligence.py
├── services/            # Business logic layer
│   ├── __init__.py
│   ├── discovery.py
│   ├── scanning.py
│   └── correlation.py
├── engines/             # Core processing engines
│   ├── __init__.py
│   ├── discovery/
│   │   ├── passive.py
│   │   └── active.py
│   ├── port_scanner/
│   │   ├── nmap_engine.py
│   │   └── scanner.py
│   ├── service_detection/
│   │   └── detector.py
│   ├── os_fingerprinting/
│   │   └── fingerprinter.py
│   ├── host_profiling/
│   │   └── profiler.py
│   ├── vulnerability/
│   │   ├── correlation.py
│   │   └── intelligence.py
│   └── risk_engine/
│       └── analyzer.py
├── integrations/        # External tool integrations
│   ├── __init__.py
│   ├── nmap/
│   │   ├── parser.py
│   │   └── scanner.py
│   ├── arp_scan/
│   │   ├── parser.py
│   │   └── scanner.py
│   ├── tshark/
│   │   └── packet_analyzer.py
│   ├── snmp/
│   │   └── engine.py
│   ├── cisa/
│   │   ├── client.py
│   │   └── synchronizer.py
│   ├── nvd/
│   │   ├── client.py
│   │   └── synchronizer.py
│   └── epss/
│       ├── client.py
│       └── synchronizer.py
├── workers/             # Background tasks
│   ├── __init__.py
│   ├── scan.py
│   └── intelligence_sync.py
├── websocket/           # WebSocket handlers
│   ├── __init__.py
│   ├── manager.py
│   └── events.py
└── tests/               # Test suite
    ├── __init__.py
    ├── test_api.py
    └── test_engines.py
```

### Desktop (Tauri 2)

**Technology Stack:**
- Tauri 2 - Desktop application framework
- Rust for backend integration
- macOS target only

**Module Structure:**

```
desktop/
├── src-tauri/           # Tauri application
│   ├── Cargo.toml       # Rust dependencies
│   ├── src/
│   │   ├── main.rs      # Application entry point
│   │   ├── cmd/         # Tauri commands
│   │   │   ├── scan.rs
│   │   │   ├── discovery.rs
│   │   │   └── vulnerability.rs
│   │   ├── menu.rs      # Menu bar configuration
│   │   └── tray.rs      # System tray configuration
│   ├── tauri.conf.json  # Tauri configuration
│   └── capabilities/    # App capability definitions
├── src/
│   ├── lib.rs           # Rust library
│   └── main.rs          # Tauri entry point
└── build.rs             # Build script
```

## Data Flow

### Network Discovery Flow

```
User Request → API Endpoint → Worker Thread
                                    ↓
                            Passive/Active Discovery
                                    ↓
                    ┌───────────────┴───────────────┐
                    │                               │
            Passive Observation               Active Scan
                    │                               │
              Network Traffic             Nmap/ARP-scan
                    │                               │
                    └───────────────┬───────────────┘
                                    ↓
                            Asset Discovery
                                    ↓
                              Database Store
                                    ↓
                        WebSocket Broadcast
```

### Vulnerability Correlation Flow

```
Host Profile → Service Analysis → CPE Mapping
                                    ↓
                         Local Vulnerability DB Query
                                    ↓
                    ┌───────────────┴───────────────┐
                    │                               │
              CISA KEV Match                NVD EPSS Data
                    │                               │
                    └───────────────┬───────────────┘
                                    ↓
                           Risk Calculation
                                    ↓
                         Vulnerability Finding
```

## Communication Patterns

### Frontend ↔ Backend

- **REST API**: Initial data loading, CRUD operations
- **WebSockets**: Real-time updates during scans, progress reporting

### Backend ↔ External Tools

- **Subprocess execution**: Nmap, ARP-scan
- **HTTP API calls**: CISA, NVD, EPSS
- **File-based communication**: Temporary scan results

### Backend ↔ Database

- **SQLAlchemy ORM**: All data persistence
- **SQLite WAL mode**: Concurrent reads

## Security Considerations

### Authorization Model

1. Scan targets must be explicitly configured by user
2. Network ranges validated before execution
3. Rate limiting enforced per target
4. No automatic exploitation

### Data Protection

1. All data stored locally
2. Scan evidence preserved for audit
3. Vulnerability matching with confidence levels
4. No external communication except API calls

### Process Security

1. Subprocess execution with sanitized inputs
2. Timeouts on all external commands
3. Signal handling for cancellation

## Configuration Management

### Application Configuration

```json
{
  "application": {
    "name": "NetScope",
    "version": "1.0.0"
  },
  "backend": {
    "host": "localhost",
    "port": 8000,
    "log_level": "INFO"
  },
  "scanning": {
    "default_rate_limit": "medium",
    "max_concurrent_hosts": 5,
    "scan_timeout_seconds": 3600
  },
  "intelligence": {
    "cisa_api_key": null,
    "nvd_api_key": null,
    "update_interval_hours": 24
  },
  "dependencies": {
    "nmap_required": true,
    "arp_scan_required": false,
    "tshark_optional": true
  }
}
```

## API Endpoints

### Network & Discovery
- `GET /api/networks` - List configured networks
- `POST /api/networks` - Add network configuration
- `DELETE /api/networks/{id}` - Remove network

### Scanning
- `POST /api/scans` - Create new scan
- `GET /api/scans/{id}` - Scan status and results
- `POST /api/scans/{id}/cancel` - Cancel running scan

### Assets & Hosts
- `GET /api/assets` - List all discovered assets
- `GET /api/assets/{id}` - Asset details
- `GET /api/hosts/{id}/vulnerabilities` - Host vulnerability list

### Vulnerabilities
- `GET /api/vulnerabilities` - CVE inventory
- `GET /api/vulnerabilities/{cve_id}` - Detailed vulnerability info
- `GET /api/kev` - CISA KEV catalog

### Intelligence
- `POST /api/intelligence/sync` - Manual sync trigger
- `GET /api/intelligence/status` - Last sync time and status

## WebSocket Events

### Client → Server
- `scan_create` - Create new scan
- `scan_cancel` - Cancel running scan
- `subscribe_events` - Subscribe to real-time events

### Server → Client
- `scan_progress` - Scan progress updates
- `new_asset` - New asset discovered
- `scan_complete` - Scan completion notification
- `vulnerability_finding` - New vulnerability finding
- `intelligence_synced` - Intelligence database update

## File Structure Summary

```
networking/
├── backend/              # Python FastAPI backend
│   └── app/
├── frontend/             # React frontend
│   └── src/
├── desktop/              # Tauri 2 macOS app
│   └── src-tauri/
├── docs/                 # Documentation
├── scripts/              # Build and utility scripts
├── PROJECT_ARCHITECTURE.md  # This file
├── DEVELOPMENT_ROADMAP.md   # Phase-by-phase plan
├── TECHNICAL_DECISIONS.md   # Technical decisions record
└── README.md             # Project overview
```
