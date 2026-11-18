# Quick Start Guide

## Prerequisites

- Python 3.9+
- Node.js 18+ (for frontend)
- npm or yarn

## Installation

### Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..
```

### Frontend Setup
```bash
cd frontend
npm install
cd ..
```

## Starting the Application

### Option 1: Using the Startup Script
```bash
chmod +x START_APPLICATION.sh
./START_APPLICATION.sh
```

### Option 2: Manual Start

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

## Accessing the Application

Once started:

- **Frontend UI:** http://localhost:5173 (or check logs/frontend.log)
- **Backend API:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs (Swagger UI)

## API Endpoints

### Root
- `GET /` - Application info
- `GET /health` - Health check

### API v1
- `GET /api/v1/networks` - List networks
- `POST /api/v1/networks` - Create network
- `GET /api/v1/assets` - List assets
- `POST /api/v1/scans` - Create scan
- `GET /api/v1/scans` - List scans
- `POST /api/v1/scans/{id}/run` - Run a scan
- `GET /api/v1/discovery/passive` - Passive discovery
- `POST /api/v1/discovery/active` - Active discovery
- `GET /api/v1/vulnerabilities` - List vulnerabilities

## Stopping the Application

```bash
pkill -f uvicorn && pkill -f vite
```

## Logs

- Backend logs: `backend/logs/backend.log`
- Frontend logs: `frontend/logs/frontend.log`

## Verification

Run tests:
```bash
cd backend
source venv/bin/activate
pytest app/tests/
```

Expected output: **164 passed**

## Configuration

Edit `backend/.env` to configure:

```env
# Backend server
BACKEND_HOST=localhost
BACKEND_PORT=8000

# Database
DATABASE_URL=sqlite+aiosqlite:///./data/netscope.db

# Scanning
DEFAULT_RATE_LIMIT=medium
SCAN_TIMEOUT_SECONDS=3600
```

## Production Deployment

For production, you should:

1. Set a secure `SECRET_KEY`
2. Configure proper database URL
3. Set up reverse proxy (nginx)
4. Enable HTTPS
5. Configure CORS for your domain
