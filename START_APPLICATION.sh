#!/bin/bash

# NetScope Application Startup Script
# This script starts both backend and frontend servers

set -e

cd "$(dirname "$0")"

echo "========================================"
echo "    NetScope Application Startup"
echo "========================================"
echo ""

# Check if backend virtual environment exists
if [ ! -d "backend/venv" ]; then
    echo "❌ Backend virtual environment not found!"
    echo "   Please run: cd backend && python3 -m venv venv"
    exit 1
fi

# Check if node_modules exists
if [ ! -d "frontend/node_modules" ]; then
    echo "❌ Frontend dependencies not found!"
    echo "   Please run: cd frontend && npm install"
    exit 1
fi

# Start backend server in background
echo "🚀 Starting Backend Server..."
cd backend
source venv/bin/activate

# Create logs directory if it doesn't exist
mkdir -p logs

# Start uvicorn server in background
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"
cd ..

# Wait for backend to start
sleep 3

# Check if backend is running
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is running on http://localhost:8000"
else
    echo "❌ Backend failed to start. Check logs/backend.log for details."
    exit 1
fi

# Start frontend development server in background
echo ""
echo "🚀 Starting Frontend Server..."
cd frontend

# Start vite dev server in background
nohup npm run dev > logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"
cd ..

# Wait for frontend to start
sleep 5

echo ""
echo "========================================"
echo "    Application Started Successfully!"
echo "========================================"
echo ""
echo "📊 Open the following URLs in your browser:"
echo "   Frontend: http://localhost:5173 (or check logs/frontend.log)"
echo "   Backend API: http://localhost:8000"
echo ""
echo "📝 View logs:"
echo "   Backend logs: backend/logs/backend.log"
echo "   Frontend logs: frontend/logs/frontend.log"
echo ""
echo "🛑 To stop the servers, run:"
echo "   pkill -f uvicorn && pkill -f vite"
echo ""
