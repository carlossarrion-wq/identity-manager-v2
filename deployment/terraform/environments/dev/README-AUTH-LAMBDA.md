# Deployment de Auth Lambda con Terraform

## 📋 Resumen

Este documento describe cómo desplegar la Lambda de autenticación (`login-authorization-service`) usando Terraform.

## 🏗️ Arquitectura

La Lambda de autenticación incluye:

- **Runtime**: Python 3.12
- **Layer**: Klayers-p312-psycopg2-binary:2 (para PostgreSQL)
- **Dependencias incluidas**: 
  - PyJWT (generación de tokens)
  - Módulos shared (services, logging, utils)
- **Tamaño**: ~132 KB (código) + 4.2 MB (layer)

## 📦 Preparación del Paquete

Antes de desplegar con Terraform, asegúrate de que el paquete Lambda esté preparado:

```bash
cd /Users/csarrion/Cline/identity-manager-v2/backend/lambdas/auth-lambda

# 1. Copiar módulos shared (si no están)
cp -r ../../shared .

# 2. Instalar PyJWT
pip3 install PyJWT -t .

# 3. Crear ZIP para Terraform
zip -r auth-lambda.zip . -x "*.pyc" -x "__pycache__/*" -x ".DS_Store"
```

## 🚀 Deployment con Terraform

### Opción 1: Deployment Completo

```bash
cd /Users/csarrion/Cline/identity-manager-v2/deployment/terraform/environments/dev

# Inicializar Terraform (primera vez)
terraform init

# Ver plan de cambios
terraform plan

# Aplicar cambios
terraform apply
```

### Opción 2: Deployment Solo de Auth Lambda

```bash
cd /Users/csarrion/Cline/identity-manager-v2/deployment/terraform/environments/dev

# Aplicar solo el módulo de auth
terraform apply -target=module.auth_lambda
```

## ✅ Configuración Incluida

El módulo de Terraform (`auth-lambda.tf`) configura automáticamente:

### 1. **Runtime y Layers**
```hcl
runtime = "python3.12"
layers = [
  "arn:aws:lambda:eu-west-1:770693421928:layer:Klayers-p312-psycopg2-binary:2"
]
```

### 2. **Variables de Entorno**
```hcl
environment {
  variables = {
    COGNITO_USER_POOL_ID   = "eu-west-1_UaMIbG9pD"
    DB_SECRET_NAME         = "identity-mgmt-dev-db-admin"
    JWT_SECRET_NAME        = "identity-mgmt-dev-key-access"
    EMAIL_SMTP_SECRET_NAME = "identity-mgmt-dev-email-smtp"
    LOG_LEVEL              = "INFO"
  }
}
```

### 3. **Permisos IAM**

El módulo crea automáticamente las siguientes policies:

#### a) CloudWatch Logs
```json
{
  "Effect": "Allow",
  "Action": [
    "logs:CreateLogGroup",
    "logs:CreateLogStream",
    "logs:PutLogEvents"
  ],
  "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/login-authorization-service:*"
}
```

#### b) Secrets Manager
```json
{
  "Effect": "Allow",
  "Action": ["secretsmanager:GetSecretValue"],
  "Resource": [
    "arn:aws:secretsmanager:*:*:secret:identity-mgmt-dev-db-admin-*",
    "arn:aws:secretsmanager:*:*:secret:identity-mgmt-dev-key-access-*",
    "arn:aws:secretsmanager:*:*:secret:identity-mgmt-dev-email-smtp-*"
  ]
}
```

#### c) Cognito
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
    "cognito-idp:ListUsers",
    "cognito-idp:ListUsersInGroup",
    "cognito-idp:ListGroups"
  ],
  "Resource": "arn:aws:cognito-idp:eu-west-1:701055077130:userpool/eu-west-1_UaMIbG9pD"
}
```

## 🔍 Verificación Post-Deployment

### 1. Verificar Lambda creada
```bash
aws lambda get-function --function-name login-authorization-service
```

### 2. Verificar Runtime y Layer
```bash
aws lambda get-function-configuration --function-name login-authorization-service \
  --query '{Runtime:Runtime,Layers:Layers[*].Arn}' --output json
```

Debe mostrar:
```json
{
  "Runtime": "python3.12",
  "Layers": [
    "arn:aws:lambda:eu-west-1:770693421928:layer:Klayers-p312-psycopg2-binary:2"
  ]
}
```

### 3. Verificar Permisos IAM
```bash
# Obtener el rol de la Lambda
ROLE_NAME=$(aws lambda get-function-configuration \
  --function-name login-authorization-service \
  --query 'Role' --output text | awk -F'/' '{print $NF}')

# Listar policies del rol
aws iam list-role-policies --role-name $ROLE_NAME
```

### 4. Probar Lambda
```bash
# Ver logs en tiempo real
aws logs tail /aws/lambda/login-authorization-service --follow
```

## 📊 Outputs de Terraform

Después del deployment, Terraform proporciona:

```bash
terraform output auth_lambda_function_name  # login-authorization-service
terraform output auth_lambda_function_arn   # ARN completo de la Lambda
terraform output auth_lambda_role_arn       # ARN del rol IAM
```

## 🔄 Actualización de la Lambda

Para actualizar el código de la Lambda:

```bash
# 1. Preparar nuevo paquete
cd /Users/csarrion/Cline/identity-manager-v2/backend/lambdas/auth-lambda
zip -r auth-lambda.zip .

# 2. Aplicar cambios con Terraform
cd /Users/csarrion/Cline/identity-manager-v2/deployment/terraform/environments/dev
terraform apply -target=module.auth_lambda
```

## ⚠️ Notas Importantes

1. **Layer de psycopg2**: El layer es público de Klayers. Si deja de estar disponible, necesitarás crear tu propio layer.

2. **Tamaño del paquete**: El paquete completo (con shared y PyJWT) es ~132 KB, bien por debajo del límite de 50 MB para deployment directo.

3. **VPC**: La Lambda NO está en VPC para desarrollo. Puede acceder a:
   - Cognito (internet)
   - RDS (publicly_accessible)
   - Secrets Manager (internet)

4. **Secrets**: Asegúrate de que los secrets existan antes del deployment:
   - `identity-mgmt-dev-db-admin`
   - `identity-mgmt-dev-key-access`
   - `identity-mgmt-dev-email-smtp`

## 🐛 Troubleshooting

### Error: "No module named 'shared'"
```bash
# Copiar módulos shared al paquete
cd backend/lambdas/auth-lambda
cp -r ../../shared .
```

### Error: "No module named 'jwt'"
```bash
# Instalar PyJWT
cd backend/lambdas/auth-lambda
pip3 install PyJWT -t .
```

### Error: "No module named 'psycopg2'"
```bash
# Verificar que el layer esté configurado
aws lambda get-function-configuration \
  --function-name login-authorization-service \
  --query 'Layers[*].Arn'
```

## 📚 Referencias

- [Módulo Lambda](../../modules/lambda/main.tf)
- [Configuración Auth Lambda](./auth-lambda.tf)
- [Klayers - psycopg2](https://github.com/keithrozario/Klayers)