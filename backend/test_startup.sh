#!/bin/bash
# Test server startup

cd "$(dirname "$0")"

export DB_TYPE=sqlite
export DB_PATH="$(pwd)/identity_manager.db"
export ENVIRONMENT=local-development
export JWT_SECRET_KEY=local-dev-secret-key
export COGNITO_USER_POOL_ID=local-dev-pool
export COGNITO_REGION=eu-west-1
export AWS_REGION=eu-west-1
export PORT=8000

echo "Starting server for 5 seconds..."
timeout 5 venv/bin/python3 local_server.py &
SERVER_PID=$!

sleep 2

echo "Testing health endpoint..."
curl -s http://localhost:8000/health || echo "Server not responding"

echo ""
echo "Testing root endpoint..."
curl -s http://localhost:8000/ || echo "Server not responding"

echo ""
echo "Testing login endpoint..."
curl -s -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com"}' || echo "Login endpoint not responding"

echo ""
echo "Stopping server..."
kill $SERVER_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null

echo ""
echo "✅ Startup test complete"
