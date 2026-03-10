# Lambda Module - Identity Manager

## Descripción

Módulo de Terraform para desplegar funciones Lambda de Identity Manager con todas las configuraciones necesarias de IAM, CloudWatch, VPC y seguridad.

## Uso

```hcl
module "lambda" {
  source = "../../modules/lambda"

  function_name    = "identity-mgmt-dev-api-lmbd"
  lambda_zip_path  = "/path/to/lambda.zip"
  
  timeout          = 30
  memory_size      = 512
  log_level        = "INFO"
  
  # Cognito Configuration
  cognito_user_pool_id  = "eu-west-1_UaMIbG9pD"
  cognito_user_pool_arn = "arn:aws:cognito-idp:eu-west-1:123456789012:userpool/eu-west-1_UaMIbG9pD"
  
  # Secrets Manager
  db_secret_name         = "identity-mgmt-dev-db-secret"
  db_secret_arn          = "arn:aws:secretsmanager:..."
  jwt_secret_name        = "identity-mgmt-dev-jwt-secret"
  jwt_secret_arn         = "arn:aws:secretsmanager:..."
  email_smtp_secret_name = "identity-mgmt-dev-email-smtp-secret"
  email_smtp_secret_arn  = "arn:aws:secretsmanager:..."
  
  # VPC Configuration - DISABLED (recomendado)
  vpc_config = null
  
  # Optional features
  enable_xray          = true
  create_function_url  = false  # SECURITY: No public URL
  create_alarms        = false
  
  tags = {
    Environment = "dev"
    Application = "identity-manager"
  }
}
```

## ⚠️ Configuración de VPC - IMPORTANTE

### Lambda SIN VPC (Recomendado)

**Por defecto, la Lambda NO debe estar en VPC** para evitar problemas de conectividad.

```hcl
vpc_config = null  # ✅ RECOMENDADO
```

**Razones:**
- ✅ Acceso directo a Secrets Manager (sin timeout)
- ✅ Acceso directo a Cognito (sin timeout)
- ✅ Acceso a RDS público (con security groups)
- ✅ Sin necesidad de VPC Endpoints
- ✅ Sin necesidad de NAT Gateway
- ✅ Menor latencia
- ✅ Menor costo

### Lambda CON VPC (Solo si es necesario)

Si necesitas que la Lambda esté en VPC, **DEBES** cumplir uno de estos requisitos:

**Opción 1: VPC Endpoints (Recomendado)**
```hcl
# Crear VPC Endpoints para:
# - com.amazonaws.region.secretsmanager
# - com.amazonaws.region.cognito-idp
# - com.amazonaws.region.rds (si RDS es privado)

vpc_config = {
  subnet_ids         = ["subnet-xxx", "subnet-yyy"]  # Subnets PRIVADAS
  security_group_ids = ["sg-xxx"]
}
```

**Opción 2: NAT Gateway**
```hcl
# Subnets privadas con ruta a NAT Gateway
vpc_config = {
  subnet_ids         = ["subnet-xxx", "subnet-yyy"]  # Con NAT
  security_group_ids = ["sg-xxx"]
}
```

**❌ Sin VPC Endpoints ni NAT Gateway:**
```hcl
# ❌ ESTO CAUSARÁ TIMEOUT de 30 segundos
vpc_config = {
  subnet_ids         = ["subnet-xxx", "subnet-yyy"]  # Sin internet
  security_group_ids = ["sg-xxx"]
}
# Error: Timeout al acceder a Secrets Manager y Cognito
```

## Permisos IAM

El módulo crea automáticamente los siguientes permisos:

### 1. CloudWatch Logs
```json
{
  "Effect": "Allow",
  "Action": [
    "logs:CreateLogGroup",
    "logs:CreateLogStream",
    "logs:PutLogEvents"
  ],
  "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/*"
}
```

### 2. Secrets Manager
```json
{
  "Effect": "Allow",
  "Action": [
    "secretsmanager:GetSecretValue"
  ],
  "Resource": [
    "<db_secret_arn>",
    "<jwt_secret_arn>",
    "<email_smtp_secret_arn>"
  ]
}
```

### 3. Cognito
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
  "Resource": "<cognito_user_pool_arn>"
}
```

### 4. VPC (Solo si vpc_config != null)
```json
{
  "Effect": "Allow",
  "Action": [
    "ec2:CreateNetworkInterface",
    "ec2:DescribeNetworkInterfaces",
    "ec2:DeleteNetworkInterface",
    "ec2:AssignPrivateIpAddresses",
    "ec2:UnassignPrivateIpAddresses"
  ],
  "Resource": "*"
}
```

## Variables de Entorno

El módulo configura automáticamente estas variables de entorno en la Lambda:

```bash
COGNITO_USER_POOL_ID    = "<cognito_user_pool_id>"
DB_SECRET_NAME          = "<db_secret_name>"
JWT_SECRET_NAME         = "<jwt_secret_name>"
EMAIL_SMTP_SECRET_NAME  = "<email_smtp_secret_name>"
LOG_LEVEL               = "<log_level>"
```

## Lambda Layer

El módulo incluye automáticamente el layer de psycopg2:

```hcl
layers = [
  "arn:aws:lambda:eu-west-1:770693421928:layer:Klayers-p312-psycopg2-binary:2"
]
```

## Runtime

```hcl
runtime = "python3.12"
```

## Deployment

### Opción 1: ZIP Local (< 50MB)

```hcl
module "lambda" {
  lambda_zip_path = "/path/to/lambda.zip"
  s3_bucket       = null
  s3_key          = null
}
```

### Opción 2: S3 (> 50MB)

```hcl
module "lambda" {
  lambda_zip_path = "/path/to/lambda.zip"  # Para calcular hash
  s3_bucket       = "my-lambda-deployments"
  s3_key          = "identity-manager/lambda-20260310.zip"
}
```

## Crear ZIP Limpio

Para evitar que el ZIP sea demasiado grande:

```bash
cd backend/lambdas/identity-mgmt-api

# Crear ZIP sin venv, tests, etc.
zip -r lambda.zip . \
  -x "venv/*" \
  -x "tests/*" \
  -x "htmlcov/*" \
  -x ".pytest_cache/*" \
  -x "*.pyc" \
  -x "__pycache__/*" \
  -x ".coverage" \
  -x "coverage.xml"

# Verificar tamaño
ls -lh lambda.zip
```

## Outputs

```hcl
output "function_name" {
  description = "Nombre de la función Lambda"
  value       = module.lambda.function_name
}

output "function_arn" {
  description = "ARN de la función Lambda"
  value       = module.lambda.function_arn
}

output "role_arn" {
  description = "ARN del rol IAM"
  value       = module.lambda.role_arn
}

output "function_url" {
  description = "Function URL (si create_function_url = true)"
  value       = module.lambda.function_url
}
```

## Alarmas de CloudWatch

Si `create_alarms = true`, se crean automáticamente:

1. **Errores**: > 5 errores en 5 minutos
2. **Throttles**: > 5 throttles en 5 minutos
3. **Duración**: > 80% del timeout

## Seguridad

### Function URL

```hcl
create_function_url = false  # ✅ RECOMENDADO
```

**⚠️ NUNCA usar Function URL en producción sin autenticación**

Si necesitas Function URL para testing:
```hcl
create_function_url = true
# Pero SIEMPRE con authorization_type = "AWS_IAM"
```

### Secrets Manager

Todos los secretos se acceden via Secrets Manager, nunca como variables de entorno directas.

## Troubleshooting

### Error: Timeout de 30 segundos

**Causa:** Lambda en VPC sin VPC Endpoints ni NAT Gateway

**Solución:**
```hcl
vpc_config = null  # Sacar Lambda de VPC
```

### Error: User Pool no existe

**Causa:** User Pool ID incorrecto

**Solución:**
```bash
# Listar User Pools
aws cognito-idp list-user-pools --max-results 10

# Usar el ID correcto
cognito_user_pool_id = "eu-west-1_XXXXXXX"
```

### Error: ZIP demasiado grande

**Causa:** ZIP incluye venv/, tests/, etc.

**Solución:** Crear ZIP limpio (ver sección "Crear ZIP Limpio")

## Ejemplos

### Lambda API (Principal)

```hcl
module "lambda_api" {
  source = "../../modules/lambda"

  function_name    = "identity-mgmt-dev-api-lmbd"
  lambda_zip_path  = "/path/to/api-lambda.zip"
  
  timeout          = 30
  memory_size      = 512
  
  cognito_user_pool_id  = "eu-west-1_UaMIbG9pD"
  cognito_user_pool_arn = "arn:aws:cognito-idp:..."
  
  db_secret_name         = "identity-mgmt-dev-db-secret"
  db_secret_arn          = "arn:aws:secretsmanager:..."
  jwt_secret_name        = "identity-mgmt-dev-jwt-secret"
  jwt_secret_arn         = "arn:aws:secretsmanager:..."
  email_smtp_secret_name = "identity-mgmt-dev-email-smtp-secret"
  email_smtp_secret_arn  = "arn:aws:secretsmanager:..."
  
  vpc_config = null  # Sin VPC
  
  enable_xray          = true
  create_function_url  = false
  create_alarms        = false
}
```

### Lambda Authorizer

```hcl
module "lambda_auth" {
  source = "../../modules/lambda"

  function_name    = "login-authorization-service"
  lambda_zip_path  = "/path/to/auth-lambda.zip"
  
  timeout          = 30
  memory_size      = 256
  
  cognito_user_pool_id  = "eu-west-1_UaMIbG9pD"
  cognito_user_pool_arn = "arn:aws:cognito-idp:..."
  
  db_secret_name         = "identity-mgmt-dev-db-secret"
  db_secret_arn          = "arn:aws:secretsmanager:..."
  jwt_secret_name        = "identity-mgmt-dev-jwt-secret"
  jwt_secret_arn         = "arn:aws:secretsmanager:..."
  email_smtp_secret_name = "identity-mgmt-dev-email-smtp-secret"
  email_smtp_secret_arn  = "arn:aws:secretsmanager:..."
  
  vpc_config = null
  
  enable_xray          = false
  create_function_url  = false
  create_alarms        = false
  log_retention_days   = 7
}
```

## Naming Conventions

### Recomendado

- Lambda API: `identity-mgmt-{env}-api-lmbd`
  - Ejemplo: `identity-mgmt-dev-api-lmbd`
- Lambda Auth: `login-authorization-service` (legacy)
  - Considerar renombrar a: `identity-mgmt-{env}-auth-lmbd`

### Secrets

- DB: `identity-mgmt-{env}-db-secret`
- JWT: `identity-mgmt-{env}-key-access`
- SMTP: `identity-mgmt-{env}-email-smtp-secret`

## Changelog

### 2026-03-10
- ✅ Actualizada validación de `function_name` (más flexible)
- ✅ Documentación completa de VPC
- ✅ Permisos de Cognito ampliados
- ✅ Comentarios sobre VPC Endpoints
- ✅ Ejemplos de uso

### 2026-03-03
- ✅ Versión inicial del módulo
- ✅ Soporte para VPC
- ✅ Permisos IAM básicos
- ✅ CloudWatch Logs

## Soporte

Para dudas o problemas, consultar:
- `/deployment/terraform/MANUAL_CHANGES_APPLIED.md`
- Equipo de Platform Engineering