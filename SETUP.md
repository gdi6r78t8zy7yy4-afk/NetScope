# NetScope Setup Guide

## Prerequisites

### macOS 13+ (Apple Silicon recommended)

1. **Python 3.12 or higher**
   ```bash
   python3 --version
   # Should show Python 3.12.x
   ```

2. **Node.js 20+**
   ```bash
   node --version
   npm --version
   ```

3. **Rust (for Tauri desktop)**
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   ```

4. **External Tools** (for scanning functionality)
   ```bash
   # Install Homebrew if not already installed
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   
   # Install Nmap (required for scanning)
   brew install nmap
   
   # Optional: ARP-scan
   brew install arp-scan
   
   # Optional: TShark for packet analysis
   brew install tshark
   ```

## Quick Start

### Option 1: Automated Setup (Recommended)

```bash
cd /Users/carl/Documents/workspace/networking

# Run setup script
./scripts/setup.sh

# Start all components
./scripts/run.sh all
```

### Option 2: Manual Setup

#### Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate and install dependencies
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Run backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev --host 0.0.0.0 --port 3000
```

#### Desktop Setup

```bash
cd desktop/src-tauri

# Build the application
cargo build --target aarch64-apple-darwin
```

## Development Commands

### Backend

```bash
cd backend
source venv/bin/activate

# Run server with auto-reload
uvicorn app.main:app --reload

# Run tests
pytest app/tests/

# Run linter
ruff check .
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Run linting
npm run lint
```

### Desktop

```bash
cd desktop/src-tauri

# Build debug version
cargo build --target aarch64-apple-darwin

# Build release version
cargo build --release --target aarch64-apple-darwin

# Run in development mode
cargo run --target aarch64-apple-darwin
```

## Project Structure

```
networking/
├── backend/              # Python FastAPI backend
│   ├── app/
│   │   ├── api/         # API endpoints
│   │   ├── core/        # Core functionality
│   │   ├── database/    # Database models and sessions
│   │   ├── engines/     # Core processing engines
│   │   ├── models/      # SQLAlchemy models
│   │   ├── schemas/     # Pydantic schemas
│   │   ├── services/    # Business logic
│   │   └── main.py      # FastAPI app entry point
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/            # React TypeScript frontend
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── stores/
│   ├── package.json
│   └── vite.config.ts
├── desktop/            # Tauri 2 desktop app
│   └── src-tauri/
│       ├── src/
│       └── tauri.conf.json
├── scripts/            # Development scripts
└── docs/               # Documentation

```

## API Endpoints

### Network Discovery
- `GET /api/v1/discovery/passive` - Passive discovery
- `POST /api/v1/discovery/active` - Active discovery

### Scanning
- `POST /api/v1/scans` - Create scan
- `GET /api/v1/scans/{id}` - Get scan status
- `POST /api/v1/scans/{id}/cancel` - Cancel scan

### Assets
- `GET /api/v1/assets` - List all assets
- `POST /api/v1/assets` - Create asset

### Vulnerabilities
- `GET /api/v1/vulnerabilities` - List vulnerabilities
- `POST /api/v1/intelligence/sync` - Sync CVE databases

## Troubleshooting

### Backend won't start
```bash
# Check Python version
python3 --version

# Reinstall dependencies
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend won't build
```bash
# Clear cache and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Desktop build fails
```bash
# Check Rust is installed
rustc --version

# Clean and rebuild
cd desktop/src-tauri
cargo clean
cargo build --target aarch64-apple-darwin
```

## Next Steps

1. Run `./scripts/setup.sh` to install dependencies
2. Start backend: `cd backend && source venv/bin/activate && uvicorn app.main:app --reload`
3. Start frontend: `cd frontend && npm run dev`
4. Desktop: `cd desktop/src-tauri && cargo build --target aarch64-apple-darwin`

---

For more information, see:
- [PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md)
- [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md)
- [README.md](README.md)
