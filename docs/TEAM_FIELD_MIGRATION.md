# Migración: Campo Team en Tablas del Proxy Bedrock

## 📋 Resumen

Esta migración agrega el campo `team` a las tres tablas del proxy Bedrock para almacenar la información del equipo que viene en el JWT token.

## 🎯 Objetivo

Permitir análisis y reportes de uso del proxy Bedrock agrupados por equipo, facilitando:
- Métricas de uso por equipo
- Control de cuotas por equipo
- Análisis de costos por equipo
- Identificación de patrones de uso por equipo

## 📊 Tablas Afectadas

### 1. `bedrock-proxy-usage-tracking-tbl`
- **Campo agregado:** `team VARCHAR(100)`
- **Propósito:** Registrar el equipo en cada petición al proxy
- **Índice:** `idx_usage_team`

### 2. `bedrock-proxy-user-quotas-tbl`
- **Campo agregado:** `team VARCHAR(100)`
- **Propósito:** Asociar cuotas de usuario con su equipo
- **Índice:** `idx_quotas_team`

### 3. `bedrock-proxy-quota-blocks-history-tbl`
- **Campo agregado:** `team VARCHAR(100)`
- **Propósito:** Registrar el equipo en el historial de bloqueos
- **Índice:** `idx_quota_history_team`

## 🔧 Aplicar Migración

### Paso 1: Ejecutar SQL en RDS

```bash
# Conectar a RDS
aws secretsmanager get-secret-value \
  --secret-id identity-mgmt-dev-db-admin \
  --query SecretString --output text | \
  jq -r 'psql -h \(.host) -p \(.port) -U \(.username) -d \(.dbname)'

# Ejecutar migración
\i database/migrations/009_add_team_field.sql
```

### Paso 2: Verificar Migración

```sql
-- Verificar que las columnas existen
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'bedrock-proxy-usage-tracking-tbl' 
  AND column_name = 'team';

-- Verificar índices
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename IN (
  'bedrock-proxy-usage-tracking-tbl',
  'bedrock-proxy-user-quotas-tbl',
  'bedrock-proxy-quota-blocks-history-tbl'
) AND indexname LIKE '%team%';

-- Verificar vista nueva
SELECT * FROM v_usage_by_team LIMIT 5;
```

## 🔄 Cambios Necesarios en el Proxy Bedrock (Go)

### 1. Extraer Team del JWT Token

El proxy Bedrock debe extraer el campo `team` del JWT token y pasarlo a las funciones de base de datos.

**Ubicación:** `proxy-bedrock/pkg/auth/jwt.go`

```go
type JWTClaims struct {
    UserID   string   `json:"user_id"`
    Email    string   `json:"email"`
    Team     string   `json:"team"`      // ← AGREGAR ESTE CAMPO
    Person   string   `json:"person"`
    Aud      []string `json:"aud"`
    Exp      int64    `json:"exp"`
    Iat      int64    `json:"iat"`
    Jti      string   `json:"jti"`
}
```

### 2. Actualizar Función de Tracking de Uso

**Ubicación:** `proxy-bedrock/pkg/database/queries.go`

```go
func (db *Database) TrackUsage(ctx context.Context, usage *UsageRecord) error {
    query := `
        INSERT INTO "bedrock-proxy-usage-tracking-tbl" (
            cognito_user_id,
            cognito_email,
            team,                    -- ← AGREGAR
            request_timestamp,
            model_id,
            source_ip,
            user_agent,
            aws_region,
            tokens_input,
            tokens_output,
            tokens_cache_read,
            tokens_cache_creation,
            cost_usd,
            processing_time_ms,
            response_status,
            error_message
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
    `
    
    _, err := db.pool.Exec(ctx, query,
        usage.CognitoUserID,
        usage.CognitoEmail,
        usage.Team,              // ← AGREGAR
        usage.RequestTimestamp,
        usage.ModelID,
        usage.SourceIP,
        usage.UserAgent,
        usage.AWSRegion,
        usage.TokensInput,
        usage.TokensOutput,
        usage.TokensCacheRead,
        usage.TokensCacheCreation,
        usage.CostUSD,
        usage.ProcessingTimeMs,
        usage.ResponseStatus,
        usage.ErrorMessage,
    )
    
    return err
}
```

### 3. Actualizar Función de Check Quota

**Ubicación:** `proxy-bedrock/pkg/database/quota_queries.go`

```go
func (db *Database) CheckAndUpdateQuota(
    ctx context.Context,
    userID string,
    email string,
    team string,  // ← AGREGAR PARÁMETRO
) (*QuotaCheckResult, error) {
    query := `
        SELECT * FROM check_and_update_quota($1, $2, $3)
    `
    
    var result QuotaCheckResult
    err := db.pool.QueryRow(ctx, query, userID, email, team).Scan(
        &result.Allowed,
        &result.RequestsToday,
        &result.DailyLimit,
        &result.IsBlocked,
        &result.BlockReason,
    )
    
    return &result, err
}
```

### 4. Actualizar Struct UsageRecord

**Ubicación:** `proxy-bedrock/pkg/database/database.go`

```go
type UsageRecord struct {
    CognitoUserID        string
    CognitoEmail         string
    Team                 string    // ← AGREGAR
    RequestTimestamp     time.Time
    ModelID              string
    SourceIP             string
    UserAgent            string
    AWSRegion            string
    TokensInput          int
    TokensOutput         int
    TokensCacheRead      int
    TokensCacheCreation  int
    CostUSD              float64
    ProcessingTimeMs     int
    ResponseStatus       string
    ErrorMessage         string
}
```

### 5. Pasar Team en las Llamadas

**Ubicación:** `proxy-bedrock/pkg/auth/middleware.go` o donde se llame a las funciones

```go
// Al verificar cuota
quotaResult, err := db.CheckAndUpdateQuota(
    ctx,
    claims.UserID,
    claims.Email,
    claims.Team,  // ← AGREGAR
)

// Al registrar uso
usage := &database.UsageRecord{
    CognitoUserID:    claims.UserID,
    CognitoEmail:     claims.Email,
    Team:             claims.Team,  // ← AGREGAR
    RequestTimestamp: time.Now(),
    // ... resto de campos
}
```

## 📈 Nuevas Capacidades

### Vista v_usage_by_team

```sql
SELECT * FROM v_usage_by_team;
```

Retorna:
- `team`: Nombre del equipo
- `request_count`: Total de peticiones
- `unique_users`: Usuarios únicos del equipo
- `total_tokens_input/output`: Tokens consumidos
- `total_cost_usd`: Costo total
- `avg_processing_time_ms`: Tiempo promedio de respuesta

### Queries Útiles

```sql
-- Top 10 equipos por uso
SELECT team, request_count, total_cost_usd
FROM v_usage_by_team
ORDER BY request_count DESC
LIMIT 10;

-- Uso por equipo en un período
SELECT 
    team,
    COUNT(*) as requests,
    SUM(cost_usd) as total_cost
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE request_timestamp >= '2026-03-01'
  AND request_timestamp < '2026-04-01'
  AND team IS NOT NULL
GROUP BY team
ORDER BY requests DESC;

-- Usuarios por equipo
SELECT 
    team,
    COUNT(DISTINCT cognito_user_id) as user_count
FROM "bedrock-proxy-user-quotas-tbl"
WHERE team IS NOT NULL
GROUP BY team
ORDER BY user_count DESC;
```

## ✅ Checklist de Implementación

### Base de Datos
- [ ] Ejecutar migración 009_add_team_field.sql
- [ ] Verificar columnas agregadas
- [ ] Verificar índices creados
- [ ] Verificar vistas actualizadas
- [ ] Probar función check_and_update_quota con team

### Proxy Bedrock (Go)
- [ ] Agregar campo `Team` a struct `JWTClaims`
- [ ] Agregar campo `Team` a struct `UsageRecord`
- [ ] Actualizar función `TrackUsage` para incluir team
- [ ] Actualizar función `CheckAndUpdateQuota` para incluir team
- [ ] Actualizar llamadas a estas funciones
- [ ] Compilar y probar localmente
- [ ] Desplegar a producción

### Dashboard (Ya está listo)
- [x] El dashboard ya usa `cognito_email` como "team"
- [x] Los queries ya están preparados para usar el campo team
- [ ] Actualizar queries para usar el nuevo campo `team` en lugar de `cognito_email`

## 🔍 Validación

### 1. Verificar que el proxy guarda el team

```sql
SELECT 
    cognito_email,
    team,
    COUNT(*) as requests
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE request_timestamp >= CURRENT_DATE
GROUP BY cognito_email, team
ORDER BY requests DESC
LIMIT 10;
```

### 2. Verificar que las cuotas tienen team

```sql
SELECT 
    cognito_email,
    team,
    requests_today,
    daily_request_limit
FROM "bedrock-proxy-user-quotas-tbl"
WHERE team IS NOT NULL
LIMIT 10;
```

## 📝 Notas

- El campo `team` es **opcional** (nullable) para mantener compatibilidad con datos existentes
- Los datos históricos no tendrán el campo `team` poblado
- El proxy debe manejar el caso donde el JWT no tenga el campo `team`
- Se recomienda agregar validación en el proxy para asegurar que el team esté presente

## 🚀 Rollback

Si es necesario revertir la migración:

```sql
-- Eliminar índices
DROP INDEX IF EXISTS idx_usage_team;
DROP INDEX IF EXISTS idx_quotas_team;
DROP INDEX IF EXISTS idx_quota_history_team;

-- Eliminar vista
DROP VIEW IF EXISTS v_usage_by_team;

-- Restaurar vistas originales
DROP VIEW IF EXISTS v_usage_detailed;
CREATE VIEW v_usage_detailed AS
SELECT 
    id, cognito_user_id, cognito_email, request_timestamp,
    model_id, source_ip, user_agent, aws_region,
    tokens_input, tokens_output, tokens_cache_read, tokens_cache_creation,
    cost_usd, processing_time_ms, response_status, error_message, created_at
FROM "bedrock-proxy-usage-tracking-tbl"
ORDER BY request_timestamp DESC;

DROP VIEW IF EXISTS v_recent_errors;
CREATE VIEW v_recent_errors AS
SELECT 
    id, cognito_user_id, cognito_email, request_timestamp,
    model_id, response_status, error_message, created_at
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE response_status != 'success'
ORDER BY request_timestamp DESC
LIMIT 100;

-- Eliminar columnas
ALTER TABLE "bedrock-proxy-usage-tracking-tbl" DROP COLUMN IF EXISTS team;
ALTER TABLE "bedrock-proxy-user-quotas-tbl" DROP COLUMN IF EXISTS team;
ALTER TABLE "bedrock-proxy-quota-blocks-history-tbl" DROP COLUMN IF EXISTS team;

-- Restaurar función original (sin parámetro team)
-- Ver CONSOLIDATED_MIGRATIONS.sql para la versión original