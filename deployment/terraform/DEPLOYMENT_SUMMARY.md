# Identity Manager - Resumen de Despliegue

**Fecha:** 2026-03-10  
**Entorno:** dev  
**Región:** eu-west-1  
**Estado:** ✅ FUNCIONANDO

---

## 📊 Arquitectura Desplegada

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (CloudFront + S3)                │
│              https://dxxn3uthouo8.cloudfront.net             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ HTTPS
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              API GATEWAY (flzqvv3jt4)                        │
│      https://flzqvv3jt4.execute-api.eu-west-1.amazonaws.com │
│                                                               │
│  Authorizer: lambda-auth-authorizer (JWT custom)             │
│  - Extrae permisos del JWT                                   │
│  - Valida identity-mgmt admin                                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Lambda Invoke
                         ▼
┌─────────────────────────────────────────────────────────────┐
│           LAMBDA: identity-mgmt-dev-api-lmbd                 │
│                                                               │
│  Runtime: Python 3.12                                        │
│  Memory: 512 MB                                              │
│  Timeout: 30s                                                │
│  Layer: Klayers psycopg2-binary                              │
│  VPC: None (acceso directo a servicios)                      │
│                                                               │
│  Variables de Entorno:                                       │
│  - COGNITO_USER_POOL_ID: eu-west-1_UaMIbG9pD                │
│  - DB_SECRET_NAME: identity-mgmt-dev-db-secret              │
│  - JWT_SECRET_NAME: identity-mgmt-dev-jwt-secret            │
│  - EMAIL_SMTP_SECRET_NAME: identity-mgmt-dev-email-smtp-... │
│  - LOG_LEVEL: INFO                                           │
└────────┬──────────────┬──────────────┬──────────────────────┘
         │              │              │
         │              │              │
         ▼              ▼              ▼
┌────────────┐  ┌──────────────┐  ┌──────────────┐
│  Secrets   │  │   Cognito    │  │     RDS      │
│  Manager   │  │  User Pool   │  │  PostgreSQL  │
│            │  │              │  │              │
│ - DB creds │  │ eu-west-1_   │  │ identity-    │
│ - JWT key  │  │ UaMIbG9pD    │  │ mgmt-dev-db  │
│ - SMTP     │  │              │  │              │
└────────────┘  └──────────────┘  └──────────────┘
```

---

## 🎯 Componentes Desplegados

### 1. Frontend
- **CloudFront Distribution:** dxxn3uthouo8.cloudfront.net
- **S3 Bucket:** identity-mgmt-dev-frontend
- **Archivos:** HTML, CSS, JS
- **CORS:** Configurado para API Gateway

### 2. API Gateway
- **ID:** flzqvv3jt4
- **Nombre:** api-tool-identity-management
- **Stage:** dev
- **Authorizer:** lambda-auth-authorizer (epnglw)
- **Métodos Securizados:**
  - `/` → POST, GET, PUT, DELETE, PATCH (CUSTOM authorizer)
  - `/{proxy+}` → ANY, GET, POST, PUT, DELETE, PATCH (CUSTOM authorizer)

### 3. Lambda Functions

#### Lambda API: `identity-mgmt-dev-api-lmbd`
```yaml
Function Name: identity-mgmt-dev-api-lmbd
Runtime: python3.12
Memory: 512 MB
Timeout: 30s
Code Size: 16 MB
Layer: arn:aws:lambda:eu-west-1:770693421928:layer:Klayers-p312-psycopg2-binary:2
VPC: None
Last Modified: 2026-03-10T20:47:19Z
```

**Permisos IAM:**
- ✅ CloudWatch Logs
- ✅ Secrets Manager (GetSecretValue)
- ✅ Cognito (Admin + List operations)

**Variables de Entorno:**
```bash
COGNITO_USER_POOL_ID=eu-west-1_UaMIbG9pD
DB_SECRET_NAME=identity-mgmt-dev-db-secret
JWT_SECRET_NAME=identity-mgmt-dev-jwt-secret
EMAIL_SMTP_SECRET_NAME=identity-mgmt-dev-email-smtp-secret
LOG_LEVEL=INFO
```

#### Lambda Auth: `lambda-auth-authorizer`
```yaml
Function Name: lambda-auth-authorizer
Runtime: python3.12
Memory: 256 MB
Timeout: 30s
Type: TOKEN authorizer
VPC: None
```

### 4. RDS PostgreSQL
```yaml
Instance: identity-mgmt-dev-db
Engine: PostgreSQL 15.x
Instance Class: db.t3.micro
Storage: 20 GB (gp2)
Publicly Accessible: Yes
VPC: vpc-04ba39cd0772a280b
Subnets: subnet-038b1f57392415153, subnet-0e984b3f275d482f1
Security Group: Permite acceso desde Lambda y EC2
```

### 5. Cognito User Pool
```yaml
Pool ID: eu-west-1_UaMIbG9pD
Pool Name: identity-manager-dev-pool
Region: eu-west-1
```

### 6. Secrets Manager
```yaml
1. identity-mgmt-dev-db-secret
   - host, port, username, password, dbname

2. identity-mgmt-dev-key-access (JWT)
   - jwt_secret_key

3. identity-mgmt-dev-email-smtp-secret
   - smtp_host, smtp_port, smtp_user, smtp_password
```

---

## 🔒 Seguridad

### Autenticación y Autorización

```
1. Usuario → Login → Cognito
2. Cognito → JWT Token (estándar)
3. Backend → JWT Custom (con permisos)
4. Frontend → JWT Custom en requests
5. API Gateway → Authorizer valida JWT
6. Authorizer → Extrae permisos del JWT
7. Lambda → Valida permisos específicos
```

**Permisos en JWT Custom:**
```json
{
  "app_permissions": [
    {
      "app_id": "e61e1af9-8992-4bdf-be65-9cad86f34da0",
      "app_name": "identity-mgmt",
      "permission_type": "admin",
      "permission_level": 100
    }
  ]
}
```

### Endpoints Securizados

✅ **Todos los endpoints requieren autenticación:**
- POST, GET, PUT, DELETE, PATCH en `/`
- ANY, GET, POST, PUT, DELETE, PATCH en `/{proxy+}`

✅ **No hay Function URLs públicas**

✅ **Secrets en Secrets Manager** (no en variables de entorno)

---

## 📝 Configuración de Terraform

### Estructura

```
deployment/terraform/
├── environments/
│   └── dev/
│       ├── main.tf              # ✅ Actualizado
│       ├── variables.tf
│       └── terraform.tfvars
├── modules/
│   ├── lambda/
│   │   ├── main.tf              # ✅ Actualizado
│   │   ├── variables.tf         # ✅ Actualizado
│   │   ├── outputs.tf
│   │   └── README.md            # ✅ Nuevo
│   ├── rds/
│   ├── secrets/
│   ├── frontend/
│   └── vpc/
├── MANUAL_CHANGES_APPLIED.md    # ✅ Nuevo
└── DEPLOYMENT_SUMMARY.md        # ✅ Este archivo
```

### Cambios Aplicados en Terraform

#### 1. `modules/lambda/variables.tf`
```hcl
# Validación más flexible para function_name
validation {
  condition     = can(regex("^[a-zA-Z0-9_-]+$", var.function_name))
  error_message = "El nombre debe contener solo letras, números, guiones y guiones bajos"
}
```

#### 2. `modules/lambda/main.tf`
```hcl
# Comentarios sobre VPC
# IMPORTANTE: Esta Lambda NO debe estar en VPC a menos que:
# 1. Se cree un VPC Endpoint para Secrets Manager
# 2. Se cree un VPC Endpoint para Cognito
# 3. O las subnets tengan NAT Gateway

# Permisos de Cognito ampliados
Action = [
  "cognito-idp:AdminCreateUser",
  "cognito-idp:AdminDeleteUser",
  # ... (16 acciones en total)
]
```

#### 3. `environments/dev/main.tf`
```hcl
module "lambda" {
  function_name    = "identity-mgmt-dev-api-lmbd"  # ✅ Naming correcto
  vpc_config       = null                           # ✅ Sin VPC
  create_function_url = false                       # ✅ Sin URL pública
  
  cognito_user_pool_id = "eu-west-1_UaMIbG9pD"     # ✅ ID correcto
}
```

---

## 🚀 Deployment Process

### Código Limpio

```bash
# Crear ZIP sin venv, tests, etc.
cd backend/lambdas/identity-mgmt-api
zip -r /tmp/identity-mgmt-api-clean.zip . \
  -x "venv/*" \
  -x "tests/*" \
  -x "htmlcov/*" \
  -x ".pytest_cache/*" \
  -x "*.pyc" \
  -x "__pycache__/*"

# Resultado: 15-16 MB (vs 55+ MB original)
```

### Deployment via S3

```bash
# Subir a S3
aws s3 cp /tmp/identity-mgmt-api-clean.zip \
  s3://gestion-demanda-lambda-deployments/identity-manager/identity-mgmt-api-20260310-214628.zip

# Actualizar Lambda
aws lambda update-function-code \
  --function-name identity-mgmt-dev-api-lmbd \
  --zip-file fileb:///tmp/identity-mgmt-api-clean.zip
```

### API Gateway Update

```bash
# Actualizar integraciones
for method in POST GET PUT DELETE PATCH; do
  aws apigateway update-integration \
    --rest-api-id flzqvv3jt4 \
    --resource-id <resource-id> \
    --http-method $method \
    --patch-operations op=replace,path=/uri,value=<lambda-arn>
done

# Crear deployment
aws apigateway create-deployment \
  --rest-api-id flzqvv3jt4 \
  --stage-name dev
```

---

## 🐛 Problemas Resueltos

### 1. Lambda en VPC sin VPC Endpoints
**Síntoma:** Timeout de 30 segundos  
**Causa:** Lambda en VPC sin acceso a Secrets Manager  
**Solución:** Sacar Lambda de VPC (`vpc_config = null`)

### 2. User Pool ID Incorrecto
**Síntoma:** Error "User pool does not exist"  
**Causa:** ID `eu-west-1_Aq5Aq5Aq5` no existe  
**Solución:** Usar ID correcto `eu-west-1_UaMIbG9pD`

### 3. Métodos HTTP sin Autorización
**Síntoma:** Vulnerabilidad de seguridad  
**Causa:** PUT, DELETE, PATCH con `AuthType: NONE`  
**Solución:** Añadir CUSTOM authorizer a todos los métodos

### 4. Function URL Pública
**Síntoma:** Acceso sin autenticación  
**Causa:** Function URL con `AuthType: NONE`  
**Solución:** Eliminar Function URL

### 5. ZIP Demasiado Grande
**Síntoma:** Error `RequestEntityTooLargeException`  
**Causa:** ZIP incluye venv/ (55+ MB)  
**Solución:** Crear ZIP limpio sin venv/tests (16 MB)

### 6. CORS No Funcionando
**Síntoma:** Error "CORS Missing Allow Origin"  
**Causa:** Lambda sin código actualizado  
**Solución:** Desplegar código limpio via S3

### 7. Naming Convention Incorrecto
**Síntoma:** Lambda con nombre `lambda_identity_management_handler`  
**Causa:** Nombre no sigue convención  
**Solución:** Usar `identity-mgmt-dev-api-lmbd`

---

## ✅ Checklist de Verificación

### Pre-Deployment
- [x] ZIP limpio creado (sin venv/tests)
- [x] Tamaño < 50 MB
- [x] User Pool ID correcto
- [x] Secrets Manager configurado
- [x] VPC config = null

### Post-Deployment
- [x] Lambda actualizada
- [x] API Gateway actualizado
- [x] Deployment creado
- [x] Permisos IAM correctos
- [x] Variables de entorno configuradas
- [x] CORS funcionando
- [x] Autenticación funcionando
- [x] Dashboard cargando datos

### Seguridad
- [x] Todos los endpoints con authorizer
- [x] No hay Function URLs públicas
- [x] Secrets en Secrets Manager
- [x] Permisos IAM mínimos necesarios
- [x] CloudWatch Logs habilitados

---

## 📊 Métricas y Monitoreo

### CloudWatch Logs
```
/aws/lambda/identity-mgmt-dev-api-lmbd
/aws/lambda/lambda-auth-authorizer
```

### Métricas Clave
- **Invocations:** Número de invocaciones
- **Errors:** Errores de ejecución
- **Duration:** Tiempo de ejecución
- **Throttles:** Invocaciones limitadas

---

## 🔄 Próximos Pasos

### Alta Prioridad
1. ✅ Eliminar Lambda antigua: `lambda_identity_management_handler`
2. ⚠️ Crear módulo Terraform para API Gateway
3. ⚠️ Importar recursos existentes a Terraform

### Media Prioridad
4. Optimizar tamaño del ZIP (target: <10 MB)
5. Configurar alarmas de CloudWatch
6. Implementar Dead Letter Queue
7. Añadir X-Ray tracing

### Baja Prioridad
8. Considerar renombrar `login-authorization-service`
9. Documentar API endpoints
10. Crear tests de integración

---

## 📞 Soporte

**Documentación:**
- `/deployment/terraform/MANUAL_CHANGES_APPLIED.md`
- `/deployment/terraform/modules/lambda/README.md`
- `/docs/` (varios archivos)

**Contacto:**
- Equipo de Platform Engineering

---

**Última actualización:** 2026-03-10 21:50 CET  
**Estado:** ✅ Sistema funcionando correctamente