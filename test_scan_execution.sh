#!/bin/bash

echo "======================================================================"
echo "NETSCOP SCAN EXECUTION TEST"
echo "======================================================================"
echo ""

cd /Users/carl/Documents/workspace/NetScope

# Check if SECRET_KEY is set
if [ -z "$SECRET_KEY" ]; then
    echo "Warning: SECRET_KEY not set in environment"
    if [ -f ".env" ]; then
        export $(cat .env | grep SECRET_KEY)
    else
        echo "Creating test .env file..."
        echo 'SECRET_KEY=testsecretkey123forlocalhostdevelopment' > .env
    fi
fi

echo "Checking SECRET_KEY..."
if [ -n "$SECRET_KEY" ]; then
    echo "✓ SECRET_KEY is set"
else
    echo "✗ SECRET_KEY not set, using default (not recommended for production)"
fi

echo ""
echo "======================================================================"
echo "1. STARTING BACKEND SERVER (in background)..."
echo "======================================================================"

# Check if port 8000 is already in use
if lsof -i :8000 > /dev/null 2>&1; then
    echo "Warning: Port 8000 is already in use"
    read -p "Kill existing process on port 8000? (y/N) " -n 1 -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        lsof -ti :8000 | xargs kill -9 2>/dev/null
    fi
fi

# Start backend server in background
cd backend
python3 -m uvicorn app.main:app --host localhost --port 8000 --reload &
BACKEND_PID=$!
cd ..

echo "Backend server PID: $BACKEND_PID"
sleep 3

# Check if backend is running
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ Backend server is running"
    
    # Check extended health status
    curl -s http://localhost:8000/health/extended | python3 -m json.tool 2>/dev/null || echo "Extended health check (JSON format below):"
    
    # Test creating a scan
    echo ""
    echo "======================================================================"
    echo "2. TESTING SCAN CREATION AND EXECUTION..."
    echo "======================================================================"
    
    # Create a test scan
    echo ""
    echo "Creating scan..."
    CREATE_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/scans \
        -H "Content-Type: application/json" \
        -d '{
            "name": "Test Discovery Scan",
            "scan_type": "discovery",
            "target_cidr": "192.168.1.0/30",
            "rate_limit": "medium"
        }')
    
    echo "$CREATE_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "Create response:"
    echo "$CREATE_RESPONSE"
    
    # Extract scan ID
    SCAN_ID=$(echo "$CREATE_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('id', ''))" 2>/dev/null)
    
    if [ -n "$SCAN_ID" ]; then
        echo ""
        echo "✓ Scan created with ID: $SCAN_ID"
        
        # Run the scan
        echo ""
        echo "Running scan..."
        RUN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/scans/$SCAN_ID/run)
        
        echo "$RUN_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "Run response:"
        echo "$RUN_RESPONSE"
        
        # Check scan status
        sleep 2
        
        echo ""
        echo "Checking scan status..."
        STATUS_RESPONSE=$(curl -s http://localhost:8000/api/v1/scans/$SCAN_ID)
        
        echo "$STATUS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "Status response:"
        echo "$STATUS_RESPONSE"
        
        # Check queue stats
        echo ""
        echo "Checking scan queue stats..."
        QUEUE_STATS=$(curl -s http://localhost:8000/api/v1/scans/queue/stats)
        
        echo "$QUEUE_STATS" | python3 -m json.tool 2>/dev/null || echo "Queue stats:"
        echo "$QUEUE_STATS"
        
        # List all scans
        echo ""
        echo "Listing all scans..."
        ALL_SCANS=$(curl -s http://localhost:8000/api/v1/scans)
        
        echo "$ALL_SCANS" | python3 -m json.tool 2>/dev/null || echo "All scans:"
        echo "$ALL_SCANS"
        
    else
        echo ""
        echo "✗ Failed to create scan"
    fi
    
else
    echo "✗ Backend server failed to start or is not responding"
fi

echo ""
echo "======================================================================"
echo "3. CLEANUP..."
echo "======================================================================"

# Kill backend server
if [ -n "$BACKEND_PID" ]; then
    kill $BACKEND_PID 2>/dev/null
    echo "Killed backend server (PID: $BACKEND_PID)"
fi

echo ""
echo "Test completed."
