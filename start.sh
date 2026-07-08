#!/bin/bash
# Local Development Startup Script for Identity Manager v2

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Identity Manager v2 - Local Development Startup       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Check if .env.local exists, if not copy from example
if [ ! -f .env.local ]; then
    echo -e "${YELLOW}⚠️  .env.local not found, creating from example...${NC}"
    cp .env.local.example .env.local
    echo -e "${GREEN}✓ Created .env.local - please review and update as needed${NC}"
    echo
fi

# Load environment variables
if [ -f .env.local ]; then
    export $(grep -v '^#' .env.local | xargs)
fi

# Default values
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-identity_manager}
DB_USER=${DB_USER:-postgres}
DB_PASSWORD=${DB_PASSWORD:-postgres}
PORT=${PORT:-8000}

# Step 1: Check PostgreSQL connection
echo -e "${BLUE}[1/5]${NC} Checking PostgreSQL connection..."
if command -v psql &> /dev/null; then
    if PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c '\q' 2>/dev/null; then
        echo -e "${GREEN}✓ PostgreSQL is running and accessible${NC}"
    else
        echo -e "${RED}✗ Cannot connect to PostgreSQL${NC}"
        echo -e "${YELLOW}Please ensure PostgreSQL is running on $DB_HOST:$DB_PORT${NC}"
        echo -e "${YELLOW}You can start it with: docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=$DB_PASSWORD postgres:15${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  psql not found, skipping PostgreSQL check${NC}"
fi
echo

# Step 2: Create database if it doesn't exist
echo -e "${BLUE}[2/5]${NC} Checking if database '$DB_NAME' exists..."
if command -v psql &> /dev/null; then
    if PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -lqt | cut -d \| -f 1 | grep -qw $DB_NAME; then
        echo -e "${GREEN}✓ Database '$DB_NAME' already exists${NC}"
    else
        echo -e "${YELLOW}Creating database '$DB_NAME'...${NC}"
        PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "CREATE DATABASE \"$DB_NAME\";" 2>/dev/null || true
        echo -e "${GREEN}✓ Database created${NC}"
    fi
fi
echo

# Step 3: Initialize database with schema and seed data
echo -e "${BLUE}[3/5]${NC} Initializing database schema and seed data..."
cd backend
if python3 init_local_db.py; then
    echo -e "${GREEN}✓ Database initialized successfully${NC}"
else
    echo -e "${RED}✗ Database initialization failed${NC}"
    exit 1
fi
echo

# Step 4: Install Python dependencies
echo -e "${BLUE}[4/5]${NC} Installing Python dependencies..."
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements-local.txt

echo -e "${GREEN}✓ Dependencies installed${NC}"
echo

# Step 5: Start the backend server
echo -e "${BLUE}[5/5]${NC} Starting backend server..."
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    Server Information                      ║${NC}"
echo -e "${GREEN}╠════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║${NC} Backend API:  http://localhost:$PORT                        ${GREEN}║${NC}"
echo -e "${GREEN}║${NC} Health Check: http://localhost:$PORT/health                 ${GREEN}║${NC}"
echo -e "${GREEN}║${NC} Database:     $DB_HOST:$DB_PORT/$DB_NAME                ${GREEN}║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo

# Run the server
python3 local_server.py
