# Configuración Completa de Lambdas - Identity Manager

## 📋 Resumen Ejecutivo

Este documento detalla la configuración completa y precisa de ambas Lambdas del sistema Identity Manager, lista para despliegue en un entorno limpio.

---

## 🎯 Lambda 1: API Principal

### Información Básica
```yaml
Function Name: identity-mgmt-dev-api-lmbd
Runtime: python3.12
Handler: lambda_function.lambda_handler
Memory: 512 MB
Timeout: 30 seconds
Architecture: x86_64
```

### Código Fuente
```
Ubicación: /backend/lambdas/identity-mgmt-api/
Handler: lambda_function.py
```

### Variables de Entorno
```bash
COGNITO_USER_POOL_ID=eu-west-1_UaMIbG9pD
DB_SECRET_NAME=identity-mgmt-dev-db-admin
JWT_SECRET_NAME=identity-mgmt-dev-key-access
EMAIL_SMTP_SECRET_NAME=identity-mgmt-dev-email-smtp
LOG_LEVEL=INFO
```

### Layers
```
arn:aws:lambda:eu-west-1:770693421928:layer:Klayers-p312-psycopg2-binary:2
```

### VPC Configuration
```yaml
VPC: None (sin VPC para acceso directo a servicios)
Reason: Acceso directo a Secrets Manager, Cognito y RDS público
```

### Permisos IAM Requeridos

#### 1. CloudWatch Logs
```json
{
  "Effect": "Allow",
  "Action": [
    "logs:CreateLogGroup",
    "logs:CreateLogStream",
    "logs:PutLogEvents"
  ],
  "Resource": "arn:aws:logs:eu-west-1:701055077130:log-group:/aws/lambda/identity-mgmt-dev-api-lmbd:*"
}
```

#### 2. Secrets Manager
```json
{
  "Effect": "Allow",
  "Action": "secretsmanager:GetSecretValue",
  "Resource": [
    "arn:aws:secretsmanager:eu-west-1:701055077130:secret:identity-mgmt-dev-db-admin-*",
    "arn:aws:secretsmanager:eu-west-1:701055077130:secret:identity-mgmt-dev-key-access-*",
    "arn:aws:secretsmanager:eu-west-1:701055077130:secret:identity-mgmt-dev-email-smtp-*"
  ]
}
```

#### 3. Cognito User Pool
```json
{
  "Effect": "Allow",
  "Action": [
    "cognito-idp:AdminCreateUser",
    "cognito-idp:AdminDeleteUser",
    "cognito-idp:AdminGetUser",
    "cognito-idp:AdminAddUserToGroup",
    "cognito-idp:AdminRemoveUserFromGroup",
    "cognito-idp:AdminListGroupsForUser",
    "cognito-idp:AdminSetUserPassword",
    "cognito-idp:AdminUpdateUserAttributes",
    "cognito-idp:AdminDisableUser",
    "cognito-idp:AdminEnableUser",
    "cognito-idp:ListUsers",
    "cognito-idp:ListUsersInGroup",
    "cognito-idp:ListGroups",
    "cognito-idp:GetGroup",
    "cognito-idp:CreateGroup",
    "cognito-idp:DeleteGroup",
    "cognito-idp:UpdateGroup"
  ],
  "Resource": "arn:aws:cognito-idp:eu-west-1:701055077130:userpool/eu-west-1_UaMIbG9pD"
}
```

### CORS Headers
```json
{
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
}
```

**Implementación:** En `utils/response_builder.py` - todas las respuestas incluyen headers CORS

### Empaquetado

#### Archivos a INCLUIR:
```
lambda_function.py
services/
  ├── cognito_service.py
  ├── database_service.py
  ├── jwt_service.py
  ├── email_service.py
  ├── permissions_service.py
  ├── proxy_usage_service.py
  └── token_regeneration_service.py
utils/
  ├── validators.py
  └── response_builder.py
requirements.txt dependencies:
  ├── boto3/
  ├── botocore/
  ├── jwt/
  ├── psycopg2/ (via layer)
  └── otros...
```

#### Archivos a EXCLUIR:
```
venv/
tests/
htmlcov/
.pytest_cache/
*.pyc
__pycache__/
.coverage
coverage.xml
*.egg-info/
.DS_Store
```

#### Comando de Empaquetado:
```bash
cd /backend/lambdas/identity-mgmt-api

zip -r lambda-api.zip . \
  -x "venv/*" \
  -x "tests/*" \
  -x "htmlcov/*" \
  -x ".pytest_cache/*" \
  -x "*.pyc" \
  -x "__pycache__/*" \
  -x ".coverage" \
  -x "coverage.xml" \
  -x "*.egg-info/*" \
  -x ".DS_Store"

# Tamaño esperado: 15-16 MB
```

---

## 🔐 Lambda 2: Authorizer

### Información Básica
```yaml
Function Name: lambda-auth-authorizer
Runtime: python3.12
Handler: lambda_function.lambda_handler
Memory: 256 MB
Timeout: 30 seconds
Architecture: x86_64
```

### Código Fuente
```
Ubicación: /backend/lambdas/auth-lambda/
Handler: lambda_function.py
```

### Variables de Entorno
```bash
COGNITO_USER_POOL_ID=eu-west-1_UaMIbG9pD
DB_SECRET_NAME=identity-mgmt-dev-db-admin
JWT_SECRET_NAME=identity-mgmt-dev-key-access
EMAIL_SMTP_SECRET_NAME=identity-mgmt-dev-email-smtp
LOG_LEVEL=INFO
```

### VPC Configuration
```yaml
VPC: None
```

### Permisos IAM Requeridos

#### 1. CloudWatch Logs
```json
{
  "Effect": "Allow",
  "Action": [
    "logs:CreateLogGroup",
    "logs:CreateLogStream",
    "logs:PutLogEvents"
  ],
  "Resource": "arn:aws:logs:eu-west-1:701055077130:log-group:/aws/lambda/lambda-auth-authorizer:*"
}
```

#### 2. Secrets Manager
```json
{
  "Effect": "Allow",
  "Action": "secretsmanager:GetSecretValue",
  "Resource": [
    "arn:aws:secretsmanager:eu-west-1:701055077130:secret:identity-mgmt-dev-db-admin-*",
    "arn:aws:secretsmanager:eu-west-1:701055077130:secret:identity-mgmt-dev-key-access-*",
    "arn:aws:secretsmanager:eu-west-1:701055077130:secret:identity-mgmt-dev-email-smtp-*"
  ]
}
```

#### 3. Cognito (Opcional - si valida con Cognito)
```json
{
  "Effect": "Allow",
  "Action": [
    "cognito-idp:GetUser",
    "cognito-idp:AdminGetUser"
  ],
  "Resource": "arn:aws:cognito-idp:eu-west-1:701055077130:userpool/eu-west-1_UaMIbG9pD"
}
```

### Empaquetado
```bash
cd /backend/lambdas/auth-lambda

zip -r lambda-auth.zip . \
  -x "venv/*" \
  -x "tests/*" \
  -x "*.pyc" \
  -x "__pycache__/*"

# Tamaño esperado: 5-10 MB
```

---

## 🔗 API Gateway Integration

### Authorizer Configuration
```yaml
Name: lambda-auth-authorizer
Type: TOKEN
Token Source: Authorization
Token Validation: ^Bearer [-0-9a-zA-Z\._]*$
Authorization Caching: Enabled (300 seconds)
Lambda Function: lambda-auth-authorizer
```

### Method Configuration

#### Recurso: `/`
```yaml
POST:
  Authorization: CUSTOM (lambda-auth-authorizer)
  Integration: AWS_PROXY → identity-mgmt-dev-api-lmbd
  
GET:
  Authorization: CUSTOM (lambda-auth-authorizer)
  Integration: AWS_PROXY → identity-mgmt-dev-api-lmbd
  
PUT:
  Authorization: CUSTOM (lambda-auth-authorizer)
  Integration: AWS_PROXY → identity-mgmt-dev-api-lmbd
  
DELETE:
  Authorization: CUSTOM (lambda-auth-authorizer)
  Integration: AWS_PROXY → identity-mgmt-dev-api-lmbd
  
PATCH:
  Authorization: CUSTOM (lambda-auth-authorizer)
  Integration: AWS_PROXY → identity-mgmt-dev-api-lmbd
```

#### Recurso: `/{proxy+}`
```yaml
ANY:
  Authorization: CUSTOM (lambda-auth-authorizer)
  Integration: AWS_PROXY → identity-mgmt-dev-api-lmbd
  
GET:
  Authorization: COGNITO_USER_POOLS
  Integration: AWS_PROXY → identity-mgmt-dev-api-lmbd
  
POST:
  Authorization: COGNITO_USER_POOLS
  Integration: AWS_PROXY → identity-mgmt-dev-api-lmbd
  
PUT:
  Authorization: CUSTOM (lambda-auth-authorizer)
  Integration: AWS_PROXY → identity-mgmt-dev-api-lmbd
  
DELETE:
  Authorization: CUSTOM (lambda-auth-authorizer)
  Integration: AWS_PROXY → identity-mgmt-dev-api-lmbd
  
PATCH:
  Authorization: CUSTOM (lambda-auth-authorizer)
  Integration: AWS_PROXY → identity-mgmt-dev-api-lmbd
```

### Lambda Permissions
```bash
# Permiso para API Gateway invocar Lambda API
aws lambda add-permission \
  --function-name identity-mgmt-dev-api-lmbd \
  --statement-id apigateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:eu-west-1:701055077130:flzqvv3jt4/*"

# Permiso para API Gateway invocar Lambda Authorizer
aws lambda add-permission \
  --function-name lambda-auth-authorizer \
  --statement-id apigateway-invoke-authorizer \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:eu-west-1:701055077130:flzqvv3jt4/authorizers/*"
```

---

## 📦 Secrets Manager

### Secrets Requeridos

#### 1. identity-mgmt-dev-db-admin
```json
{
  "host": "identity-mgmt-dev-db.xxx.eu-west-1.rds.amazonaws.com",
  "port": 5432,
  "username": "postgres",
  "password": "***",
  "dbname": "identity_manager_dev_rds"
}
```

#### 2. identity-mgmt-dev-key-access
```json
{
  "jwt_secret_key": "***"
}
```

#### 3. identity-mgmt-dev-email-smtp
```json
{
  "smtp_host": "smtp.gmail.com",
  "smtp_port": 587,
  "smtp_user": "***",
  "smtp_password": "***"
}
```

---

## ✅ Checklist de Despliegue

### Pre-Deployment
- [ ] Secrets Manager configurado con los 3 secrets
- [ ] Cognito User Pool creado (eu-west-1_UaMIbG9pD)
- [ ] RDS PostgreSQL desplegado y accesible
- [ ] ZIPs de Lambda creados (sin venv/tests)
- [ ] Tamaño de ZIPs verificado (<50MB)

### Lambda API Deployment
- [ ] Función Lambda creada: `identity-mgmt-dev-api-lmbd`
- [ ] Runtime: python3.12
- [ ] Handler: lambda_function.lambda_handler
- [ ] Memory: 512 MB, Timeout: 30s
- [ ] Layer psycopg2 añadido
- [ ] Variables de entorno configuradas
- [ ] VPC: None
- [ ] Permisos IAM: CloudWatch Logs
- [ ] Permisos IAM: Secrets Manager
- [ ] Permisos IAM: Cognito
- [ ] CloudWatch Log Group creado
- [ ] Código desplegado

### Lambda Auth Deployment
- [ ] Función Lambda creada: `lambda-auth-authorizer`
- [ ] Runtime: python3.12
- [ ] Memory: 256 MB, Timeout: 30s
- [ ] Variables de entorno configuradas
- [ ] VPC: None
- [ ] Permisos IAM: CloudWatch Logs
- [ ] Permisos IAM: Secrets Manager
- [ ] Código desplegado

### API Gateway Configuration
- [ ] Authorizer creado: lambda-auth-authorizer
- [ ] Métodos en `/` configurados con CUSTOM authorizer
- [ ] Métodos en `/{proxy+}` configurados
- [ ] Permisos de invocación añadidos
- [ ] Deployment creado
- [ ] CORS verificado

### Post-Deployment
- [ ] Logs de CloudWatch funcionando
- [ ] Conexión a RDS verificada
- [ ] Acceso a Secrets Manager verificado
- [ ] Cognito operations funcionando
- [ ] CORS funcionando desde frontend
- [ ] Autenticación funcionando
- [ ] Autorización funcionando

---

## 🚀 Comandos de Despliegue Rápido

### Opción 1: AWS CLI (Manual)
```bash
# 1. Crear ZIPs
cd /backend/lambdas/identity-mgmt-api
zip -r /tmp/lambda-api.zip . -x "venv/*" -x "tests/*" -x "*.pyc" -x "__pycache__/*"

cd /backend/lambdas/auth-lambda
zip -r /tmp/lambda-auth.zip . -x "venv/*" -x "tests/*" -x "*.pyc" -x "__pycache__/*"

# 2. Crear/Actualizar Lambda API
aws lambda create-function \
  --function-name identity-mgmt-dev-api-lmbd \
  --runtime python3.12 \
  --role arn:aws:iam::701055077130:role/identity-mgmt-dev-api-lmbd-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb:///tmp/lambda-api.zip \
  --timeout 30 \
  --memory-size 512 \
  --layers arn:aws:lambda:eu-west-1:770693421928:layer:Klayers-p312-psycopg2-binary:2 \
  --environment "Variables={COGNITO_USER_POOL_ID=eu-west-1_UaMIbG9pD,DB_SECRET_NAME=identity-mgmt-dev-db-admin,JWT_SECRET_NAME=identity-mgmt-dev-key-access,EMAIL_SMTP_SECRET_NAME=identity-mgmt-dev-email-smtp,LOG_LEVEL=INFO}"

# 3. Crear/Actualizar Lambda Auth
aws lambda create-function \
  --function-name lambda-auth-authorizer \
  --runtime python3.12 \
  --role arn:aws:iam::701055077130:role/lambda-auth-authorizer-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb:///tmp/lambda-auth.zip \
  --timeout 30 \
  --memory-size 256 \
  --environment "Variables={COGNITO_USER_POOL_ID=eu-west-1_UaMIbG9pD,DB_SECRET_NAME=identity-mgmt-dev-db-admin,JWT_SECRET_NAME=identity-mgmt-dev-key-access,EMAIL_SMTP_SECRET_NAME=identity-mgmt-dev-email-smtp,LOG_LEVEL=INFO}"
```

### Opción 2: Terraform (Recomendado)
```bash
cd deployment/terraform/environments/dev

# 1. Actualizar ZIPs
./package-lambdas.sh

# 2. Aplicar Terraform
terraform plan
terraform apply
```

---

## 📝 Notas Importantes

### Seguridad
1. ✅ **Sin Function URLs públicas** - Solo acceso via API Gateway
2. ✅ **Todos los endpoints con authorizer** - Sin endpoints públicos
3. ✅ **Secrets en Secrets Manager** - No en variables de entorno
4. ✅ **CORS configurado** - Headers en todas las respuestas
5. ✅ **Permisos IAM mínimos** - Solo lo necesario

### Performance
1. ✅ **Sin VPC** - Menor latencia, sin cold starts largos
2. ✅ **Layer para psycopg2** - Reduce tamaño del ZIP
3. ✅ **Memory optimizada** - 512MB para API, 256MB para Auth
4. ✅ **Timeout adecuado** - 30s suficiente

### Mantenibilidad
1. ✅ **Código modularizado** - Services separados
2. ✅ **CORS centralizado** - En response_builder
3. ✅ **Logging completo** - CloudWatch Logs
4. ✅ **Auditoría** - Todas las operaciones registradas

---

**Última actualización:** 2026-03-10 21:56 CET