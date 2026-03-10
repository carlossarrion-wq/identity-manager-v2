# Cambios Manuales Aplicados (Pendientes de Terraform)

## 📋 Resumen

Este documento lista todos los cambios aplicados manualmente vía AWS CLI que deben ser incorporados en la configuración de Terraform para el próximo despliegue.

**Fecha:** 2026-03-10
**Entorno:** dev
**Región:** eu-west-1

---

## 🔧 Cambios Aplicados

### 1. Lambda Configuration

#### ✅ Lambda: `identity-mgmt-dev-api-lmbd`

**Variables de Entorno:**
```hcl
environment {
  variables = {
    COGNITO_USER_POOL_ID   = "eu-west-1_UaMIbG9pD"  # ✅ CORRECTO
    DB_SECRET_NAME         = "identity-mgmt-dev-db-secret"
    JWT_SECRET_NAME        = "identity-mgmt-dev-jwt-secret"
    EMAIL_SMTP_SECRET_NAME = "identity-mgmt-dev-email-smtp-secret"
    LOG_LEVEL              = "INFO"
  }
}
```

**VPC Configuration:**
```hcl
# Lambda DEBE estar FUERA de VPC
vpc_config = null  # ✅ CORRECTO en main.tf
```

**Razón:** Lambda en VPC sin VPC Endpoints causa timeout al acceder a Secrets Manager y Cognito.

**Layer:**
```hcl
layers = [
  "arn:aws:lambda:eu-west-1:770693421928:layer:Klayers-p312-psycopg2-binary:2"
]
```

**Runtime:**
```hcl
runtime = "python3.12"  # ✅ CORRECTO
```

---

### 2. IAM Permissions

#### ✅ Permisos de Cognito (YA EN TERRAFORM)

El módulo Lambda ya incluye estos permisos en `modules/lambda/main.tf`:

```hcl
resource "aws_iam_role_policy" "lambda_cognito" {
  name = "${var.function_name}-cognito"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
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
        ]
        Resource = var.cognito_user_pool_arn
      }
    ]
  })
}
```

✅ **Estado:** Ya incluido en Terraform

---

### 3. API Gateway Configuration

#### ⚠️ PENDIENTE: Securizar Métodos HTTP

**Cambios aplicados manualmente:**

```bash
# Métodos en /{proxy+} que tenían AuthType: NONE
PUT    /{proxy+} → CUSTOM authorizer (epnglw)
DELETE /{proxy+} → CUSTOM authorizer (epnglw)
PATCH  /{proxy+} → CUSTOM authorizer (epnglw)
```

**Estado actual de autorizadores:**

```
Recurso: /
├─ POST   → CUSTOM (lambda-auth-authorizer) ✅
├─ GET    → CUSTOM (lambda-auth-authorizer) ✅
├─ PUT    → CUSTOM (lambda-auth-authorizer) ✅
├─ DELETE → CUSTOM (lambda-auth-authorizer) ✅
└─ PATCH  → CUSTOM (lambda-auth-authorizer) ✅

Recurso: /{proxy+}
├─ ANY    → CUSTOM (lambda-auth-authorizer) ✅
├─ GET    → COGNITO_USER_POOLS ✅
├─ POST   → COGNITO_USER_POOLS ✅
├─ PUT    → CUSTOM (lambda-auth-authorizer) ✅ [MANUAL]
├─ DELETE → CUSTOM (lambda-auth-authorizer) ✅ [MANUAL]
└─ PATCH  → CUSTOM (lambda-auth-authorizer) ✅ [MANUAL]
```

**Authorizer ID:** `epnglw`
**Authorizer Lambda:** `lambda-auth-authorizer`
**Authorizer Type:** TOKEN

⚠️ **Acción Requerida:** Crear módulo Terraform para API Gateway que incluya:
- Todos los métodos HTTP con sus autorizadores
- Configuración CORS
- Integración con Lambda
- Deployments automáticos

---

### 4. Lambda Function URL

#### ✅ Function URL Eliminada

**Cambio aplicado:**
```bash
# Lambda: identity-mgmt-dev-api-lmbd
# Function URL pública ELIMINADA (era AuthType: NONE)
aws lambda delete-function-url-config --function-name identity-mgmt-dev-api-lmbd
```

**En Terraform:**
```hcl
# En environments/dev/main.tf
module "lambda" {
  # ...
  create_function_url = false  # ⚠️ CAMBIAR A false
}
```

⚠️ **Acción Requerida:** Actualizar `create_function_url = false` en `environments/dev/main.tf`

---

### 5. API Gateway Integration

#### ⚠️ PENDIENTE: Actualizar Integraciones

**Cambios aplicados manualmente:**

Todos los métodos HTTP en `/` y `/{proxy+}` ahora apuntan a:
```
arn:aws:apigateway:eu-west-1:lambda:path/2015-03-31/functions/arn:aws:lambda:eu-west-1:701055077130:function:identity-mgmt-dev-api-lmbd/invocations
```

**Permisos de invocación:**
```bash
aws lambda add-permission \
  --function-name identity-mgmt-dev-api-lmbd \
  --statement-id apigateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:eu-west-1:701055077130:flzqvv3jt4/*"
```

⚠️ **Acción Requerida:** Crear módulo Terraform para API Gateway completo

---

## 📝 Acciones Pendientes

### Alta Prioridad

1. **Actualizar `create_function_url` en `environments/dev/main.tf`**
   ```hcl
   module "lambda" {
     # ...
     create_function_url = false  # Cambiar de true a false
   }
   ```

2. **Crear módulo Terraform para API Gateway**
   - Ubicación: `modules/api-gateway/`
   - Debe incluir:
     - Recursos y métodos HTTP
     - Autorizadores (CUSTOM y COGNITO_USER_POOLS)
     - Integraciones con Lambda
     - Configuración CORS
     - Deployments
     - Permisos de invocación

3. **Verificar User Pool ID en todas las configuraciones**
   - ✅ Correcto: `eu-west-1_UaMIbG9pD`
   - ❌ Incorrecto: `eu-west-1_Aq5Aq5Aq5` (no existe)

### Media Prioridad

4. **Eliminar Lambda antigua**
   ```bash
   aws lambda delete-function --function-name lambda_identity_management_handler
   ```
   
5. **Documentar naming conventions**
   - Lambda API: `identity-mgmt-{env}-api-lmbd`
   - Lambda Auth: `login-authorization-service` (legacy, considerar renombrar)
   - Secrets: `identity-mgmt-{env}-{type}-{detail}`

### Baja Prioridad

6. **Optimizar tamaño del ZIP de Lambda**
   - Actual: ~55MB
   - Excluir: venv/, tests/, htmlcov/, .pytest_cache/
   - Target: <20MB

---

## 🔒 Seguridad

### Vulnerabilidades Corregidas

1. ✅ **Métodos HTTP sin autorización**
   - PUT, DELETE, PATCH en `/{proxy+}` tenían `AuthType: NONE`
   - Corregido: Todos usan CUSTOM authorizer

2. ✅ **Function URL pública**
   - `identity-mgmt-dev-api-lmbd` tenía URL pública sin auth
   - Corregido: Function URL eliminada

3. ✅ **Lambda en VPC sin VPC Endpoints**
   - Lambda en VPC causaba timeout (30s) en Secrets Manager
   - Corregido: Lambda fuera de VPC

4. ✅ **User Pool ID incorrecto**
   - Lambda usaba pool inexistente
   - Corregido: `eu-west-1_UaMIbG9pD`

---

## 📊 Estado del Sistema

### ✅ Funcionando Correctamente

- Frontend (CloudFront + S3)
- Lambda API (`identity-mgmt-dev-api-lmbd`)
- Lambda Auth (`lambda-auth-authorizer`)
- RDS PostgreSQL (público, accesible)
- Secrets Manager (credenciales BD, JWT, SMTP)
- Cognito User Pool
- API Gateway (todos los endpoints securizados)

### ⚠️ Pendiente de Limpieza

- Lambda antigua: `lambda_identity_management_handler`
- Procesos background de copia de código

---

## 🎯 Próximo Despliegue con Terraform

**Antes de ejecutar `terraform apply`:**

1. Actualizar `create_function_url = false`
2. Crear módulo `api-gateway`
3. Importar recursos existentes de API Gateway:
   ```bash
   terraform import module.api_gateway.aws_api_gateway_rest_api.main flzqvv3jt4
   ```
4. Verificar plan con `terraform plan`
5. Aplicar cambios con `terraform apply`

---

## 📞 Contacto

Para dudas sobre estos cambios, contactar al equipo de Platform Engineering.

**Última actualización:** 2026-03-10 21:42 CET