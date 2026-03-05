# Proxy Bedrock

## 📋 Visión General

El Proxy Bedrock es un servidor HTTP escrito en Go que actúa como intermediario entre aplicaciones cliente y AWS Bedrock, proporcionando autenticación, control de cuotas, métricas y traducción de formatos.

## 🎯 Características

### Autenticación JWT
- Validación de tokens JWT
- Extracción de claims (user_id, team, person)
- Verificación de permisos en base de datos
- Soporte para regeneración automática

### Control de Cuotas
- Límites diarios por usuario/equipo
- Verificación antes de cada request
- Actualización atómica de contadores
- Reset automático diario (00:00 UTC)

### Métricas y Tracking
- Registro de uso en tiempo real
- Cálculo de costos por modelo
- Tracking de tokens (input, output, cache)
- Worker asíncrono para no bloquear requests

### Traducción de Formatos
- Anthropic Messages API → AWS Bedrock Converse API
- Soporte para streaming (SSE)
- Buffer inteligente para tags XML
- Traducción de herramientas (tools)

## 🏗️ Arquitectura

```
Client Request
    ↓
Logging Middleware (amslog)
    ↓
Auth Middleware (JWT validation)
    ↓
Quota Middleware (check limits)
    ↓
Format Translator
    ↓
AWS Bedrock Client
    ↓
Stream Processor
    ↓
Metrics Worker (async)
    ↓
Database (save metrics)
```

## 🔐 Autenticación

### JWT Token Structure

```json
{
  "user_id": "cognito_user_id",
  "email": "user@example.com",
  "team": "developers-group",
  "person": "John Doe",
  "default_inference_profile": "profile_arn",
  "iss": "identity-manager",
  "aud": ["bedrock-proxy"],
  "exp": 1771930682,
  "iat": 1769170682,
  "jti": "unique-jwt-id"
}
```

### Validación

1. Extraer token del header `Authorization: Bearer <token>`
2. Validar firma HMAC-SHA256
3. Verificar expiración
4. Calcular hash del token
5. Buscar en base de datos
6. Verificar que no esté revocado
7. Actualizar `last_used_at`

## 📊 Control de Cuotas

### Tabla: bedrock-proxy-user-quotas-tbl

```sql
- cognito_user_id
- daily_token_limit (default: 1,000,000)
- tokens_used_today
- last_reset_date
- is_blocked
- blocked_reason
```

### Flujo de Verificación

1. Obtener cuota del usuario
2. Verificar si está bloqueado
3. Verificar si excede límite diario
4. Si OK → continuar
5. Si excede → bloquear y retornar 429

### Reset Automático

- **Scheduler**: Cron job en el proxy
- **Frecuencia**: Diario a las 00:00 UTC
- **Acción**: `tokens_used_today = 0` para todos los usuarios

## 📈 Métricas y Tracking

### Tabla: bedrock-proxy-usage-tracking-tbl

```sql
- request_id (UUID)
- cognito_user_id
- cognito_email
- team
- person
- request_timestamp
- model_id
- tokens_input
- tokens_output
- tokens_cache_read
- tokens_cache_creation
- cost_usd
- processing_time_ms
- response_status
- error_message
```

### Worker Asíncrono

- **Channel**: Buffer de 1000 métricas
- **Procesamiento**: Batch inserts
- **No bloqueante**: Request continúa sin esperar

## 🔄 Traducción de Formatos

### Anthropic → Bedrock

**Anthropic Messages API:**
```json
{
  "model": "claude-3-5-sonnet-20241022",
  "max_tokens": 1024,
  "messages": [
    {"role": "user", "content": "Hello"}
  ]
}
```

**Bedrock Converse API:**
```json
{
  "modelId": "anthropic.claude-3-5-sonnet-20241022-v2:0",
  "messages": [
    {"role": "user", "content": [{"text": "Hello"}]}
  ],
  "inferenceConfig": {
    "maxTokens": 1024
  }
}
```

### Buffer XML

Problema: Tags XML cortados en streaming
```
Chunk 1: "Use <write_fi"
Chunk 2: "le> tool"
```

Solución: Buffer de 100 caracteres
```
Chunk 1: "Use " (buffer: "<write_fi")
Chunk 2: "<write_file> tool"
```

## 🚀 Endpoints

### POST /v1/messages

Endpoint principal compatible con Anthropic API.

**Headers:**
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Request:**
```json
{
  "model": "claude-3-5-sonnet-20241022",
  "max_tokens": 4096,
  "messages": [
    {"role": "user", "content": "Hello"}
  ],
  "stream": true
}
```

**Response (streaming):**
```
event: message_start
data: {"type":"message_start",...}

event: content_block_delta
data: {"type":"content_block_delta","delta":{"text":"Hello"}}

event: message_stop
data: {"type":"message_stop"}
```

### GET /health

Health check del servicio.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-05T09:45:00Z",
  "database": "connected",
  "version": "1.1.0"
}
```

## ⚙️ Configuración

### Variables de Entorno

```bash
# AWS Bedrock
AWS_BEDROCK_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
AWS_BEDROCK_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_BEDROCK_REGION=eu-west-1
AWS_BEDROCK_ANTHROPIC_DEFAULT_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0

# PostgreSQL
DB_HOST=identity-manager-dev-rds.xxxxx.eu-west-1.rds.amazonaws.com
DB_PORT=5432
DB_NAME=identity_manager_dev_rds
DB_USER=postgres
DB_PASSWORD=<secret>
DB_SSLMODE=require
DB_MAX_CONNS=25
DB_MIN_CONNS=5

# JWT
JWT_SECRET_KEY=<secret>
JWT_ISSUER=bedrock-proxy
JWT_AUDIENCE=bedrock-api

# Server
PORT=8081
LOG_LEVEL=info
LOG_FORMAT=json
LOG_OUTPUT=file
```

## 🐳 Deployment

### Docker

```bash
# Build
docker build -t bedrock-proxy:latest .

# Run
docker run -p 8081:8081 --env-file .env bedrock-proxy:latest
```

### ECS

```bash
# Push to ECR
aws ecr get-login-password --region eu-west-1 | \
  docker login --username AWS --password-stdin \
  701055077130.dkr.ecr.eu-west-1.amazonaws.com

docker tag bedrock-proxy:latest \
  701055077130.dkr.ecr.eu-west-1.amazonaws.com/bedrock-proxy:latest

docker push \
  701055077130.dkr.ecr.eu-west-1.amazonaws.com/bedrock-proxy:latest

# Deploy
aws ecs update-service \
  --cluster bedrock-proxy-dev-cluster \
  --service bedrock-proxy-dev-service \
  --force-new-deployment \
  --region eu-west-1
```

## 📝 Logging

### Formato JSON Estructurado

```json
{
  "timestamp": "2026-03-05T09:45:00Z",
  "level": "info",
  "message": "Request processed",
  "request_id": "uuid",
  "user_id": "cognito_user_id",
  "duration_ms": 1234,
  "status": 200
}
```

### Sanitización

- Tokens JWT → `[REDACTED]`
- Passwords → `[REDACTED]`
- API Keys → `[REDACTED]`

## 🔗 Referencias

- [Arquitectura del Sistema](./02-ARCHITECTURE.md)
- [Guía de Instalación](./03-INSTALLATION.md)
- [Base de Datos](./07-DATABASE.md)