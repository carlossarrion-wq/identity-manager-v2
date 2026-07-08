#!/bin/bash
# Simplified Local Development Startup Script (SQLite-based)

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Identity Manager v2 - Local Development Startup       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Set environment variables for local development
export DB_TYPE=sqlite
export DB_PATH="$SCRIPT_DIR/backend/identity_manager.db"
export JWT_SECRET_KEY=local-dev-secret-key-change-in-production
export JWT_ALGORITHM=HS256
export PORT=8000
export ENVIRONMENT=local-development
export AWS_REGION=eu-west-1

echo -e "${BLUE}[1/4]${NC} Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 found: $(python3 --version)${NC}"
echo

echo -e "${BLUE}[2/4]${NC} Setting up Python virtual environment..."
cd backend
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate

echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements-local.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo

echo -e "${BLUE}[3/4]${NC} Initializing SQLite database..."
if [ ! -f "identity_manager.db" ]; then
    python3 init_sqlite_db.py
else
    echo -e "${GREEN}✓ Database already exists at: $DB_PATH${NC}"
fi
echo

echo -e "${BLUE}[4/4]${NC} Starting backend server..."
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    Server Information                      ║${NC}"
echo -e "${GREEN}╠════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║${NC} Backend API:  http://localhost:$PORT                        ${GREEN}║${NC}"
echo -e "${GREEN}║${NC} Health Check: http://localhost:$PORT/health                 ${GREEN}║${NC}"
echo -e "${GREEN}║${NC} Database:     SQLite (${DB_PATH##*/})            ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}                                                            ${GREEN}║${NC}"
echo -e "${GREEN}║${NC} Test Credentials:                                          ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}   Email: admin@test.com                                    ${GREEN}║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo

python3 local_server.py
