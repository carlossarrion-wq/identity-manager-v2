#!/bin/bash
###############################################################################
# Script de Pruebas para Funcionalidad de Permisos
# =================================================
# Ejecuta tests unitarios para el servicio de permisos antes del deployment
###############################################################################

set -e  # Exit on error

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Tests de Permisos - Identity Manager${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "lambda_function.py" ]; then
    echo -e "${RED}Error: Debe ejecutar este script desde el directorio backend/lambdas/identity-mgmt-api/${NC}"
    exit 1
fi

# Verificar que pytest está instalado
if ! command -v pytest &> /dev/null; then
    echo -e "${YELLOW}pytest no está instalado. Instalando dependencias de desarrollo...${NC}"
    pip3 install -r requirements-dev.txt --break-system-packages
fi

echo -e "${YELLOW}1. Ejecutando tests unitarios del servicio de permisos...${NC}"
pytest tests/unit/test_permissions_service.py -v --tb=short

echo ""
echo -e "${YELLOW}2. Ejecutando tests de validadores de permisos...${NC}"
pytest tests/unit/test_permissions_validators.py -v --tb=short

echo ""
echo -e "${YELLOW}3. Ejecutando todos los tests unitarios (incluyendo existentes)...${NC}"
pytest tests/unit/ -v --tb=short

echo ""
echo -e "${YELLOW}4. Generando reporte de cobertura...${NC}"
pytest tests/unit/test_permissions_service.py tests/unit/test_permissions_validators.py \
    --cov=services.permissions_service \
    --cov=utils.validators \
    --cov-report=term-missing \
    --cov-report=html

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✓ Tests completados exitosamente${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Reporte de cobertura HTML generado en: ${YELLOW}htmlcov/index.html${NC}"
echo ""
echo -e "${YELLOW}Próximos pasos:${NC}"
echo "  1. Revisar el reporte de cobertura"
echo "  2. Si todos los tests pasan, proceder con el deployment"
echo "  3. Ejecutar: ./scripts/deploy_lambda.sh"
echo ""
