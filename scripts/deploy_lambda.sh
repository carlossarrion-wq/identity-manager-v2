#!/bin/bash
# ============================================================================
# Script de Deployment - Identity Manager API Lambda
# ============================================================================
# Purpose: Empaquetar y desplegar la Lambda usando Terraform
# Usage: ./scripts/deploy_lambda.sh [dev|pre|pro]
# ============================================================================

set -e  # Exit on error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Validar argumentos
ENVIRONMENT=${1:-dev}

if [[ ! "$ENVIRONMENT" =~ ^(dev|pre|pro)$ ]]; then
    echo -e "${RED}Error: Entorno inválido. Usar: dev, pre o pro${NC}"
    echo "Usage: $0 [dev|pre|pro]"
    exit 1
fi

echo -e "${BLUE}=============================================="
echo "DEPLOYMENT - IDENTITY MANAGER API LAMBDA"
echo "Entorno: $ENVIRONMENT"
echo "=============================================="
echo -e "${NC}"

# Directorios
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TERRAFORM_DIR="$PROJECT_ROOT/deployment/terraform/environments/$ENVIRONMENT"

# ============================================================================
# PASO 1: Empaquetar Lambda
# ============================================================================
echo -e "${BLUE}[PASO 1/4] Empaquetando Lambda...${NC}"
echo ""

bash "$SCRIPT_DIR/package_lambda.sh"

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Error al empaquetar Lambda${NC}"
    exit 1
fi

echo ""

# ============================================================================
# PASO 2: Verificar Terraform
# ============================================================================
echo -e "${BLUE}[PASO 2/4] Verificando configuración de Terraform...${NC}"
echo ""

if [ ! -d "$TERRAFORM_DIR" ]; then
    echo -e "${RED}✗ Directorio de Terraform no encontrado: $TERRAFORM_DIR${NC}"
    exit 1
fi

cd "$TERRAFORM_DIR"

# Verificar que terraform.tfvars existe
if [ ! -f "terraform.tfvars" ]; then
    echo -e "${YELLOW}⚠ terraform.tfvars no encontrado${NC}"
    echo "Copiando desde terraform.tfvars.example..."
    if [ -f "terraform.tfvars.example" ]; then
        cp terraform.tfvars.example terraform.tfvars
        echo -e "${YELLOW}⚠ Por favor, edita terraform.tfvars con los valores correctos${NC}"
        exit 1
    else
        echo -e "${RED}✗ terraform.tfvars.example no encontrado${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✓ Configuración de Terraform verificada${NC}"
echo ""

# ============================================================================
# PASO 3: Terraform Init & Plan
# ============================================================================
echo -e "${BLUE}[PASO 3/4] Ejecutando Terraform Init & Plan...${NC}"
echo ""

# Terraform init
echo "Inicializando Terraform..."
terraform init -upgrade

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Error en terraform init${NC}"
    exit 1
fi

echo ""
echo "Ejecutando Terraform Plan..."
terraform plan -out=tfplan

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Error en terraform plan${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Terraform plan completado${NC}"
echo ""

# ============================================================================
# PASO 4: Terraform Apply
# ============================================================================
echo -e "${BLUE}[PASO 4/4] Aplicando cambios con Terraform...${NC}"
echo ""

# Pedir confirmación
echo -e "${YELLOW}¿Deseas aplicar los cambios? (yes/no)${NC}"
read -r CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo -e "${YELLOW}Deployment cancelado${NC}"
    rm -f tfplan
    exit 0
fi

# Aplicar cambios
terraform apply tfplan

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Error en terraform apply${NC}"
    rm -f tfplan
    exit 1
fi

# Limpiar plan
rm -f tfplan

echo ""
echo -e "${GREEN}=============================================="
echo "✓ DEPLOYMENT COMPLETADO"
echo "=============================================="
echo -e "${NC}"

# Mostrar outputs
echo "Outputs de Terraform:"
terraform output

echo ""
echo -e "${GREEN}Lambda desplegada correctamente en entorno: $ENVIRONMENT${NC}"
echo ""
echo "Para ver los logs:"
echo "  aws logs tail /aws/lambda/identity-mgmt-$ENVIRONMENT-api-lmbd --follow"
echo ""
echo "Para invocar la Lambda:"
echo "  aws lambda invoke --function-name identity-mgmt-$ENVIRONMENT-api-lmbd --payload '{\"operation\":\"get_config\"}' response.json"
echo ""
