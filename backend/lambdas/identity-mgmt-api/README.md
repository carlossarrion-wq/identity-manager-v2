# Identity Manager API Lambda

Función Lambda para gestión de usuarios de Cognito, tokens JWT y perfiles de inferencia de Bedrock.

## 📋 Información General

- **Nombre**: `identity-mgmt-<env>-api-lmbd`
- **Runtime**: Python 3.12
- **Handler**: `lambda_function.lambda_handler`
- **Timeout**: 30 segundos
- **Memoria**: 512 MB

## 🏗️ Arquitectura

```
lambda_function.py          # Handler principal y routing
├── services/
│   ├── cognito_service.py  # Gestión de usuarios Cognito
│   ├── database_service.py # Operaciones de PostgreSQL
│   └── jwt_service.py      # Generación y validación JWT
└── utils/
    ├── validators.py       # Validación de requests
    └── response_builder.py # Constructor de respuestas
```

## ⚙️ Operaciones Disponibles

### Gestión de Usuarios

#### `list_users`
Listar usuarios del User Pool de Cognito.

**Request:**
```json
{
  "operation": "list_users",
  "filters": {
    "group": "developers-group",
    "status": "CONFIRMED"
  },
  "pagination": {
    "limit": 60,
    "pagination_token": "optional_token"
  }
}
```

#### `create_user`
Crear nuevo usuario en Cognito.

**Request:**
```json
{
  "operation": "create_user",
  "data": {
    "email": "user@example.com",
    "person": "Juan Pérez García",
    "group": "developers-group",
    "temporary_password": "TempPass123!",
    "send_email": true
  }
}
```

#### `delete_user`
Eliminar usuario y todos sus datos relacionados.

**Request:**
```json
{
  "operation": "delete_user",
  "user_id": "cognito_user_id"
}
```

### Gestión de Tokens JWT

#### `list_tokens`
Listar tokens JWT.

**Request:**
```json
{
  "operation": "list_tokens",
  "filters": {
    "user_id": "optional_user_id",
    "status": "active",
    "profile_id": "optional_profile_uuid"
  },
  "pagination": {
    "limit": 50,
    "offset": 0
  }
}
```

#### `create_token`
Generar nuevo token JWT.

**Request:**
```json
{
  "operation": "create_token",
  "data": {
    "user_id": "cognito_user_id",
    "validity_period": "90_days",
    "application_profile_id": "uuid_of_profile"
  }
}
```

**Períodos de validez disponibles:**
- `1_day`: 24 horas
- `7_days`: 168 horas
- `30_days`: 720 horas
- `60_days`: 1440 horas
- `90_days`: 2160 horas (por defecto)

**Estructura del Token JWT generado:**
```json
{
  "user_id": "uuid-cognito-user",
  "email": "user@example.com",
  "default_inference_profile": "profile-uuid",
  "team": "developers-group",
  "person": "Juan Pérez García",
  "iss": "identity-manager",
  "sub": "uuid-cognito-user",
  "aud": ["bedrock-proxy", "kb-agent"],
  "exp": 1771930682,
  "iat": 1769170682,
  "jti": "unique-jwt-id-uuid"
}
```

#### `revoke_token`
Revocar token JWT sin eliminarlo.

**Request:**
```json
{
  "operation": "revoke_token",
  "token_id": "uuid",
  "reason": "Usuario cambió de rol"
}
```

#### `delete_token`
Eliminar token permanentemente de la BD.

**Request:**
```json
{
  "operation": "delete_token",
  "token_id": "uuid"
}
```

### Gestión de Perfiles y Configuración

#### `list_profiles`
Listar perfiles de inferencia disponibles.

**Request:**
```json
{
  "operation": "list_profiles",
  "filters": {
    "application_id": "optional_uuid",
    "is_active": true
  }
}
```

#### `list_groups`
Listar grupos del User Pool de Cognito.

**Request:**
```json
{
  "operation": "list_groups"
}
```

#### `get_config`
Obtener configuración del sistema.

**Request:**
```json
{
  "operation": "get_config"
}
```

## 🔧 Variables de Entorno

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `AWS_REGION` | Región de AWS | `eu-west-1` |
| `COGNITO_USER_POOL_ID` | ID del User Pool | `eu-west-1_UaMIbG9pD` |
| `DB_SECRET_NAME` | Nombre del secreto de BD | `identity-mgmt-dev-db-admin` |
| `JWT_SECRET_NAME` | Nombre del secreto JWT | `identity-mgmt-dev-jwt-secret` |
| `LOG_LEVEL` | Nivel de logging | `INFO` |

## 📦 Dependencias

Ver `requirements.txt`:
- `boto3`: AWS SDK
- `psycopg2-binary`: PostgreSQL driver
- `PyJWT`: JWT encoding/decoding
- `python-dateutil`: Utilidades de fecha

## 🚀 Deployment

### Opción 1: Script Automático

```bash
# Empaquetar y desplegar en un solo comando
./scripts/deploy_lambda.sh dev
```

### Opción 2: Paso a Paso

```bash
# 1. Empaquetar Lambda
./scripts/package_lambda.sh

# 2. Desplegar con Terraform
cd deployment/terraform/environments/dev
terraform init
terraform plan
terraform apply
```

## 🧪 Testing Local

### Invocar Lambda localmente

```bash
# Crear evento de prueba
cat > test_event.json <<EOF
{
  "body": "{\"operation\": \"get_config\"}"
}
EOF

# Invocar con AWS SAM (si está instalado)
sam local invoke -e test_event.json

# O invocar directamente en AWS
aws lambda invoke \
  --function-name identity-mgmt-dev-api-lmbd \
  --payload file://test_event.json \
  response.json

cat response.json | jq
```

### Ejemplos de Invocación

**Listar usuarios:**
```bash
aws lambda invoke \
  --function-name identity-mgmt-dev-api-lmbd \
  --payload '{"body":"{\"operation\":\"list_users\"}"}' \
  response.json
```

**Crear token:**
```bash
aws lambda invoke \
  --function-name identity-mgmt-dev-api-lmbd \
  --payload '{"body":"{\"operation\":\"create_token\",\"data\":{\"user_id\":\"user@example.com\",\"validity_period\":\"90_days\",\"application_profile_id\":\"uuid-here\"}}"}' \
  response.json
```

## 📊 Monitoreo

### CloudWatch Logs

```bash
# Ver logs en tiempo real
aws logs tail /aws/lambda/identity-mgmt-dev-api-lmbd --follow

# Buscar errores
aws logs filter-log-events \
  --log-group-name /aws/lambda/identity-mgmt-dev-api-lmbd \
  --filter-pattern "ERROR"
```

### Métricas

La Lambda incluye alarmas de CloudWatch para:
- **Errores**: > 5 errores en 5 minutos
- **Throttling**: > 5 throttles en 5 minutos
- **Duración**: > 80% del timeout

## 🔒 Permisos IAM

La Lambda tiene permisos para:
- **Cognito**: Gestión completa de usuarios y grupos
- **Secrets Manager**: Lectura de secretos (BD y JWT)
- **RDS**: Conexión a PostgreSQL (vía VPC)
- **CloudWatch**: Escritura de logs

## 🐛 Troubleshooting

### Error: "COGNITO_USER_POOL_ID no está configurado"
**Solución**: Verificar que la variable de entorno esté configurada en Terraform.

### Error: "Error accediendo a Secrets Manager"
**Solución**: Verificar que el rol de la Lambda tenga permisos para leer el secreto.

### Error: "Error de base de datos: timeout"
**Solución**: 
1. Verificar que la Lambda esté en la misma VPC que RDS
2. Verificar security groups
3. Aumentar timeout de la Lambda

### Error: "Token inválido"
**Solución**: Verificar que el secreto JWT esté configurado correctamente.

## 📝 Logs y Auditoría

Todas las operaciones se registran en:
1. **CloudWatch Logs**: Logs de ejecución de la Lambda
2. **Tabla de Auditoría**: `identity-manager-audit-tbl` en PostgreSQL

Formato de log de auditoría:
```sql
{
  "operation_type": "CREATE_TOKEN",
  "resource_type": "jwt_token",
  "resource_id": "uuid",
  "new_value": {...},
  "request_id": "lambda-request-id",
  "timestamp": "2026-02-28T13:00:00Z"
}
```

## 🔄 Actualización

Para actualizar la Lambda:

```bash
# 1. Modificar código
# 2. Ejecutar deployment
./scripts/deploy_lambda.sh dev

# Terraform detectará cambios en el ZIP y actualizará automáticamente
```

## 📚 Referencias

- [Documento de Diseño](../../../DESIGN.md)
- [Terraform Module](../../../deployment/terraform/modules/lambda/)
- [Deployment Scripts](../../../scripts/)

## 👥 Contacto

**Proyecto**: Identity Manager v5.0 (UUID Edition)
**Equipo**: TCS Team
**Región**: AWS eu-west-1
