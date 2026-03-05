#!/bin/bash
# ============================================================================
# Script para aplicar migración 012
# ============================================================================

set -e

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Aplicando Migración 012${NC}"
echo -e "${YELLOW}Add Quota Management Fields${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

# Verificar que existe el archivo de migración
if [ ! -f "012_add_quota_management_fields.sql" ]; then
    echo -e "${RED}Error: No se encuentra el archivo 012_add_quota_management_fields.sql${NC}"
    exit 1
fi

# Solicitar credenciales si no están en variables de entorno
if [ -z "$DB_HOST" ]; then
    read -p "Database Host: " DB_HOST
fi

if [ -z "$DB_PORT" ]; then
    read -p "Database Port [5432]: " DB_PORT
    DB_PORT=${DB_PORT:-5432}
fi

if [ -z "$DB_NAME" ]; then
    read -p "Database Name: " DB_NAME
fi

if [ -z "$DB_USER" ]; then
    read -p "Database User: " DB_USER
fi

if [ -z "$PGPASSWORD" ]; then
    read -sp "Database Password: " PGPASSWORD
    echo ""
    export PGPASSWORD
fi

echo ""
echo -e "${YELLOW}Conectando a: ${DB_HOST}:${DB_PORT}/${DB_NAME}${NC}"
echo ""

# Aplicar migración
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f 012_add_quota_management_fields.sql

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ Migración 012 aplicada exitosamente${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Campos añadidos:"
    echo "  - blocked_by (VARCHAR 255)"
    echo "  - block_reason (TEXT)"
    echo "  - unblocked_at (TIMESTAMP)"
    echo "  - unblocked_by (VARCHAR 255)"
    echo "  - unblock_reason (TEXT)"
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}✗ Error al aplicar migración 012${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi