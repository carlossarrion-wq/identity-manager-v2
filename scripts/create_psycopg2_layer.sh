#!/bin/bash
# ============================================================================
# Script para crear Lambda Layer con psycopg2-binary
# ============================================================================
# Crea un Lambda Layer compatible con Python 3.12 que incluye psycopg2-binary
# para conexiones a PostgreSQL desde AWS Lambda
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Creating psycopg2 Lambda Layer${NC}"
echo -e "${GREEN}========================================${NC}"

# Variables
LAYER_DIR="backend/layers/psycopg2"
PYTHON_DIR="${LAYER_DIR}/python"
ZIP_FILE="${LAYER_DIR}/psycopg2-layer.zip"
PSYCOPG2_VERSION="2.9.9"

# Clean previous builds
echo -e "${YELLOW}Cleaning previous builds...${NC}"
rm -rf "${LAYER_DIR}"
mkdir -p "${PYTHON_DIR}"

# Install psycopg2-binary
echo -e "${YELLOW}Installing psycopg2-binary ${PSYCOPG2_VERSION}...${NC}"
pip3 install psycopg2-binary==${PSYCOPG2_VERSION} -t "${PYTHON_DIR}/" --no-cache-dir

# Remove unnecessary files to reduce size
echo -e "${YELLOW}Removing unnecessary files...${NC}"
find "${PYTHON_DIR}" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find "${PYTHON_DIR}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "${PYTHON_DIR}" -type f -name "*.pyc" -delete 2>/dev/null || true
find "${PYTHON_DIR}" -type f -name "*.pyo" -delete 2>/dev/null || true
find "${PYTHON_DIR}" -type f -name "*.dist-info" -delete 2>/dev/null || true

# Create ZIP file
echo -e "${YELLOW}Creating ZIP file...${NC}"
cd "${LAYER_DIR}"
zip -r psycopg2-layer.zip python/ -q

# Get file size
FILE_SIZE=$(du -h psycopg2-layer.zip | cut -f1)

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Lambda Layer created successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Location: ${ZIP_FILE}"
echo -e "Size: ${FILE_SIZE}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Upload layer to AWS Lambda"
echo "2. Update Terraform configuration"
echo "3. Redeploy Lambda function"
echo ""
echo -e "${YELLOW}To upload manually:${NC}"
echo "aws lambda publish-layer-version \\"
echo "  --layer-name identity-mgmt-psycopg2-layer \\"
echo "  --description 'psycopg2-binary ${PSYCOPG2_VERSION} for PostgreSQL connections' \\"
echo "  --zip-file fileb://${ZIP_FILE} \\"
echo "  --compatible-runtimes python3.12 \\"
echo "  --region eu-west-1"
