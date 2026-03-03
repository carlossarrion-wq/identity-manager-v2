# Integración del Sistema de Control de Cuotas con Proxy-Bedrock

## Análisis del Estado Actual

### Arquitectura Actual del Proxy-Bedrock

El proxy-bedrock actualmente utiliza:

1. **Base de Datos Antigua** con tablas:
   - `tokens`: Almacena tokens JWT
   - `users`: Información de usuarios
   - `quota_usage`: Uso mensual agregado
   - `user_blocking_status`: Contadores diarios y bloqueos
   - `request_metrics`: Métricas de peticiones

2. **Flujo de Autenticación y Control**:
```
Request → AuthMiddleware → ValidateToken (BD) → CheckQuota (BD) → 
→ Process Request → UpdateQuotaAndCounters (BD) → CheckAndBlockUser (BD)
```

3. **Módulos Go**:
   - `pkg/auth/middleware.go`: Autenticación JWT
   - `pkg/database/database.go`: Conexión a PostgreSQL
   - `pkg/database/queries.go`: Queries de validación y cuotas

## Propuesta de Migración

### Objetivo

Migrar el proxy-bedrock para usar el **nuevo sistema de control de cuotas** basado en:
- `bedrock-proxy-user-quotas-tbl`
- `bedrock-proxy-quota-blocks-history-tbl`
- Función `check_and_update_quota()`

### Ventajas de la Nueva Arquitectura

✅ **Simplificación**: Una sola función (`check_and_update_quota`) reemplaza múltiples queries  
✅ **Atomicidad**: Toda la lógica de cuotas en una transacción  
✅ **Reset Automático**: Sin necesidad de proceso batch  
✅ **Bloqueos Flexibles**: Soporte para `blocked_until` (múltiples días)  
✅ **Auditoría Completa**: Historial de todos los bloqueos  

## Plan de Integración

### Fase 1: Actualizar Queries en Go

#### 1.1. Nuevo Archivo: `pkg/database/quota_queries.go`

```go
package database

import (
	"context"
	"fmt"
	"time"
)

// QuotaCheckResult contiene el resultado de verificar la cuota
type QuotaCheckResult struct {
	Allowed        bool
	RequestsToday  int
	DailyLimit     int
	IsBlocked      bool
	BlockReason    string
	BlockedUntil   *time.Time
}

// CheckAndUpdateQuota verifica y actualiza la cuota del usuario
// Llama a la función PL/pgSQL check_and_update_quota()
func (db *Database) CheckAndUpdateQuota(ctx context.Context, cognitoUserID, cognitoEmail string) (*QuotaCheckResult, error) {
	query := `
		SELECT * FROM check_and_update_quota($1, $2)
	`

	var result QuotaCheckResult
	err := db.pool.QueryRow(ctx, query, cognitoUserID, cognitoEmail).Scan(
		&result.Allowed,
		&result.RequestsToday,
		&result.DailyLimit,
		&result.IsBlocked,
		&result.BlockReason,
	)

	if err != nil {
		return nil, fmt.Errorf("error checking quota: %w", err)
	}

	return &result, nil
}

// GetUserQuotaStatus obtiene el estado actual de la cuota de un usuario
func (db *Database) GetUserQuotaStatus(ctx context.Context, cognitoUserID string) (*QuotaStatus, error) {
	query := `
		SELECT * FROM get_user_quota_status($1)
	`

	var status QuotaStatus
	var blockedAt, lastRequestAt *time.Time
	
	err := db.pool.QueryRow(ctx, query, cognitoUserID).Scan(
		&status.CognitoUserID,
		&status.CognitoEmail,
		&status.DailyLimit,
		&status.RequestsToday,
		&status.RemainingRequests,
		&status.UsagePercentage,
		&status.IsBlocked,
		&blockedAt,
		&status.AdministrativeSafe,
		&lastRequestAt,
	)

	if err != nil {
		return nil, fmt.Errorf("error getting quota status: %w", err)
	}

	if blockedAt != nil {
		status.BlockedAt = *blockedAt
	}
	if lastRequestAt != nil {
		status.LastRequestAt = *lastRequestAt
	}

	return &status, nil
}

// QuotaStatus contiene el estado de cuota de un usuario
type QuotaStatus struct {
	CognitoUserID       string
	CognitoEmail        string
	DailyLimit          int
	RequestsToday       int
	RemainingRequests   int
	UsagePercentage     float64
	IsBlocked           bool
	BlockedAt           time.Time
	AdministrativeSafe  bool
	LastRequestAt       time.Time
}

// AdministrativeUnblockUser desbloquea un usuario administrativamente
func (db *Database) AdministrativeUnblockUser(ctx context.Context, cognitoUserID, adminUserID, reason string) error {
	query := `
		SELECT administrative_unblock_user($1, $2, $3)
	`

	var success bool
	err := db.pool.QueryRow(ctx, query, cognitoUserID, adminUserID, reason).Scan(&success)
	if err != nil {
		return fmt.Errorf("error unblocking user: %w", err)
	}

	if !success {
		return fmt.Errorf("failed to unblock user")
	}

	return nil
}

// UpdateUserDailyLimit actualiza el límite diario de un usuario
func (db *Database) UpdateUserDailyLimit(ctx context.Context, cognitoUserID string, newLimit int) error {
	query := `
		SELECT update_user_daily_limit($1, $2)
	`

	var success bool
	err := db.pool.QueryRow(ctx, query, cognitoUserID, newLimit).Scan(&success)
	if err != nil {
		return fmt.Errorf("error updating daily limit: %w", err)
	}

	if !success {
		return fmt.Errorf("failed to update daily limit")
	}

	return nil
}

// AdministrativeBlockUser bloquea un usuario hasta una fecha específica
func (db *Database) AdministrativeBlockUser(ctx context.Context, cognitoUserID, adminUserID string, blockUntil time.Time, reason string) error {
	query := `
		SELECT administrative_block_user($1, $2, $3, $4)
	`

	var success bool
	err := db.pool.QueryRow(ctx, query, cognitoUserID, adminUserID, blockUntil, reason).Scan(&success)
	if err != nil {
		return fmt.Errorf("error blocking user: %w", err)
	}

	if !success {
		return fmt.Errorf("failed to block user")
	}

	return nil
}
```

#### 1.2. Actualizar `pkg/auth/middleware.go`

Añadir verificación de cuota después de la autenticación:

```go
// Después de la autenticación exitosa, verificar cuota
quotaResult, err := am.db.CheckAndUpdateQuota(r.Context(), userCtx.UserID, userCtx.Email)
if err != nil {
	am.respondError(w, r, http.StatusInternalServerError, 
		fmt.Sprintf("quota check failed: %v", err), "quota_check_error")
	return
}

// Si no está permitido, rechazar la petición
if !quotaResult.Allowed {
	// Registrar evento de cuota excedida
	if Logger != nil {
		Logger.WarningContext(r.Context(), amslog.Event{
			Name:    "QUOTA_EXCEEDED",
			Message: quotaResult.BlockReason,
			Outcome: amslog.OutcomeFailure,
			Fields: map[string]interface{}{
				"user.id":         userCtx.UserID,
				"user.email":      userCtx.Email,
				"requests_today":  quotaResult.RequestsToday,
				"daily_limit":     quotaResult.DailyLimit,
				"is_blocked":      quotaResult.IsBlocked,
				"client.ip":       clientIP,
			},
		})
	}

	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("X-RateLimit-Limit", fmt.Sprintf("%d", quotaResult.DailyLimit))
	w.Header().Set("X-RateLimit-Remaining", "0")
	w.Header().Set("X-RateLimit-Reset", "midnight")
	w.WriteHeader(http.StatusTooManyRequests)
	fmt.Fprintf(w, `{"error":"%s","requests_today":%d,"daily_limit":%d}`, 
		quotaResult.BlockReason, quotaResult.RequestsToday, quotaResult.DailyLimit)
	return
}

// Añadir información de cuota al contexto
ctx = context.WithValue(ctx, "quota_info", quotaResult)
```

### Fase 2: Migración de Datos

#### 2.1. Script de Migración

```sql
-- Migrar datos de user_blocking_status a bedrock-proxy-user-quotas-tbl
INSERT INTO "bedrock-proxy-user-quotas-tbl" (
    cognito_user_id,
    cognito_email,
    daily_request_limit,
    current_date,
    requests_today,
    is_blocked,
    blocked_at,
    blocked_until,
    last_request_at,
    created_at,
    updated_at
)
SELECT 
    ubs.user_id as cognito_user_id,
    u.email as cognito_email,
    u.daily_request_limit,
    CURRENT_DATE as current_date,
    ubs.daily_requests as requests_today,
    ubs.is_blocked,
    ubs.blocked_at,
    ubs.blocked_until,
    ubs.last_request_at,
    ubs.created_at,
    ubs.updated_at
FROM user_blocking_status ubs
JOIN users u ON ubs.user_id = u.iam_username
ON CONFLICT (cognito_user_id) DO UPDATE
SET daily_request_limit = EXCLUDED.daily_request_limit,
    requests_today = EXCLUDED.requests_today,
    is_blocked = EXCLUDED.is_blocked,
    blocked_at = EXCLUDED.blocked_at,
    blocked_until = EXCLUDED.blocked_until,
    last_request_at = EXCLUDED.last_request_at,
    updated_at = CURRENT_TIMESTAMP;
```

### Fase 3: Actualizar Tracking de Uso

#### 3.1. Mantener Registro en `bedrock-proxy-usage-tracking-tbl`

El registro de métricas detalladas se mantiene en la tabla de tracking:

```go
// Después de procesar la petición a Bedrock
func (db *Database) InsertUsageTracking(ctx context.Context, usage *UsageTrackingData) error {
	query := `
		INSERT INTO "bedrock-proxy-usage-tracking-tbl" (
			cognito_user_id,
			cognito_email,
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
		) VALUES (
			$1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
		)
	`

	_, err := db.pool.Exec(ctx, query,
		usage.CognitoUserID,
		usage.CognitoEmail,
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
		usage.ProcessingTimeMS,
		usage.ResponseStatus,
		usage.ErrorMessage,
	)

	return err
}
```

## Flujo Completo Propuesto

```
┌─────────────────────────────────────────────────────────────┐
│ 1. REQUEST LLEGA AL PROXY                                   │
│    [SÍNCRONO]                                                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. AUTH MIDDLEWARE                                           │
│    [SÍNCRONO - BLOQUEA SI FALLA]                            │
│    - Extraer JWT del header                                  │
│    - Validar firma JWT                                       │
│    - Validar token en BD (tabla tokens)                      │
│    - Extraer cognito_user_id y cognito_email                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. VERIFICAR CUOTA                                           │
│    [SÍNCRONO - BLOQUEA SI EXCEDE LÍMITE]                    │
│    LLAMAR: check_and_update_quota(user_id, email)           │
│                                                               │
│    La función hace:                                          │
│    - Crear registro si no existe                             │
│    - Verificar si blocked_until ha pasado → desbloquear     │
│    - Verificar si es nuevo día → reset                       │
│    - Verificar si está bloqueado → rechazar                  │
│    - Verificar si alcanzó límite → bloquear y rechazar      │
│    - Incrementar contador → permitir                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ├─── NO PERMITIDO (429)
                     │    └─> Retornar error con detalles
                     │        [FIN - NO CONTINÚA]
                     │
                     └─── PERMITIDO (200)
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. PROCESAR REQUEST A BEDROCK                                │
│    [SÍNCRONO - ESPERA RESPUESTA]                            │
│    - Enviar petición a Bedrock                               │
│    - Recibir respuesta (streaming o no-streaming)           │
│    - Capturar tokens y costos                                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. RETORNAR RESPUESTA AL CLIENTE                             │
│    [SÍNCRONO - RESPUESTA INMEDIATA]                         │
│    - Headers con info de cuota                               │
│    - Respuesta de Bedrock                                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. REGISTRAR USO DETALLADO                                   │
│    [ASÍNCRONO - EN GOROUTINE]                               │
│    go func() {                                               │
│        INSERT INTO bedrock-proxy-usage-tracking-tbl          │
│        - Métricas detalladas de la petición                  │
│        - Tokens, costos, tiempos                             │
│    }()                                                       │
│                                                               │
│    ⚠️ NO BLOQUEA - Cliente ya tiene respuesta               │
└─────────────────────────────────────────────────────────────┘
```

### Resumen de Sincronía

| Paso | Operación | Tipo | Bloquea Request | Motivo |
|------|-----------|------|-----------------|--------|
| 1 | Request llega | Síncrono | - | Inicio |
| 2 | Autenticación | **Síncrono** | ✅ Sí | Debe validar antes de continuar |
| 3 | Verificar cuota | **Síncrono** | ✅ Sí | Debe bloquear si excede límite |
| 4 | Llamada Bedrock | **Síncrono** | ✅ Sí | Necesita respuesta para cliente |
| 5 | Retornar respuesta | **Síncrono** | - | Envío al cliente |
| 6 | Registrar uso | **Asíncrono** | ❌ No | Tracking detallado, no crítico |

## Ventajas de Esta Arquitectura

### 1. **Separación de Responsabilidades**

- **Autenticación**: Valida identidad (tabla `tokens`)
- **Control de Cuotas**: Limita uso diario (función `check_and_update_quota`)
- **Tracking**: Registra métricas detalladas (tabla `usage-tracking`)

### 2. **Rendimiento**

- Una sola llamada a función PL/pgSQL (vs múltiples queries)
- Transacción atómica en la BD
- Sin race conditions

### 3. **Mantenibilidad**

- Lógica de cuotas centralizada en PostgreSQL
- Fácil de actualizar sin cambiar código Go
- Testing más simple

### 4. **Escalabilidad**

- Reset distribuido (no requiere cron job)
- Soporte para bloqueos de múltiples días
- Preparado para futuras extensiones

## Plan de Implementación

### Paso 1: Preparar Base de Datos
```bash
# Aplicar migración 007
psql -h <host> -U <user> -d <database> -f database/migrations/007_create_daily_quota_control.sql

# Migrar datos existentes
psql -h <host> -U <user> -d <database> -f database/migrations/migrate_to_new_quota_system.sql
```

### Paso 2: Actualizar Código Go
```bash
cd /Users/csarrion/Cline/proxy-bedrock

# Crear nuevo archivo
touch pkg/database/quota_queries.go

# Actualizar middleware
# Editar pkg/auth/middleware.go
```

### Paso 3: Testing
```bash
# Test unitarios
go test ./pkg/database/...

# Test de integración
go test ./pkg/auth/...

# Test end-to-end
curl -H "Authorization: Bearer <token>" http://localhost:8080/v1/messages
```

### Paso 4: Despliegue
```bash
# Build
go build -o proxy-bedrock cmd/proxy/main.go

# Deploy
./deploy.sh
```

## Compatibilidad con Sistema Antiguo

Durante la transición, ambos sistemas pueden coexistir:

1. **Mantener tablas antiguas** (`user_blocking_status`, `quota_usage`)
2. **Escribir en ambos sistemas** temporalmente
3. **Leer del nuevo sistema** para decisiones
4. **Eliminar sistema antiguo** después de validación

## Monitoreo y Observabilidad

### Métricas a Monitorear

```go
// Prometheus metrics
var (
	quotaChecksTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "quota_checks_total",
			Help: "Total number of quota checks",
		},
		[]string{"result"}, // allowed, blocked, error
	)

	quotaCheckDuration = prometheus.NewHistogram(
		prometheus.HistogramOpts{
			Name: "quota_check_duration_seconds",
			Help: "Duration of quota checks",
		},
	)

	usersBlockedTotal = prometheus.NewCounter(
		prometheus.CounterOpts{
			Name: "users_blocked_total",
			Help: "Total number of users blocked",
		},
	)
)
```

### Logs Estructurados

```go
Logger.InfoContext(ctx, amslog.Event{
	Name: "QUOTA_CHECK",
	Fields: map[string]interface{}{
		"user.id": userID,
		"quota.allowed": result.Allowed,
		"quota.requests_today": result.RequestsToday,
		"quota.daily_limit": result.DailyLimit,
		"quota.is_blocked": result.IsBlocked,
	},
})
```

## Conclusión

Esta arquitectura proporciona:

✅ **Simplicidad**: Una función hace todo el control de cuotas  
✅ **Atomicidad**: Sin race conditions  
✅ **Flexibilidad**: Bloqueos de múltiples días  
✅ **Escalabilidad**: Reset distribuido automático  
✅ **Auditoría**: Historial completo de bloqueos  
✅ **Mantenibilidad**: Lógica en PostgreSQL, fácil de actualizar  

La migración es incremental y permite validación antes de eliminar el sistema antiguo.