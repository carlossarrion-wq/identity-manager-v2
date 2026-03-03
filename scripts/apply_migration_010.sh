#!/bin/bash

# =====================================================
# Apply Migration 010: Add person field
# =====================================================
# This script applies migration 010 to add person field
# to bedrock-proxy tables
# =====================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Migration 010: Add person field${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if required environment variables are set
if [ -z "$DB_HOST" ] || [ -z "$DB_NAME" ] || [ -z "$DB_USER" ]; then
    echo -e "${RED}Error: Required environment variables not set${NC}"
    echo "Please set: DB_HOST, DB_NAME, DB_USER, DB_PASSWORD"
    exit 1
fi

# Prompt for password if not set
if [ -z "$DB_PASSWORD" ]; then
    echo -n "Enter database password: "
    read -s DB_PASSWORD
    echo ""
    export DB_PASSWORD
fi

MIGRATION_FILE="database/migrations/010_add_person_field.sql"

# Check if migration file exists
if [ ! -f "$MIGRATION_FILE" ]; then
    echo -e "${RED}Error: Migration file not found: $MIGRATION_FILE${NC}"
    exit 1
fi

echo -e "${YELLOW}Database: $DB_NAME@$DB_HOST${NC}"
echo -e "${YELLOW}Migration file: $MIGRATION_FILE${NC}"
echo ""

# Confirm before proceeding
read -p "Do you want to proceed with the migration? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo -e "${YELLOW}Migration cancelled${NC}"
    exit 0
fi

echo ""
echo -e "${GREEN}Applying migration...${NC}"

# Apply migration
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f $MIGRATION_FILE

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Migration applied successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${GREEN}Changes applied:${NC}"
    echo "  ✓ Added 'person' column to bedrock-proxy-usage-tracking-tbl"
    echo "  ✓ Added 'person' column to bedrock-proxy-user-quotas-tbl"
    echo "  ✓ Added 'person' column to bedrock-proxy-quota-blocks-history-tbl"
    echo "  ✓ Created indexes on person fields"
    echo "  ✓ Updated views: v_usage_detailed, v_recent_errors, v_usage_by_team"
    echo "  ✓ Created new view: v_usage_by_person"
    echo "  ✓ Updated function: check_and_update_quota()"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Update proxy-bedrock Go code to extract 'person' from JWT"
    echo "  2. Update usage tracking to include person field"
    echo "  3. Update quota check calls to pass person parameter"
    echo "  4. Test the changes in development environment"
    echo ""
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}Migration failed!${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo -e "${RED}Please check the error messages above${NC}"
    exit 1
fi