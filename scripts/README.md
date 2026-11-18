# NetScope Scripts

This directory contains utility scripts for development.

## Scripts

### setup.sh
Installs all dependencies for backend, frontend, and desktop.
```bash
./scripts/setup.sh
```

### run.sh
Runs NetScope components:
- `backend` - Start the FastAPI backend server
- `frontend` - Start the React development server  
- `desktop` - Build and run the Tauri desktop app
- `all` - Run all components simultaneously

```bash
./scripts/run.sh backend
./scripts/run.sh frontend
./scripts/run.sh desktop
./scripts/run.sh all
```

## Usage

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Setup dependencies
./scripts/setup.sh

# Run components
./scripts/run.sh all
```

## Build Scripts

For production builds:
```bash
# Frontend build
cd frontend && npm run build

# Desktop build (macOS)
cd desktop/src-tauri && cargo build --release
```
