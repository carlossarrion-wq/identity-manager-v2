#!/bin/bash
# ============================================================================
# Script para Empaquetar Lambda - Identity Manager API
# ============================================================================
# Purpose: Crear archivo ZIP con el código de la Lambda y sus dependencias
# Usage: ./scripts/package_lambda.sh
# ============================================================================

set -e  # Exit on error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=============================================="
echo "EMPAQUETADO DE LAMBDA - IDENTITY MANAGER API"
echo "=============================================="
echo -e "${NC}"

# Directorios
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LAMBDA_DIR="$PROJECT_ROOT/backend/lambdas/identity-mgmt-api"
BUILD_DIR="$PROJECT_ROOT/build/lambda"
OUTPUT_DIR="$PROJECT_ROOT/deployment/terraform/lambda-packages"

# Limpiar directorio de build
echo -e "${YELLOW}[1/5]${NC} Limpiando directorio de build..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
mkdir -p "$OUTPUT_DIR"
echo -e "${GREEN}✓ Directorio limpio${NC}"
echo ""

# Copiar código de la Lambda
echo -e "${YELLOW}[2/5]${NC} Copiando código de la Lambda..."
cp -r "$LAMBDA_DIR"/* "$BUILD_DIR/"
echo -e "${GREEN}✓ Código copiado${NC}"
echo ""

# Instalar dependencias
echo -e "${YELLOW}[3/5]${NC} Instalando dependencias de Python..."
if [ -f "$BUILD_DIR/requirements.txt" ]; then
    # Excluir psycopg2-binary ya que viene del Klayers Lambda Layer
    grep -v "psycopg2-binary" "$BUILD_DIR/requirements.txt" > "$BUILD_DIR/requirements-no-psycopg2.txt" || true
    if [ -s "$BUILD_DIR/requirements-no-psycopg2.txt" ]; then
        pip3 install -r "$BUILD_DIR/requirements-no-psycopg2.txt" -t "$BUILD_DIR/" --upgrade --quiet
    fi
    rm -f "$BUILD_DIR/requirements-no-psycopg2.txt"
    echo -e "${GREEN}✓ Dependencias instaladas (psycopg2-binary viene del Klayers Layer)${NC}"
else
    echo -e "${RED}✗ No se encontró requirements.txt${NC}"
    exit 1
fi
echo ""

# Limpiar archivos innecesarios
echo -e "${YELLOW}[4/5]${NC} Limpiando archivos innecesarios..."
cd "$BUILD_DIR"

# IMPORTANTE: Eliminar venv que se copió del código fuente
rm -rf venv/ 2>/dev/null || true
rm -rf .venv/ 2>/dev/null || true
rm -rf env/ 2>/dev/null || true

# Eliminar archivos de tests
rm -rf tests/ 2>/dev/null || true
rm -f test_*.py 2>/dev/null || true
rm -f *_test.py 2>/dev/null || true
rm -f pytest.ini 2>/dev/null || true
rm -f .coverage 2>/dev/null || true
rm -f coverage.xml 2>/dev/null || true
rm -rf htmlcov/ 2>/dev/null || true
rm -rf .pytest_cache/ 2>/dev/null || true

# Eliminar archivos de desarrollo
rm -f requirements-dev.txt 2>/dev/null || true
rm -f README.md 2>/dev/null || true
rm -f TESTING_STRATEGY.md 2>/dev/null || true
rm -f run_permissions_tests.sh 2>/dev/null || true

# Limpiar cache y archivos temporales
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type f -name ".DS_Store" -delete 2>/dev/null || true

echo -e "${GREEN}✓ Archivos limpiados (venv, tests y dev files excluidos)${NC}"
echo ""

# Crear archivo ZIP
echo -e "${YELLOW}[5/5]${NC} Creando archivo ZIP..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ZIP_NAME="identity-mgmt-api-lambda-${TIMESTAMP}.zip"
ZIP_PATH="$OUTPUT_DIR/$ZIP_NAME"

zip -r "$ZIP_PATH" . -q

# Crear symlink al último build
cd "$OUTPUT_DIR"
ln -sf "$ZIP_NAME" "identity-mgmt-api-lambda-latest.zip"

ZIP_SIZE=$(du -h "$ZIP_PATH" | cut -f1)
echo -e "${GREEN}✓ Archivo ZIP creado${NC}"
echo ""

# Resumen
echo -e "${GREEN}=============================================="
echo "✓ EMPAQUETADO COMPLETADO"
echo "=============================================="
echo -e "${NC}"
echo "Archivo ZIP: $ZIP_PATH"
echo "Tamaño: $ZIP_SIZE"
echo "Symlink: $OUTPUT_DIR/identity-mgmt-api-lambda-latest.zip"
echo ""
echo "Para desplegar con Terraform:"
echo "  cd deployment/terraform/environments/dev"
echo "  terraform apply"
echo ""
