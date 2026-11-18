#!/bin/bash

# NetScope Setup Script

set -e

echo "=== NetScope Setup ==="

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "Python version: $PYTHON_VERSION"

if [[ ! "$PYTHON_VERSION" =~ ^3\.1[2-9] ]]; then
    echo "Warning: Python 3.12+ required"
fi

# Setup Backend
echo ""
echo "Setting up Python backend..."
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate and install dependencies
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

# Setup Frontend
echo ""
echo "Setting up Node frontend..."
cd ../frontend

if [ ! -d "node_modules" ]; then
    npm install
fi

# Setup Desktop (Tauri)
echo ""
echo "Setting up Tauri desktop..."
cd ../desktop/src-tauri

if [ ! -f "Cargo.lock" ]; then
    cargo build --target aarch64-apple-darwin 2>/dev/null || \
    echo "Note: Run 'cargo build' manually if Rust is installed"
fi

# Return to root
cd ../../..

echo ""
echo "Setup complete!"
echo ""
echo "To start the application:"
echo "  Backend:   cd backend && source venv/bin/activate && python -m uvicorn app.main:app --reload"
echo "  Frontend:  cd frontend && npm run dev"
echo "  Desktop:   cd desktop/src-tauri && cargo build --target aarch64-apple-darwin"
