#!/bin/bash
# =====================================================
# Initialize Identity Manager Database from EC2
# =====================================================
# This script must be run from an EC2 instance in the same VPC as RDS

set -e

echo "🚀 Identity Manager - Database Initialization"
echo "=============================================="

# Get credentials from Secrets Manager
echo "📦 Fetching credentials from Secrets Manager..."
SECRET=$(aws secretsmanager get-secret-value \
  --secret-id identity-mgmt-dev-db-admin \
  --region eu-west-1 \
  --query SecretString --output text)

DB_HOST=$(echo $SECRET | jq -r .host)
DB_PORT=$(echo $SECRET | jq -r .port)
DB_NAME=$(echo $SECRET | jq -r .dbname)
DB_USER=$(echo $SECRET | jq -r .username)
DB_PASS=$(echo $SECRET | jq -r .password)

echo "✅ Credentials retrieved"
echo "   Host: $DB_HOST"
echo "   Port: $DB_PORT"
echo "   Database: $DB_NAME"
echo ""

# Set PGPASSWORD for psql
export PGPASSWORD=$DB_PASS

# Test connection
echo "🔌 Testing database connection..."
if psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT version();" > /dev/null 2>&1; then
  echo "✅ Connection successful"
else
  echo "❌ Connection failed. Please check:"
  echo "   - EC2 is in same VPC as RDS"
  echo "   - Security Group allows PostgreSQL (5432)"
  echo "   - RDS is available"
  exit 1
fi

echo ""
echo "📊 Executing database schema..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -f ~/database/schema/identity_manager_schema_v2.sql

echo ""
echo "🌱 Loading seed data..."

echo "  → Permission types..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -f ~/database/seeds/insert_permission_types_v2.sql

echo "  → Applications..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -f ~/database/seeds/insert_applications_v2.sql

echo "  → Models..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -f ~/database/seeds/insert_models_v2.sql

echo "  → Modules..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -f ~/database/seeds/insert_modules_v2.sql

echo ""
echo "✅ Database initialized successfully!"
echo ""
echo "📋 Verification:"
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
SELECT 
  'permission_types' as table_name, 
  COUNT(*) as records 
FROM \"identity-manager-permission-types-tbl\"
UNION ALL
SELECT 'applications', COUNT(*) FROM \"identity-manager-applications-tbl\"
UNION ALL
SELECT 'models', COUNT(*) FROM \"identity-manager-models-tbl\"
UNION ALL
SELECT 'modules', COUNT(*) FROM \"identity-manager-modules-tbl\"
ORDER BY table_name;
"

echo ""
echo "🎉 All done!"
