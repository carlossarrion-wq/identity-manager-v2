#!/bin/bash

# Script to apply migration 011: Add Token Regeneration Support
# This migration adds fields to the tokens table to support automatic token regeneration

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}Migration 011: Token Regeneration Support${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Get database credentials from AWS Secrets Manager
echo -e "${YELLOW}[1/4]${NC} Fetching database credentials from Secrets Manager..."
SECRET_NAME="identity-mgmt-dev-db-admin"
AWS_REGION="eu-west-1"

SECRET_JSON=$(aws secretsmanager get-secret-value \
    --secret-id "$SECRET_NAME" \
    --region "$AWS_REGION" \
    --query SecretString \
    --output text)

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Failed to fetch database credentials${NC}"
    exit 1
fi

DB_HOST=$(echo "$SECRET_JSON" | jq -r '.host')
DB_PORT=$(echo "$SECRET_JSON" | jq -r '.port')
DB_NAME=$(echo "$SECRET_JSON" | jq -r '.dbname')
DB_USER=$(echo "$SECRET_JSON" | jq -r '.username')
DB_PASSWORD=$(echo "$SECRET_JSON" | jq -r '.password')

echo -e "${GREEN}✓ Credentials fetched successfully${NC}"
echo -e "  Database: ${DB_NAME}"
echo -e "  Host: ${DB_HOST}"
echo ""

# Check if migration has already been applied
echo -e "${YELLOW}[2/4]${NC} Checking if migration has already been applied..."

PGPASSWORD="$DB_PASSWORD" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -t -c "SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'identity-manager-tokens-tbl' 
        AND column_name = 'regenerated_at'
    );" | grep -q 't'

if [ $? -eq 0 ]; then
    echo -e "${YELLOW}⚠ Migration appears to have been applied already${NC}"
    echo -e "${YELLOW}  Column 'regenerated_at' already exists${NC}"
    read -p "Do you want to continue anyway? (yes/no): " CONTINUE
    if [ "$CONTINUE" != "yes" ]; then
        echo -e "${BLUE}Migration cancelled${NC}"
        exit 0
    fi
else
    echo -e "${GREEN}✓ Migration has not been applied yet${NC}"
fi
echo ""

# Apply migration
echo -e "${YELLOW}[3/4]${NC} Applying migration..."
echo -e "${BLUE}  Adding regeneration fields to tokens table...${NC}"

MIGRATION_FILE="database/migrations/011_add_token_regeneration_support.sql"

if [ ! -f "$MIGRATION_FILE" ]; then
    echo -e "${RED}✗ Migration file not found: $MIGRATION_FILE${NC}"
    exit 1
fi

PGPASSWORD="$DB_PASSWORD" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -f "$MIGRATION_FILE"

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Migration failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Migration applied successfully${NC}"
echo ""

# Verify migration
echo -e "${YELLOW}[4/4]${NC} Verifying migration..."

# Check new columns
COLUMNS_ADDED=$(PGPASSWORD="$DB_PASSWORD" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -t -c "SELECT COUNT(*) FROM information_schema.columns 
           WHERE table_name = 'identity-manager-tokens-tbl' 
           AND column_name IN (
               'regenerated_at', 
               'regenerated_to_jti', 
               'regenerated_from_jti',
               'regeneration_reason',
               'regeneration_client_ip',
               'regeneration_user_agent',
               'regeneration_email_sent'
           );" | tr -d ' ')

if [ "$COLUMNS_ADDED" -eq "7" ]; then
    echo -e "${GREEN}✓ All 7 regeneration columns added successfully${NC}"
else
    echo -e "${RED}✗ Expected 7 columns, found $COLUMNS_ADDED${NC}"
    exit 1
fi

# Check indexes
INDEXES_CREATED=$(PGPASSWORD="$DB_PASSWORD" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -t -c "SELECT COUNT(*) FROM pg_indexes 
           WHERE tablename = 'identity-manager-tokens-tbl' 
           AND indexname IN (
               'idx_tokens_regenerated',
               'idx_tokens_regenerated_from',
               'idx_tokens_regenerated_to'
           );" | tr -d ' ')

if [ "$INDEXES_CREATED" -eq "3" ]; then
    echo -e "${GREEN}✓ All 3 regeneration indexes created successfully${NC}"
else
    echo -e "${YELLOW}⚠ Expected 3 indexes, found $INDEXES_CREATED${NC}"
fi

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}✓ Migration 011 completed successfully!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "${BLUE}Summary:${NC}"
echo -e "  • Added 7 regeneration tracking fields to tokens table"
echo -e "  • Created 3 indexes for efficient regeneration queries"
echo -e "  • All regeneration data stored in identity-manager-tokens-tbl"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Add custom attribute 'custom:auto_regen_tokens' to Cognito User Pool"
echo -e "  2. Implement token_regeneration_service.py in Lambda"
echo -e "  3. Add /api/tokens/regenerate endpoint"
echo ""