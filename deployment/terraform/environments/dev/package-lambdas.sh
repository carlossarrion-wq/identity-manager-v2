#!/bin/bash
# ============================================================================
# Lambda Packaging Script - Identity Manager
# ============================================================================
# Este script empaqueta las funciones Lambda con las dependencias necesarias
# excluyendo archivos innecesarios para reducir el tamaño del ZIP.
#
# Uso: ./package-lambdas.sh
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../../" && pwd)"
LAMBDA_DIR="$PROJECT_ROOT/backend/lambdas"
OUTPUT_DIR="$SCRIPT_DIR/../../lambda-packages"

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Lambda Packaging Script${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# ============================================================================
# Lambda 1: API Principal
# ============================================================================
echo -e "${YELLOW}📦 Empaquetando Lambda API...${NC}"

API_SOURCE="$LAMBDA_DIR/identity-mgmt-api"
API_OUTPUT="$OUTPUT_DIR/identity-mgmt-api-lambda-latest.zip"

if [ ! -d "$API_SOURCE" ]; then
    echo -e "${RED}❌ Error: Directorio no encontrado: $API_SOURCE${NC}"
    exit 1
fi

cd "$API_SOURCE"

# Remove old ZIP if exists
rm -f "$API_OUTPUT"

# Create ZIP excluding unnecessary files
zip -r "$API_OUTPUT" . \
    -x "venv/*" \
    -x "tests/*" \
    -x "htmlcov/*" \
    -x ".pytest_cache/*" \
    -x "*.pyc" \
    -x "__pycache__/*" \
    -x ".coverage" \
    -x "coverage.xml" \
    -x "*.egg-info/*" \
    -x ".DS_Store" \
    -x ".git/*" \
    -x ".gitignore" \
    -x "README.md" \
    -x "*.md" \
    > /dev/null 2>&1

# Get file size
API_SIZE=$(du -h "$API_OUTPUT" | cut -f1)

echo -e "${GREEN}✅ Lambda API empaquetada: $API_SIZE${NC}"
echo -e "   Ubicación: $API_OUTPUT"
echo ""

# ============================================================================
# Lambda 2: Authorizer
# ============================================================================
echo -e "${YELLOW}📦 Empaquetando Lambda Authorizer...${NC}"

AUTH_SOURCE="$LAMBDA_DIR/auth-lambda"
AUTH_OUTPUT="$OUTPUT_DIR/auth-lambda-latest.zip"

if [ ! -d "$AUTH_SOURCE" ]; then
    echo -e "${RED}❌ Error: Directorio no encontrado: $AUTH_SOURCE${NC}"
    exit 1
fi

cd "$AUTH_SOURCE"

# Remove old ZIP if exists
rm -f "$AUTH_OUTPUT"

# Create ZIP excluding unnecessary files
zip -r "$AUTH_OUTPUT" . \
    -x "venv/*" \
    -x "tests/*" \
    -x "*.pyc" \
    -x "__pycache__/*" \
    -x ".DS_Store" \
    -x ".git/*" \
    -x ".gitignore" \
    -x "README.md" \
    -x "*.md" \
    > /dev/null 2>&1

# Get file size
AUTH_SIZE=$(du -h "$AUTH_OUTPUT" | cut -f1)

echo -e "${GREEN}✅ Lambda Authorizer empaquetada: $AUTH_SIZE${NC}"
echo -e "   Ubicación: $AUTH_OUTPUT"
echo ""

# ============================================================================
# Summary
# ============================================================================
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}✅ Empaquetado completado${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "Archivos generados:"
echo -e "  1. ${GREEN}identity-mgmt-api-lambda-latest.zip${NC} ($API_SIZE)"
echo -e "  2. ${GREEN}auth-lambda-latest.zip${NC} ($AUTH_SIZE)"
echo ""
echo -e "Siguiente paso:"
echo -e "  ${YELLOW}terraform plan${NC}"
echo -e "  ${YELLOW}terraform apply${NC}"
echo ""

# Verify ZIP sizes
API_SIZE_MB=$(du -m "$API_OUTPUT" | cut -f1)
AUTH_SIZE_MB=$(du -m "$AUTH_OUTPUT" | cut -f1)

if [ "$API_SIZE_MB" -gt 50 ]; then
    echo -e "${RED}⚠️  ADVERTENCIA: Lambda API excede 50MB ($API_SIZE_MB MB)${NC}"
    echo -e "   Considera usar S3 para el deployment"
    echo ""
fi

if [ "$AUTH_SIZE_MB" -gt 50 ]; then
    echo -e "${RED}⚠️  ADVERTENCIA: Lambda Auth excede 50MB ($AUTH_SIZE_MB MB)${NC}"
    echo -e "   Considera usar S3 para el deployment"
    echo ""
fi

exit 0