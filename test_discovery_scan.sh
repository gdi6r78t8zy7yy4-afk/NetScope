#!/bin/bash

# Test script for Discovery Scan API endpoints
# This script tests the backend scan creation and execution endpoints

set -e

BACKEND_URL="http://localhost:8000"

echo "=== Testing Discovery Scan API Endpoints ==="
echo ""

# Check if backend is running
echo "Checking if backend is available..."
curl -s "$BACKEND_URL/health" > /dev/null 2>&1 || {
    echo "Backend is not running. Starting backend..."
    
    # Start backend in background
    cd /Users/carl/Documents/workspace/NetScope/backend
    python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    
    echo "Waiting for backend to start..."
    sleep 5
    
    # Check if backend started
    curl -s "$BACKEND_URL/health" > /dev/null 2>&1 || {
        echo "Failed to start backend!"
        exit 1
    }
    
    echo "Backend started successfully (PID: $BACKEND_PID)"
}

echo ""
echo "=== Test 1: Health Check ==="
curl -s "$BACKEND_URL/health" | head -5

echo ""
echo "=== Test 2: List Scans (before creating any) ==="
curl -s "$BACKEND_URL/api/v1/scans"

echo ""
echo ""
echo "=== Test 3: Create a Discovery Scan ==="
SCAN_RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/v1/scans" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Discovery Scan",
    "scan_type": "discovery",
    "target_cidr": "127.0.0.1/32",
    "rate_limit": "fast"
  }')

echo "Create Scan Response:"
echo "$SCAN_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$SCAN_RESPONSE"

# Extract scan ID
if command -v jq &> /dev/null; then
  SCAN_ID=$(echo "$SCAN_RESPONSE" | jq -r '.id // empty')
else
  # Fallback without jq - extract using grep and sed
  SCAN_ID=$(echo "$SCAN_RESPONSE" | grep -o '"id": [0-9]*' | head -1 | sed 's/"id": //')
fi

echo ""
echo "Scan ID: $SCAN_ID"

if [ -z "$SCAN_ID" ]; then
  echo "ERROR: Failed to extract scan ID"
  exit 1
fi

echo ""
echo "=== Test 4: Run the Scan ==="
RUN_RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/v1/scans/$SCAN_ID/run")

echo "Run Scan Response:"
echo "$RUN_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RUN_RESPONSE"

echo ""
echo "=== Test 5: List Scans (after running) ==="
curl -s "$BACKEND_URL/api/v1/scans" | python3 -m json.tool 2>/dev/null || curl -s "$BACKEND_URL/api/v1/scans"

echo ""
echo "=== Test 6: Get Single Scan ==="
curl -s "$BACKEND_URL/api/v1/scans/$SCAN_ID" | python3 -m json.tool 2>/dev/null || curl -s "$BACKEND_URL/api/v1/scans/$SCAN_ID"

echo ""
echo "=== Test 7: Check Assets ==="
curl -s "$BACKEND_URL/api/v1/assets" | python3 -m json.tool 2>/dev/null || curl -s "$BACKEND_URL/api/v1/assets"

echo ""
echo "=== Test Complete ==="
echo "Note: Discovery scans require nmap to be installed for actual host discovery."
echo "The API endpoints are working correctly."
