#!/bin/bash
# ============================================================================
# Script para crear Lambda Layer con psycopg2-binary usando Docker
# ============================================================================
# Usa la imagen oficial de AWS Lambda para Python 3.12 para garantizar
# compatibilidad binaria con el entorno de ejecución de Lambda
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Creating psycopg2 Lambda Layer (Docker)${NC}"
echo -e "${GREEN}========================================${NC}"

# Variables
LAYER_DIR="backend/layers/psycopg2"
PSYCOPG2_VERSION="2.9.9"

# Clean previous builds
echo -e "${YELLOW}Cleaning previous builds...${NC}"
rm -rf "${LAYER_DIR}"
mkdir -p "${LAYER_DIR}"

# Create layer using Docker with Lambda Python 3.12 image
echo -e "${YELLOW}Building layer with Docker (Lambda Python 3.12 environment)...${NC}"
docker run --rm \
  -v "$(pwd)/${LAYER_DIR}":/output \
  public.ecr.aws/lambda/python:3.12 \
  /bin/bash -c "
    pip install psycopg2-binary==${PSYCOPG2_VERSION} -t /output/python/ --no-cache-dir && \
    find /output/python -type d -name 'tests' -exec rm -rf {} + 2>/dev/null || true && \
    find /output/python -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true && \
    find /output/python -type f -name '*.pyc' -delete 2>/dev/null || true && \
    find /output/python -type f -name '*.pyo' -delete 2>/dev/null || true && \
    cd /output && zip -r psycopg2-layer.zip python/ -q
  "

# Get file size
FILE_SIZE=$(du -h "${LAYER_DIR}/psycopg2-layer.zip" | cut -f1)

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Lambda Layer created successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Location: ${LAYER_DIR}/psycopg2-layer.zip"
echo -e "Size: ${FILE_SIZE}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Upload layer to AWS Lambda"
echo "2. Update Terraform configuration"
echo "3. Redeploy Lambda function"
echo ""
echo -e "${YELLOW}To upload to AWS:${NC}"
echo "aws lambda publish-layer-version \\"
echo "  --layer-name identity-mgmt-psycopg2-layer \\"
echo "  --description 'psycopg2-binary ${PSYCOPG2_VERSION} for PostgreSQL connections' \\"
echo "  --zip-file fileb://${LAYER_DIR}/psycopg2-layer.zip \\"
echo "  --compatible-runtimes python3.12 \\"
echo "  --region eu-west-1"
