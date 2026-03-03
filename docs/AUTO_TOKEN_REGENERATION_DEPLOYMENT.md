# Auto Token Regeneration - Deployment Guide
## Guía de Despliegue de Regeneración Automática de Tokens

**Fecha:** 3 de Marzo de 2026  
**Versión:** 1.0  
**Feature:** Auto Token Regeneration

---

## 📋 Índice

1. [Resumen de la Feature](#resumen-de-la-feature)
2. [Componentes Modificados](#componentes-modificados)
3. [Pre-requisitos](#pre-requisitos)
4. [Paso 1: Base de Datos](#paso-1-base-de-datos)
5. [Paso 2: Cognito User Pool](#paso-2-cognito-user-pool)
6. [Paso 3: Backend Lambda](#paso-3-backend-lambda)
7. [Paso 4: Proxy Bedrock](#paso-4-proxy-bedrock)
8. [Paso 5: Dashboard](#paso-5-dashboard)
9. [Verificación](#verificación)
10. [Rollback](#rollback)
11. [Troubleshooting](#troubleshooting)

---

## 🎯 Resumen de la Feature

La regeneración automática de tokens permite que cuando un token JWT expire, el sistema genere automáticamente un nuevo token con la misma configuración y lo envíe por email al usuario, sin intervención manual.

### Beneficios:
- ✅ Experiencia de usuario mejorada (sin interrupciones)
- ✅ Reducción de tickets de soporte
- ✅ Mantenimiento automático de tokens
- ✅ Auditoría completa de regeneraciones

### Flujo:
```
Token Expira → Proxy Detecta → Lambda Valida → Genera Nuevo Token → Envía Email → Usuario Notificado
```

---

## 🔧 Componentes Modificados

### 1. Base de Datos
- **Tabla:** `identity-manager-tokens-tbl`
- **Cambios:** 7 nuevos campos + 3 índices
- **Migración:** `011_add_token_regeneration_support.sql`

### 2. Backend Lambda
- **Archivos nuevos:**
  - `services/token_regeneration_service.py`
- **Archivos modificados:**
  - `services/email_service.py`
  - `lambda_function.py`
- **Nuevo endpoint:** `/api/tokens/regenerate`

### 3. Proxy Bedrock
- **Archivo modificado:** `pkg/auth/middleware.go`
- **Funciones nuevas:**
  - `callLambdaAPI()`
  - `handleExpiredToken()`

### 4. Dashboard
- **Archivo modificado:** `frontend/dashboard/js/dashboard.js`
- **Cambios:** Indicadores visuales de regeneración

---

## ✅ Pre-requisitos

### Accesos Necesarios:
- [ ] Acceso a AWS Console (RDS, Lambda, Cognito, API Gateway)
- [ ] Acceso SSH a instancia EC2 (para migración BD)
- [ ] Permisos para modificar Cognito User Pool
- [ ] Acceso al repositorio Git
- [ ] Acceso al servidor del Proxy Bedrock

### Herramientas:
- [ ] AWS CLI configurado
- [ ] psql client instalado
- [ ] Go 1.21+ (para compilar proxy)
- [ ] Git

---

## 📊 Paso 1: Base de Datos

### 1.1 Aplicar Migración 011

**Conectarse a la instancia EC2:**
```bash
ssh -i ~/.ssh/your-key.pem ec2-user@your-ec2-instance
```

**Ejecutar script de migración:**
```bash
cd /path/to/identity-manager-v2
./scripts/apply_migration_011.sh
```

**Verificar migración:**
```sql
-- Conectar a PostgreSQL
psql -h your-rds-endpoint -U postgres -d identity_manager

-- Verificar nuevos campos
\d identity-manager-tokens-tbl

-- Verificar índices
\di idx_tokens_regenerated_*

-- Verificar que no hay errores
SELECT COUNT(*) FROM "identity-manager-tokens-tbl";
```

### 1.2 Campos Añadidos

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `regenerated_at` | TIMESTAMP | Fecha de regeneración |
| `regenerated_to_jti` | UUID | JTI del nuevo token |
| `regenerated_from_jti` | UUID | JTI del token anterior |
| `regeneration_reason` | VARCHAR(100) | Motivo (auto_regeneration) |
| `regeneration_client_ip` | VARCHAR(45) | IP del cliente |
| `regeneration_user_agent` | TEXT | User agent |
| `regeneration_email_sent` | BOOLEAN | Estado del email |

### 1.3 Rollback de Migración (si es necesario)

```sql
-- Eliminar índices
DROP INDEX IF EXISTS idx_tokens_regenerated_at;
DROP INDEX IF EXISTS idx_tokens_regenerated_to_jti;
DROP INDEX IF EXISTS idx_tokens_regenerated_from_jti;

-- Eliminar campos
ALTER TABLE "identity-manager-tokens-tbl"
DROP COLUMN IF EXISTS regenerated_at,
DROP COLUMN IF EXISTS regenerated_to_jti,
DROP COLUMN IF EXISTS regenerated_from_jti,
DROP COLUMN IF EXISTS regeneration_reason,
DROP COLUMN IF EXISTS regeneration_client_ip,
DROP COLUMN IF EXISTS regeneration_user_agent,
DROP COLUMN IF EXISTS regeneration_email_sent;
```

---

## 👤 Paso 2: Cognito User Pool

### 2.1 Añadir Custom Attribute

**Via AWS Console:**

1. Ir a **Amazon Cognito** → **User Pools**
2. Seleccionar tu User Pool (ej: `identity-manager-dev-user-pool`)
3. Ir a **Sign-up experience** → **Attributes**
4. Click en **Add custom attribute**
5. Configurar:
   ```
   Name: auto_regen_tokens
   Type: String
   Mutable: Yes (Editable)
   Min length: 0
   Max length: 10
   ```
6. Click **Save changes**

**Via AWS CLI:**
```bash
aws cognito-idp add-custom-attributes \
  --user-pool-id eu-west-1_XXXXXXX \
  --custom-attributes \
    Name=auto_regen_tokens,AttributeDataType=String,Mutable=true,StringAttributeConstraints={MinLength=0,MaxLength=10}
```

### 2.2 Configurar Usuarios Existentes

**Opción 1: Habilitar para todos (recomendado):**
```bash
# Script para actualizar todos los usuarios
aws cognito-idp list-users \
  --user-pool-id eu-west-1_XXXXXXX \
  --query 'Users[].Username' \
  --output text | while read username; do
    aws cognito-idp admin-update-user-attributes \
      --user-pool-id eu-west-1_XXXXXXX \
      --username "$username" \
      --user-attributes Name=custom:auto_regen_tokens,Value=true
done
```

**Opción 2: Habilitar selectivamente:**
```bash
# Para un usuario específico
aws cognito-idp admin-update-user-attributes \
  --user-pool-id eu-west-1_XXXXXXX \
  --username user@example.com \
  --user-attributes Name=custom:auto_regen_tokens,Value=true
```

### 2.3 Verificar Configuración

```bash
# Ver atributos de un usuario
aws cognito-idp admin-get-user \
  --user-pool-id eu-west-1_XXXXXXX \
  --username user@example.com \
  --query 'UserAttributes[?Name==`custom:auto_regen_tokens`]'
```

---

## 🔧 Paso 3: Backend Lambda

### 3.1 Desplegar Código Actualizado

**Opción A: Deployment automático (recomendado):**
```bash
cd /path/to/identity-manager-v2
./scripts/deploy_lambda.sh
```

**Opción B: Deployment manual:**
```bash
# 1. Empaquetar Lambda
cd backend/lambdas/identity-mgmt-api
zip -r lambda-package.zip . -x "*.git*" -x "*__pycache__*" -x "*.pyc" -x "tests/*"

# 2. Subir a Lambda
aws lambda update-function-code \
  --function-name identity-mgmt-dev-api-lmbd \
  --zip-file fileb://lambda-package.zip

# 3. Esperar a que se complete
aws lambda wait function-updated \
  --function-name identity-mgmt-dev-api-lmbd
```

### 3.2 Verificar Deployment

```bash
# Ver última actualización
aws lambda get-function \
  --function-name identity-mgmt-dev-api-lmbd \
  --query 'Configuration.[LastModified,CodeSize,Runtime]'

# Test del nuevo endpoint
curl -X POST https://your-api-gateway-url/dev \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "regenerate_token",
    "data": {
      "expired_token_jti": "test-jti",
      "user_id": "test-user-id",
      "client_ip": "127.0.0.1",
      "user_agent": "test"
    }
  }'
```

### 3.3 Archivos Desplegados

```
backend/lambdas/identity-mgmt-api/
├── services/
│   ├── token_regeneration_service.py  ← NUEVO
│   ├── email_service.py               ← MODIFICADO
│   └── ...
├── lambda_function.py                 ← MODIFICADO
└── ...
```

---

## 🚀 Paso 4: Proxy Bedrock

### 4.1 Configurar Variable de Entorno

**Añadir en el archivo de configuración del proxy:**
```bash
# .env o configuración del sistema
export LAMBDA_API_URL="https://your-api-gateway-url.execute-api.eu-west-1.amazonaws.com/dev"
```

**O en systemd service:**
```ini
# /etc/systemd/system/proxy-bedrock.service
[Service]
Environment="LAMBDA_API_URL=https://your-api-gateway-url.execute-api.eu-west-1.amazonaws.com/dev"
```

### 4.2 Compilar y Desplegar Proxy

```bash
# 1. Ir al directorio del proxy (submódulo)
cd proxy-bedrock

# 2. Compilar
go build -o bin/proxy-bedrock cmd/main.go

# 3. Verificar compilación
./bin/proxy-bedrock --version

# 4. Detener servicio actual
sudo systemctl stop proxy-bedrock

# 5. Copiar binario
sudo cp bin/proxy-bedrock /usr/local/bin/

# 6. Reiniciar servicio
sudo systemctl start proxy-bedrock

# 7. Verificar estado
sudo systemctl status proxy-bedrock
```

### 4.3 Verificar Logs

```bash
# Ver logs en tiempo real
sudo journalctl -u proxy-bedrock -f

# Buscar eventos de regeneración
sudo journalctl -u proxy-bedrock | grep "TOKEN_EXPIRED\|TOKEN_REGENERATED"
```

### 4.4 Archivo Modificado

```
proxy-bedrock/
└── pkg/
    └── auth/
        └── middleware.go  ← MODIFICADO (+267 líneas)
```

---

## 🎨 Paso 5: Dashboard

### 5.1 Desplegar Dashboard Actualizado

**Si usas S3 + CloudFront:**
```bash
# Sincronizar archivos
aws s3 sync frontend/dashboard/ s3://your-dashboard-bucket/ \
  --exclude "*.md" \
  --exclude ".git*"

# Invalidar caché de CloudFront
aws cloudfront create-invalidation \
  --distribution-id YOUR_DISTRIBUTION_ID \
  --paths "/js/dashboard.js"
```

**Si usas servidor web:**
```bash
# Copiar archivo actualizado
scp frontend/dashboard/js/dashboard.js \
  user@your-server:/var/www/dashboard/js/
```

### 5.2 Verificar en Navegador

1. Abrir dashboard: `https://your-dashboard-url`
2. Ir a pestaña **Tokens**
3. Verificar que se muestran los badges:
   - 🔄 **Regenerated** (tokens viejos regenerados)
   - ✨ **Auto-generated** (tokens nuevos generados automáticamente)

### 5.3 Archivo Modificado

```
frontend/dashboard/
└── js/
    └── dashboard.js  ← MODIFICADO (+19 líneas)
```

---

## ✅ Verificación

### Test End-to-End

#### 1. Preparar Test

```bash
# Crear usuario de prueba con auto-regen habilitado
aws cognito-idp admin-create-user \
  --user-pool-id eu-west-1_XXXXXXX \
  --username test-regen@example.com \
  --user-attributes \
    Name=email,Value=test-regen@example.com \
    Name=custom:auto_regen_tokens,Value=true \
  --temporary-password "TempPass123!"
```

#### 2. Crear Token con Expiración Corta

```bash
# Via Dashboard o API
curl -X POST https://your-api-gateway-url/dev \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "create_token",
    "data": {
      "user_id": "user-id-from-cognito",
      "application_profile_id": "profile-id",
      "validity_period": "1_day",
      "send_email": true
    }
  }'
```

#### 3. Simular Expiración

**Opción A: Esperar a que expire naturalmente**

**Opción B: Modificar manualmente en BD (solo para testing):**
```sql
UPDATE "identity-manager-tokens-tbl"
SET expires_at = NOW() - INTERVAL '1 hour'
WHERE token_id = 'your-test-token-id';
```

#### 4. Hacer Request con Token Expirado

```bash
curl -X POST https://your-proxy-url/invoke-model \
  -H "Authorization: Bearer YOUR_EXPIRED_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "modelId": "anthropic.claude-3-sonnet-20240229-v1:0",
    "messages": [{"role": "user", "content": "test"}]
  }'
```

#### 5. Verificar Respuesta

**Respuesta esperada (regeneración exitosa):**
```json
{
  "error": {
    "type": "token_expired_regenerated",
    "message": "token has expired. A new token has been generated and sent to your email",
    "code": 401,
    "auto_regenerated": true,
    "email_sent": true
  }
}
```

#### 6. Verificar Email

- Revisar inbox de `test-regen@example.com`
- Debe recibir email con:
  - Título: "🔄 Token JWT Regenerado Automáticamente"
  - Nuevo token JWT
  - Fecha de expiración del token anterior

#### 7. Verificar en Dashboard

1. Ir a pestaña **Tokens**
2. Buscar el token del usuario de prueba
3. Verificar badges:
   - Token viejo: 🔄 **Regenerated**
   - Token nuevo: ✨ **Auto-generated**

#### 8. Verificar en Base de Datos

```sql
SELECT 
    token_id,
    jti,
    email,
    status,
    regenerated_at,
    regenerated_to_jti,
    regenerated_from_jti,
    regeneration_email_sent
FROM "identity-manager-tokens-tbl"
WHERE email = 'test-regen@example.com'
ORDER BY created_at DESC
LIMIT 5;
```

### Checklist de Verificación

- [ ] Migración 011 aplicada correctamente
- [ ] Custom attribute `custom:auto_regen_tokens` creado en Cognito
- [ ] Lambda desplegada con nuevo código
- [ ] Proxy compilado y desplegado con `LAMBDA_API_URL`
- [ ] Dashboard actualizado con badges visuales
- [ ] Test end-to-end exitoso
- [ ] Email de regeneración recibido
- [ ] Badges visibles en dashboard
- [ ] Datos correctos en base de datos
- [ ] Logs del proxy muestran eventos de regeneración

---

## 🔄 Rollback

### Si necesitas revertir la feature:

#### 1. Revertir Base de Datos
```sql
-- Ejecutar rollback de migración 011
-- (Ver sección 1.3)
```

#### 2. Revertir Lambda
```bash
# Volver a versión anterior
aws lambda update-function-code \
  --function-name identity-mgmt-dev-api-lmbd \
  --s3-bucket your-lambda-bucket \
  --s3-key previous-version.zip
```

#### 3. Revertir Proxy
```bash
cd proxy-bedrock
git checkout HEAD~1 pkg/auth/middleware.go
go build -o bin/proxy-bedrock cmd/main.go
sudo cp bin/proxy-bedrock /usr/local/bin/
sudo systemctl restart proxy-bedrock
```

#### 4. Revertir Dashboard
```bash
cd frontend/dashboard
git checkout HEAD~1 js/dashboard.js
# Redesplegar según tu método
```

---

## 🔍 Troubleshooting

### Problema 1: Token no se regenera

**Síntomas:**
- Proxy retorna error `auto_regen_disabled`

**Solución:**
```bash
# Verificar custom attribute en Cognito
aws cognito-idp admin-get-user \
  --user-pool-id eu-west-1_XXXXXXX \
  --username user@example.com

# Si no existe o es "false", actualizar:
aws cognito-idp admin-update-user-attributes \
  --user-pool-id eu-west-1_XXXXXXX \
  --username user@example.com \
  --user-attributes Name=custom:auto_regen_tokens,Value=true
```

### Problema 2: Error "max_tokens_reached"

**Síntomas:**
- Proxy retorna error con `active_tokens_count: 5`

**Solución:**
```sql
-- Ver tokens activos del usuario
SELECT token_id, jti, created_at, expires_at, status
FROM "identity-manager-tokens-tbl"
WHERE user_id = 'user-id'
AND status = 'active'
ORDER BY created_at DESC;

-- Revocar tokens viejos si es necesario
UPDATE "identity-manager-tokens-tbl"
SET is_revoked = true,
    revoked_at = NOW(),
    revocation_reason = 'Manual cleanup for regeneration'
WHERE token_id IN ('old-token-id-1', 'old-token-id-2');
```

### Problema 3: Proxy no puede llamar a Lambda

**Síntomas:**
- Logs muestran `TOKEN_REGEN_API_ERROR`
- Error: "LAMBDA_API_URL environment variable not set"

**Solución:**
```bash
# Verificar variable de entorno
echo $LAMBDA_API_URL

# Si no está configurada, añadir y reiniciar
export LAMBDA_API_URL="https://your-api-url"
sudo systemctl restart proxy-bedrock
```

### Problema 4: Email no se envía

**Síntomas:**
- Regeneración exitosa pero `email_sent: false`

**Solución:**
```bash
# Verificar logs de Lambda
aws logs tail /aws/lambda/identity-mgmt-dev-api-lmbd --follow

# Verificar configuración de email en Secrets Manager
aws secretsmanager get-secret-value \
  --secret-id identity-manager/dev/email-smtp

# Verificar que el secret contiene:
# - gmail_smtp.user
# - gmail_smtp.password
# - gmail_smtp.server
# - gmail_smtp.port
```

### Problema 5: Badges no aparecen en Dashboard

**Síntomas:**
- Dashboard no muestra 🔄 o ✨ badges

**Solución:**
```bash
# Limpiar caché del navegador
# Ctrl+Shift+R (Windows/Linux) o Cmd+Shift+R (Mac)

# Verificar que el archivo está actualizado
curl https://your-dashboard-url/js/dashboard.js | grep "regenerated_at"

# Si no está actualizado, redesplegar
aws s3 cp frontend/dashboard/js/dashboard.js \
  s3://your-bucket/js/dashboard.js

# Invalidar CloudFront
aws cloudfront create-invalidation \
  --distribution-id YOUR_ID \
  --paths "/js/dashboard.js"
```

---

## 📊 Monitoreo Post-Despliegue

### Métricas a Monitorear

#### 1. CloudWatch Logs - Lambda
```bash
# Buscar regeneraciones exitosas
aws logs filter-log-events \
  --log-group-name /aws/lambda/identity-mgmt-dev-api-lmbd \
  --filter-pattern "REGENERATE_TOKEN" \
  --start-time $(date -u -d '1 hour ago' +%s)000

# Buscar errores de regeneración
aws logs filter-log-events \
  --log-group-name /aws/lambda/identity-mgmt-dev-api-lmbd \
  --filter-pattern "ERROR" \
  --filter-pattern "regenerat" \
  --start-time $(date -u -d '1 hour ago' +%s)000
```

#### 2. Proxy Logs
```bash
# Eventos de token expirado
sudo journalctl -u proxy-bedrock --since "1 hour ago" | grep "TOKEN_EXPIRED"

# Regeneraciones exitosas
sudo journalctl -u proxy-bedrock --since "1 hour ago" | grep "TOKEN_REGENERATED"

# Errores de regeneración
sudo journalctl -u proxy-bedrock --since "1 hour ago" | grep "TOKEN_REGEN.*ERROR"
```

#### 3. Base de Datos
```sql
-- Regeneraciones en las últimas 24 horas
SELECT 
    DATE_TRUNC('hour', regenerated_at) as hour,
    COUNT(*) as regenerations,
    COUNT(CASE WHEN regeneration_email_sent THEN 1 END) as emails_sent
FROM "identity-manager-tokens-tbl"
WHERE regenerated_at >= NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', regenerated_at)
ORDER BY hour DESC;

-- Usuarios con más regeneraciones
SELECT 
    email,
    COUNT(*) as regeneration_count
FROM "identity-manager-tokens-tbl"
WHERE regenerated_at IS NOT NULL
GROUP BY email
ORDER BY regeneration_count DESC
LIMIT 10;
```

### Alertas Recomendadas

1. **Alta tasa de regeneraciones fallidas** (> 10% en 1 hora)
2. **Emails no enviados** (> 5 en 1 hora)
3. **Errores de API Lambda** (> 10 en 5 minutos)
4. **Proxy no puede conectar a Lambda** (> 3 en 5 minutos)

---

## 📝 Notas Finales

### Configuración por Defecto

- **Auto-regeneración:** Habilitada para nuevos usuarios
- **Límite de tokens activos:** 5 por usuario
- **Timeout Lambda API:** 10 segundos
- **Email:** Enviado automáticamente en cada regeneración

### Mejores Prácticas

1. **Monitorear** las primeras 48 horas post-despliegue
2. **Revisar** logs diariamente la primera semana
3. **Ajustar** límites según uso real
4. **Comunicar** a usuarios sobre la nueva feature
5. **Documentar** cualquier issue encontrado

### Soporte

Para issues o preguntas:
- **Logs:** CloudWatch + Proxy journalctl
- **Base de Datos:** Queries de auditoría
- **Documentación:** Este archivo + AUTO_TOKEN_REGENERATION_DESIGN.md

---

**Deployment completado exitosamente! 🎉**