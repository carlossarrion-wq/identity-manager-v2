#!/bin/bash
# =====================================================
# SCRIPT DE INICIALIZACIÓN DE BD - UUID VERSION
# =====================================================
# Purpose: Inicializar la base de datos con esquema UUID
# Version: 3.0
# Date: 2026-02-27
# =====================================================

set -e  # Exit on error

echo "=============================================="
echo "IDENTITY MANAGER - INICIALIZACIÓN BD (UUID)"
echo "=============================================="
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# =====================================================
# 1. OBTENER CREDENCIALES DE SECRETS MANAGER
# =====================================================
echo -e "${YELLOW}[1/5]${NC} Obteniendo credenciales de AWS Secrets Manager..."

SECRET_NAME="identity-mgmt-dev-db-admin"
REGION="eu-west-1"

SECRET_JSON=$(aws secretsmanager get-secret-value \
    --secret-id $SECRET_NAME \
    --region $REGION \
    --query SecretString \
    --output text 2>&1)

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Error al obtener credenciales de Secrets Manager${NC}"
    echo "$SECRET_JSON"
    exit 1
fi

# Extraer valores del JSON
export PGPASSWORD=$(echo $SECRET_JSON | jq -r .password)
DB_HOST=$(echo $SECRET_JSON | jq -r .host)
DB_PORT=$(echo $SECRET_JSON | jq -r .port)
DB_USER=$(echo $SECRET_JSON | jq -r .username)
DB_NAME=$(echo $SECRET_JSON | jq -r .dbname)

echo -e "${GREEN}✓ Credenciales obtenidas correctamente${NC}"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo ""

# =====================================================
# 2. PROBAR CONEXIÓN
# =====================================================
echo -e "${YELLOW}[2/5]${NC} Probando conexión a RDS..."

psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT version();" > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ No se pudo conectar a la base de datos${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Conexión exitosa${NC}"
echo ""

# =====================================================
# 3. CREAR ESQUEMA (UUID VERSION)
# =====================================================
echo -e "${YELLOW}[3/5]${NC} Creando esquema de base de datos (UUID version)..."

psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
    -f ~/database/schema/identity_manager_schema_v3_uuid.sql

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Error al crear el esquema${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Esquema creado correctamente${NC}"
echo ""

# =====================================================
# 4. INSERTAR DATOS INICIALES
# =====================================================
echo -e "${YELLOW}[4/5]${NC} Insertando datos iniciales..."

psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
    -f ~/database/seeds/insert_data_v3_uuid.sql

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Error al insertar datos iniciales${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Datos iniciales insertados correctamente${NC}"
echo ""

# =====================================================
# 5. VERIFICAR INSTALACIÓN
# =====================================================
echo -e "${YELLOW}[5/5]${NC} Verificando instalación..."
echo ""

# Listar tablas
echo "Tablas creadas:"
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "\dt" | grep "identity-manager"

echo ""
echo "Vistas creadas:"
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "\dv" | grep "v_"

echo ""
echo "Resumen de datos:"
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME <<EOF
SELECT 
    'Tipos de permisos' as tabla, 
    COUNT(*)::text as registros 
FROM "identity-manager-permission-types-tbl"
UNION ALL
SELECT 'Modelos LLM', COUNT(*)::text FROM "identity-manager-models-tbl"
UNION ALL
SELECT 'Aplicaciones', COUNT(*)::text FROM "identity-manager-applications-tbl"
UNION ALL
SELECT 'Módulos', COUNT(*)::text FROM "identity-manager-modules-tbl"
UNION ALL
SELECT 'Configuraciones', COUNT(*)::text FROM "identity-manager-config-tbl";
EOF

echo ""
echo -e "${GREEN}=============================================="
echo "✓ INICIALIZACIÓN COMPLETADA EXITOSAMENTE"
echo "=============================================="
echo -e "${NC}"
echo "Base de datos lista para usar con UUIDs"
echo ""
echo "Ejemplo de consulta:"
echo "  psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME"
echo ""

# Limpiar variable de password
unset PGPASSWORD
