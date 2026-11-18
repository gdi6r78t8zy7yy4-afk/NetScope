#!/bin/bash

# NetScope Run Script

echo "=== NetScope Application ==="
echo ""

case "${1:-all}" in
    backend)
        echo "Starting backend server..."
        cd backend
        
        if [ ! -d "venv" ]; then
            echo "Error: Backend not installed. Run scripts/setup.sh first."
            exit 1
        fi
        
        source venv/bin/activate
        uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
        ;;
        
    frontend)
        echo "Starting frontend development server..."
        cd frontend
        
        if [ ! -d "node_modules" ]; then
            echo "Error: Frontend not installed. Run scripts/setup.sh first."
            exit 1
        fi
        
        npm run dev -- --host 0.0.0.0 --port 3000
        ;;
        
    desktop)
        echo "Building and running desktop application..."
        cd desktop/src-tauri
        
        if [ ! -f "Cargo.lock" ]; then
            echo "Error: Desktop not built. Run scripts/setup.sh first."
            exit 1
        fi
        
        cargo run --target aarch64-apple-darwin
        ;;
        
    all)
        echo "Starting all components..."
        
        # Start backend in background
        cd backend
        source venv/bin/activate
        uvicorn app.main:app --reload &
        BACKEND_PID=$!
        cd ..
        
        # Start frontend in background
        cd frontend
        npm run dev &
        FRONTEND_PID=$!
        cd ..
        
        echo "Backend PID: $BACKEND_PID"
        echo "Frontend PID: $FRONTEND_PID"
        
        # Wait for both processes
        wait
        
        ;;
        
    *)
        echo "Usage: $0 [backend|frontend|desktop|all]"
        exit 1
        ;;
esac
