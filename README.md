# NetScope – Network Discovery & Vulnerability Intelligence Platform

[![License](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)
[![macOS](https://img.shields.io/badge/macOS-13+-blue.svg)](https://www.apple.com/macos/)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-orange.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-blue.svg)](https://react.dev/)
[![Tauri](https://img.shields.io/badge/Tauri-2.0+-blue.svg)](https://tauri.app/)

NetScope is a production-quality, modular macOS desktop application that combines network discovery, vulnerability intelligence, and security assessment tools into one unified interface.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Installation](#installation)
- [Usage](#usage)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Features

### Network Discovery
- Passive observation of network traffic
- Active host discovery via Nmap and ARP-scan
- IPv4 and IPv6 support with CIDR notation
- MAC address detection with vendor identification
- DNS hostname resolution

### Port Scanning
- TCP and UDP port scanning
- Common port scanning presets
- Custom port range specification
- Service version detection

### Host Profiling
- Operating system fingerprinting
- Device type classification
- Service enumeration with confidence levels
- Network interface analysis

### Vulnerability Intelligence
- CISA Known Exploited Vulnerabilities (KEV) catalog
- NVD CVE database integration
- FIRST EPSS score retrieval
- Local vulnerability cache for offline operation

### Vulnerability Correlation
- Automatic CVE matching against discovered services
- Confidence scoring for matches
- Version range analysis
- Evidence tracking

### Risk Analysis
- CVSS-based severity scoring
- KEV status highlighting
- EPSS percentile calculation
- Risk prioritization engine

### Network Topology
- Interactive network visualization with Cytoscape.js
- Grouping by subnet and device type
- KEV-affected asset highlighting
- Export capabilities

## Architecture

NetScope uses a modular architecture:

```
┌─────────────────────────────┐
│   macOS Desktop (Tauri 2)   │
└──────────┬──────────────────┘
           │
┌──────────▼──────────────────┐
│     React + TypeScript      │
└──────────┬──────────────────┘
           │
┌──────────▼──────────────────┐
│     FastAPI + Python        │
└──────────┬──────────────────┘
           │
┌──────────▼──────────────────┐
│       SQLite Database       │
└─────────────────────────────┘
```

External integrations:
- Nmap for network scanning
- ARP-scan for host discovery (optional)
- TShark for packet analysis (optional)
- CISA KEV API
- NVD CVE API
- FIRST EPSS

## Technology Stack

### Frontend
- React 18+
- TypeScript
- Vite
- Tailwind CSS
- shadcn/ui
- Apache ECharts
- Cytoscape.js
- TanStack Query
- Zustand

### Backend
- Python 3.12+
- FastAPI
- Pydantic
- SQLAlchemy
- SQLite
- WebSockets

### Desktop
- Tauri 2
- Rust (for desktop integration)

## Installation

### Prerequisites

1. macOS 13+ (Apple Silicon recommended)
2. Python 3.12+
3. Homebrew

### External Dependencies

NetScope requires the following external tools:

```bash
# Install Nmap (required for scanning)
brew install nmap

# Optional: ARP-scan for passive discovery
brew install arp-scan

# Optional: TShark for packet analysis
brew install tshark
```

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/your-org/netscope.git
cd netscope
```

2. Set up Python backend:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Set up Node.js frontend:
```bash
cd ../frontend
npm install
```

4. Set up Tauri desktop:
```bash
cd ../desktop/src-tauri
cargo build --target aarch64-apple-darwin
```

5. Start development servers:
```bash
# Terminal 1: Backend
cd backend
python -m uvicorn app.main:app --reload

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: Desktop (Tauri)
cd desktop/src-tauri
cargo run --target aarch64-apple-darwin
```

### Production Build

```bash
# Build desktop application
cd desktop/src-tauri
cargo build --release --target aarch64-apple-darwin

# Build frontend
cd ../..
npm run build
```

## Usage

### Network Discovery

1. Navigate to the "Network Discovery" page
2. Configure scan targets (CIDR ranges, IP addresses)
3. Choose discovery mode:
   - **Passive**: Monitor existing network traffic
   - **Active**: Probe networks for active hosts
4. Review discovered assets in the inventory

### Port Scanning

1. Navigate to "Port Scanner"
2. Select target host(s) from discovered assets
3. Choose scan type:
   - **Common Ports**: Standard ports (22, 80, 443, etc.)
   - **Full TCP Range**: Scan ports 1-65535
   - **Custom Range**: Specify port range
4. Configure scan options and rate limits
5. Start scan and monitor progress

### Vulnerability Analysis

1. Navigate to "Vulnerabilities"
2. View CVE inventory and KEV findings
3. Filter by severity or KEV status
4. Click on CVE for detailed information
5. View affected hosts and services

### Risk Assessment

1. Navigate to "Risk Analysis"
2. Review prioritized findings
3. Sort by risk score or severity
4. Drill down into specific risks
5. Generate remediation recommendations

## Development Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ Complete | Foundation & Project Structure |
| 2 | ✅ Complete | Network Discovery & Asset Inventory |
| 3 | 🔄 In Progress | Port Scanning & Service Detection |
| 4 | Pending | Vulnerability Intelligence Integration |
| 5 | Pending | Correlation & Risk Analysis |
| 6 | Pending | Network Topology & Visualization |
| 7 | Pending | Packaging & Polishing |

See `DEVELOPMENT_ROADMAP.md` for detailed phase information.

## Configuration

### Application Settings

- Backend host and port
- Scan defaults (rate limits, timeouts)
- Intelligence API keys (CISA, NVD)
- Dependency management preferences

### Scanning Configuration

- Default target ranges
- Concurrent scan limits
- Rate limiting presets (slow, medium, fast)
- Service detection enabled/disabled

## API Documentation

The backend provides a complete OpenAPI specification:

```
http://localhost:8000/docs
```

Endpoints are available under `/api/v1/` prefix.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Development Guidelines

1. Follow the project architecture (see `PROJECT_ARCHITECTURE.md`)
2. Write tests for new functionality
3. Update documentation as needed
4. Run linting and type checks before committing
5. Ensure all tests pass

### Code Style

- Python: Follow PEP 8 with black formatting
- TypeScript: Use ESLint and Prettier
- Rust: Follow rustfmt style

## Security Considerations

NetScope is designed with security as a primary concern:

- All scanning requires explicit authorization
- No automatic exploitation capability
- Conservative scanning defaults
- Input validation on all endpoints
- Local-only data storage
- Process isolation for external tools

**Important**: This tool is intended for authorized network inventory and defensive security assessment. Use only on networks where you have permission to scan.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Nmap team for the exceptional network scanning tool
- CISA for the KEV catalog
- NIST for the NVD database
- FIRST for EPSS data

## Contact

For questions or support, please open an issue in the GitHub repository.

---

**Built with security and stability in mind.**
