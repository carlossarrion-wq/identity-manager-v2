#!/bin/bash
# =====================================================
# Script para aplicar migración 009 - Campo Team
# =====================================================

set -e

echo "🔧 Aplicando migración 009: Campo Team"
echo "========================================"

# Obtener credenciales de RDS
echo "📥 Obteniendo credenciales de RDS..."
SECRET_JSON=$(aws secretsmanager get-secret-value \
  --secret-id identity-mgmt-dev-db-admin \
  --query SecretString \
  --output text)

DB_HOST=$(echo $SECRET_JSON | jq -r '.host')
DB_PORT=$(echo $SECRET_JSON | jq -r '.port')
DB_USER=$(echo $SECRET_JSON | jq -r '.username')
DB_NAME=$(echo $SECRET_JSON | jq -r '.dbname')
DB_PASS=$(echo $SECRET_JSON | jq -r '.password')

echo "✅ Credenciales obtenidas"
echo "   Host: $DB_HOST"
echo "   Port: $DB_PORT"
echo "   Database: $DB_NAME"
echo "   User: $DB_USER"
echo ""

# Ejecutar migración
echo "🚀 Ejecutando migración..."
export PGPASSWORD="$DB_PASS"

psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
  -f database/migrations/009_add_team_field.sql

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Migración aplicada exitosamente"
    echo ""
    
    # Verificar cambios
    echo "🔍 Verificando cambios..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<EOF
-- Verificar columnas agregadas
SELECT 
    table_name,
    column_name,
    data_type
FROM information_schema.columns 
WHERE column_name = 'team'
  AND table_name IN (
    'bedrock-proxy-usage-tracking-tbl',
    'bedrock-proxy-user-quotas-tbl',
    'bedrock-proxy-quota-blocks-history-tbl'
  )
ORDER BY table_name;

-- Verificar índices
SELECT 
    tablename,
    indexname
FROM pg_indexes 
WHERE indexname LIKE '%team%'
  AND tablename IN (
    'bedrock-proxy-usage-tracking-tbl',
    'bedrock-proxy-user-quotas-tbl',
    'bedrock-proxy-quota-blocks-history-tbl'
  )
ORDER BY tablename;

-- Verificar vista nueva
SELECT COUNT(*) as view_exists
FROM information_schema.views
WHERE table_name = 'v_usage_by_team';
EOF
    
    echo ""
    echo "✅ Verificación completada"
    echo ""
    echo "📊 Próximos pasos:"
    echo "   1. Actualizar proxy Bedrock (Go) para enviar campo team"
    echo "   2. Ver docs/TEAM_FIELD_MIGRATION.md para detalles"
else
    echo ""
    echo "❌ Error al aplicar migración"
    exit 1
fi

unset PGPASSWORD