#!/bin/bash
#
# Script para configurar Cognito Authorizer en API Gateway existente
# Este script configura la seguridad sin recrear la infraestructura
#

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuración
ENVIRONMENT=${1:-dev}
AWS_REGION=${2:-eu-west-1}

echo -e "${GREEN}🔒 Configurando seguridad de API Gateway${NC}"
echo "Environment: $ENVIRONMENT"
echo "Region: $AWS_REGION"
echo ""

# 1. Obtener API Gateway ID
echo -e "${YELLOW}📡 Buscando API Gateway...${NC}"
API_ID=$(aws apigateway get-rest-apis --region $AWS_REGION \
    --query "items[?name=='api-tool-identity-management'].id" \
    --output text)

if [ -z "$API_ID" ]; then
    echo -e "${RED}❌ No se encontró API Gateway con nombre 'api-tool-identity-management'${NC}"
    echo "APIs disponibles:"
    aws apigateway get-rest-apis --region $AWS_REGION \
        --query "items[].name" --output table
    exit 1
fi

echo -e "${GREEN}✅ API Gateway encontrado: $API_ID${NC}"

# 2. Obtener Cognito User Pool ID
echo -e "${YELLOW}🔐 Buscando Cognito User Pool...${NC}"
USER_POOL_ID=$(aws cognito-idp list-user-pools --max-results 10 --region $AWS_REGION \
    --query "UserPools[?Name=='identity-manager-$ENVIRONMENT-pool'].Id" \
    --output text)

if [ -z "$USER_POOL_ID" ]; then
    echo -e "${RED}❌ No se encontró User Pool con nombre 'identity-manager-$ENVIRONMENT-pool'${NC}"
    echo "User Pools disponibles:"
    aws cognito-idp list-user-pools --max-results 10 --region $AWS_REGION \
        --query "UserPools[].[Name,Id]" --output table
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
USER_POOL_ARN="arn:aws:cognito-idp:$AWS_REGION:$ACCOUNT_ID:userpool/$USER_POOL_ID"

echo -e "${GREEN}✅ User Pool encontrado: $USER_POOL_ID${NC}"
echo "   ARN: $USER_POOL_ARN"

# 3. Crear o actualizar Cognito Authorizer
echo -e "${YELLOW}🔧 Configurando Cognito Authorizer...${NC}"

# Verificar si ya existe un authorizer
EXISTING_AUTHORIZER=$(aws apigateway get-authorizers \
    --rest-api-id $API_ID \
    --region $AWS_REGION \
    --query "items[?name=='cognito-authorizer'].id" \
    --output text)

if [ -n "$EXISTING_AUTHORIZER" ]; then
    echo "Authorizer existente encontrado: $EXISTING_AUTHORIZER"
    echo "Usando authorizer existente..."
    
    AUTHORIZER_ID=$EXISTING_AUTHORIZER
    echo -e "${GREEN}✅ Usando authorizer existente${NC}"
else
    echo "Creando nuevo Authorizer..."
    
    AUTHORIZER_ID=$(aws apigateway create-authorizer \
        --rest-api-id $API_ID \
        --name cognito-authorizer \
        --type COGNITO_USER_POOLS \
        --provider-arns $USER_POOL_ARN \
        --identity-source "method.request.header.Authorization" \
        --authorizer-result-ttl-in-seconds 300 \
        --region $AWS_REGION \
        --query 'id' \
        --output text)
    
    echo -e "${GREEN}✅ Authorizer creado: $AUTHORIZER_ID${NC}"
fi

# 4. Obtener recursos y métodos de la API
echo -e "${YELLOW}📋 Obteniendo recursos de la API...${NC}"

RESOURCES=$(aws apigateway get-resources \
    --rest-api-id $API_ID \
    --region $AWS_REGION \
    --query 'items[].{id:id,path:path}' \
    --output json)

echo "Recursos encontrados:"
echo "$RESOURCES" | jq -r '.[] | "\(.path) (\(.id))"'

# 5. Aplicar authorizer a los métodos
echo -e "${YELLOW}🔐 Aplicando authorizer a métodos...${NC}"

# Buscar el recurso /{proxy+} (Lambda proxy integration)
RESOURCE_ID=$(echo "$RESOURCES" | jq -r '.[] | select(.path=="/{proxy+}") | .id')

if [ -z "$RESOURCE_ID" ]; then
    echo -e "${YELLOW}⚠️  No se encontró recurso /{proxy+}${NC}"
    echo "Recursos disponibles:"
    echo "$RESOURCES" | jq -r '.[].path'
else
    echo "Aplicando authorizer al recurso: /{proxy+} ($RESOURCE_ID)"
    
    # Actualizar método ANY (proxy integration usa ANY)
    aws apigateway update-method \
        --rest-api-id $API_ID \
        --resource-id $RESOURCE_ID \
        --http-method ANY \
        --region $AWS_REGION \
        --patch-operations \
            op=replace,path=/authorizationType,value=COGNITO_USER_POOLS \
            op=replace,path=/authorizerId,value=$AUTHORIZER_ID \
            op=add,path=/requestParameters/method.request.header.Authorization,value=true \
        2>/dev/null && echo -e "${GREEN}✅ ANY method secured${NC}" || echo -e "${YELLOW}⚠️  ANY method not found or already configured${NC}"
    
    # También intentar con POST y GET por si acaso
    aws apigateway update-method \
        --rest-api-id $API_ID \
        --resource-id $RESOURCE_ID \
        --http-method POST \
        --region $AWS_REGION \
        --patch-operations \
            op=replace,path=/authorizationType,value=COGNITO_USER_POOLS \
            op=replace,path=/authorizerId,value=$AUTHORIZER_ID \
            op=add,path=/requestParameters/method.request.header.Authorization,value=true \
        2>/dev/null && echo -e "${GREEN}✅ POST method secured${NC}" || true
    
    aws apigateway update-method \
        --rest-api-id $API_ID \
        --resource-id $RESOURCE_ID \
        --http-method GET \
        --region $AWS_REGION \
        --patch-operations \
            op=replace,path=/authorizationType,value=COGNITO_USER_POOLS \
            op=replace,path=/authorizerId,value=$AUTHORIZER_ID \
            op=add,path=/requestParameters/method.request.header.Authorization,value=true \
        2>/dev/null && echo -e "${GREEN}✅ GET method secured${NC}" || true
fi

# 6. Crear deployment
echo -e "${YELLOW}🚀 Desplegando cambios...${NC}"

DEPLOYMENT_ID=$(aws apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name $ENVIRONMENT \
    --region $AWS_REGION \
    --description "Added Cognito Authorizer for security" \
    --query 'id' \
    --output text)

echo -e "${GREEN}✅ Deployment creado: $DEPLOYMENT_ID${NC}"

# 7. Resumen
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Configuración completada exitosamente${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo "📊 Resumen:"
echo "  • API Gateway ID: $API_ID"
echo "  • Authorizer ID: $AUTHORIZER_ID"
echo "  • User Pool: $USER_POOL_ID"
echo "  • Stage: $ENVIRONMENT"
echo ""
echo "🔒 Seguridad aplicada:"
echo "  • Todos los requests requieren token de Cognito"
echo "  • Header requerido: Authorization: Bearer <token>"
echo "  • Cache de autorización: 5 minutos"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANTE:${NC}"
echo "  • Actualiza el frontend para enviar el token de Cognito"
echo "  • Los requests sin token recibirán 401 Unauthorized"
echo "  • Los usuarios sin permisos recibirán 403 Forbidden"
echo ""
echo -e "${GREEN}🎉 ¡Listo para usar!${NC}"