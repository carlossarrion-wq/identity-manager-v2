# Análisis de Migración: Proxy-Bedrock

## Fecha: 2 de Marzo de 2026

## Objetivo
Identificar todas las queries, funciones y endpoints del proxy-bedrock que necesitan actualizarse para usar el nuevo sistema de control de cuotas.

---

## 1. Archivos de Base de Datos Actuales

### Ubicación
```
/Users/csarrion/Cline/proxy-bedrock/pkg/database/
├── database.go                    → Conexión y pool de PostgreSQL
├── queries.go                     → Queries actuales (REVISAR)
└── queries.go.backup-20260113     → Backup anterior
```

---

## 2. Funciones Identificadas en `queries.go`

Basado en la revisión anterior del archivo, las funciones actuales son:

### 2.1. Funciones de Validación de Token
```go
func (db *Database) ValidateToken(ctx context.Context, tokenHash string) (*TokenInfo, error)
```
- **Tablas usadas (BD ANTIGUA)**: `tokens`, `users`
- **Tablas nuevas (BD NUEVA)**: `identity-manager-tokens-tbl`, `identity-manager-profiles-tbl`, `identity-manager-models-tbl`
- **Acción**: Valida JWT contra BD
- **Estado**: ❌ **ACTUALIZAR** (cambiar a nuevas tablas, nueva BD y nueva clave JWT)

**Estructura del JWT (nuevo)**:
```json
{
  "user_id": "1285a444-d011-7063-0d76-ffeb254d0e69",
  "email": "carlos.sarrion@es.ibm.com",
  "default_inference_profile": "dc1b3985-78df-4ef6-804a-2cfb50f7dee3",
  "team": "lcs-sdlc-gen-group",
  "person": "Carlos Sarrión",
  "iss": "identity-manager",
  "sub": "1285a444-d011-7063-0d76-ffeb254d0e69",
  "aud": ["bedrock-proxy"],
  "exp": 1780176949,
  "iat": 1772400949,
  "jti": "f8c37207-0436-4bf6-b35f-42961c17611e"
}
```

**Cambios en Validación JWT**:
1. **Clave de Validación**: Cambiar a secreto `identity-mgmt-dev-key-access-lHcQeF`
2. **Claims del Token**: El JWT ya contiene `user_id`, `email`, `team`, `person`, `default_inference_profile`
3. **Validación en BD**: Solo verificar que el token no esté revocado y no haya expirado

**Query actual** (aproximado):
```sql
SELECT 
    t.jti, t.user_id, u.email, u.team, u.person, u.role,
    t.is_revoked, t.expires_at, u.monthly_quota_usd,
    u.daily_limit_usd, u.daily_request_limit, u.default_inference_profile
FROM tokens t
JOIN users u ON t.user_id = u.iam_username
WHERE t.token_hash = $1
  AND t.is_revoked = false
  AND t.expires_at > NOW()
  AND u.is_active = true
```

**Query nueva** (a implementar):
```sql
SELECT 
    t.jti,
    t.cognito_user_id,
    t.cognito_email,
    t.is_revoked,
    t.expires_at,
    p.model_arn,
    p.profile_name,
    p.cognito_group_name,
    m.model_id,
    m.model_name
FROM "identity-manager-tokens-tbl" t
JOIN "identity-manager-profiles-tbl" p ON t.application_profile_id = p.id
JOIN "identity-manager-models-tbl" m ON p.model_id = m.id
WHERE t.token_hash = $1
  AND t.is_revoked = false
  AND t.expires_at > NOW()
  AND p.is_active = true
```

**Cambios clave**:
- ✅ Cambiar clave JWT (usar secreto `identity-mgmt-dev-key-access-lHcQeF`)
- ✅ Cambiar conexión a nueva BD (usar secreto `identity-mgmt-dev-db-admin-mmq8Et`)
- ✅ Extraer `user_id`, `email`, `team`, `person` **del JWT** (no de BD)
- ✅ Usar `cognito_user_id` en lugar de `user_id` en BD
- ✅ Obtener `model_arn` desde `identity-manager-profiles-tbl`
- ✅ JOIN con `identity-manager-models-tbl` para info del modelo
- ⚠️ **IMPORTANTE**: `team`, `person` vienen en el JWT, no en la BD
- ❌ Ya no hay `monthly_quota_usd`, `daily_limit_usd` en BD (se obtienen de tabla de cuotas)

**Flujo de Validación Nuevo**:
1. Extraer JWT del header `Authorization: Bearer <token>`
2. Validar firma JWT con clave del secreto `identity-mgmt-dev-key-access-lHcQeF`
3. Extraer claims del JWT: `user_id`, `email`, `team`, `person`, `default_inference_profile`, `jti`
4. Calcular hash del token
5. Verificar en BD que el token no esté revocado ni expirado
6. Retornar información combinada (claims del JWT + datos de BD)

### 2.2. Funciones de Cuotas (A REEMPLAZAR)
```go
func (db *Database) CheckQuota(ctx context.Context, userID string) (*QuotaInfo, error)
```
- **Tablas usadas**: `users`, `quota_usage`, `user_blocking_status`
- **Acción**: Verifica límites de cuota
- **Estado**: ❌ **REEMPLAZAR** con `CheckAndUpdateQuota()`

```go
func (db *Database) UpdateQuotaAndCounters(ctx context.Context, userID string, costUSD float64) error
```
- **Tablas usadas**: `quota_usage`, `user_blocking_status`
- **Acción**: Actualiza contadores después de request
- **Estado**: ❌ **ELIMINAR** (ya no necesario, `check_and_update_quota()` lo hace)

```go
func (db *Database) CheckAndBlockUser(ctx context.Context, userID string) error
```
- **Tablas usadas**: `user_blocking_status`, `users`
- **Acción**: Verifica y bloquea usuario si excede límites
- **Estado**: ❌ **ELIMINAR** (ya no necesario, `check_and_update_quota()` lo hace)

### 2.3. Funciones de Métricas (A REEMPLAZAR)
```go
func (db *Database) InsertMetric(ctx context.Context, metric *MetricData) error
```
- **Tabla usada**: `request_metrics`
- **Acción**: Inserta métricas de request
- **Estado**: ❌ **REEMPLAZAR** con `InsertUsageTracking()`

### 2.4. Funciones de Reset (A ELIMINAR)
```go
func (db *Database) ResetDailyCounters(ctx context.Context) (*ResetResult, error)
```
- **Tabla usada**: `user_blocking_status`
- **Acción**: Reset diario de contadores
- **Estado**: ❌ **ELIMINAR** (reset automático en `check_and_update_quota()`)

---

## 3. Nuevas Funciones a Crear

### 3.1. Archivo: `pkg/database/quota_queries.go` (NUEVO)

```go
// Funciones principales
func (db *Database) CheckAndUpdateQuota(ctx, cognitoUserID, cognitoEmail string) (*QuotaCheckResult, error)
func (db *Database) GetUserQuotaStatus(ctx, cognitoUserID string) (*QuotaStatus, error)

// Funciones administrativas
func (db *Database) AdministrativeUnblockUser(ctx, cognitoUserID, adminUserID, reason string) error
func (db *Database) UpdateUserDailyLimit(ctx, cognitoUserID string, newLimit int) error
func (db *Database) AdministrativeBlockUser(ctx, cognitoUserID, adminUserID string, blockUntil time.Time, reason string) error

// Función de tracking
func (db *Database) InsertUsageTracking(ctx context.Context, usage *UsageTrackingData) error
```

---

## 4. Cambios en Middleware y Handlers

### 4.1. `pkg/auth/middleware.go`

**Ubicación del cambio**: Después de autenticación exitosa (~línea 150)

**Código actual** (aproximado):
```go
// Autenticación exitosa
userCtx := UserContext{...}

// Continuar con siguiente handler
next.ServeHTTP(w, r.WithContext(ctx))
```

**Código nuevo**:
```go
// Autenticación exitosa
userCtx := UserContext{...}

// NUEVO: Verificar cuota ANTES de continuar
quotaResult, err := am.db.CheckAndUpdateQuota(r.Context(), userCtx.UserID, userCtx.Email)
if err != nil {
    am.respondError(w, r, http.StatusInternalServerError, "quota check failed", "quota_check_error")
    return
}

if !quotaResult.Allowed {
    // Rechazar con HTTP 429
    w.Header().Set("X-RateLimit-Limit", fmt.Sprintf("%d", quotaResult.DailyLimit))
    w.Header().Set("X-RateLimit-Remaining", "0")
    w.WriteHeader(http.StatusTooManyRequests)
    fmt.Fprintf(w, `{"error":"%s"}`, quotaResult.BlockReason)
    return
}

// Continuar con siguiente handler
next.ServeHTTP(w, r.WithContext(ctx))
```

### 4.2. `pkg/bedrock.go`

**Ubicación del cambio**: En goroutine de post-processing (~línea 1150)

**Código actual** (aproximado):
```go
go func() {
    this.processMetrics(context.Background(), user, metricsCapture, startTime)
}()
```

**Código nuevo**:
```go
go func() {
    // Preparar datos de uso
    usageData := &database.UsageTrackingData{
        CognitoUserID:       user.UserID,
        CognitoEmail:        user.Email,
        RequestTimestamp:    startTime,
        ModelID:             modelID,
        SourceIP:            getClientIP(r),
        UserAgent:           r.UserAgent(),
        AWSRegion:           this.config.Region,
        TokensInput:         metricsCapture.InputTokens,
        TokensOutput:        metricsCapture.OutputTokens,
        TokensCacheRead:     metricsCapture.CacheReadTokens,
        TokensCacheCreation: metricsCapture.CacheWriteTokens,
        CostUSD:             calculateCost(...),
        ProcessingTimeMS:    int(time.Since(startTime).Milliseconds()),
        ResponseStatus:      "success",
        ErrorMessage:        "",
    }
    
    // Insertar de manera asíncrona
    if err := this.db.InsertUsageTracking(context.Background(), usageData); err != nil {
        Logger.ErrorContext(ctx, amslog.Event{
            Name:    "USAGE_TRACKING_ERROR",
            Message: "Failed to insert usage tracking",
            Error: &amslog.ErrorInfo{
                Type:    "DatabaseError",
                Message: err.Error(),
            },
        })
    }
}()
```

---

## 5. Endpoints Afectados

### 5.1. Endpoint Principal: `/v1/messages`

**Handler**: `bedrock.HandleProxy()`

**Flujo actual**:
```
1. Request → AuthMiddleware (valida JWT)
2. → bedrock.HandleProxy() (procesa request)
3. → Bedrock API (streaming/no-streaming)
4. → Response al cliente
5. → [Async] processMetrics() (registra métricas)
```

**Flujo nuevo**:
```
1. Request → AuthMiddleware (valida JWT)
2. → AuthMiddleware (NUEVO: verifica cuota con check_and_update_quota)
   ├─ Si excede → HTTP 429 (FIN)
   └─ Si OK → Continuar
3. → bedrock.HandleProxy() (procesa request)
4. → Bedrock API (streaming/no-streaming)
5. → Response al cliente
6. → [Async] InsertUsageTracking() (registra uso detallado)
```

### 5.2. Otros Endpoints (Si existen)

- `/health` → No afectado
- `/metrics` → No afectado (Prometheus)
- `/models` → No afectado

---

## 6. Bases de Datos y Tablas

### 6.1. BASE DE DATOS ANTIGUA (Proxy-Bedrock actual)

**Conexión**: Configurada en el proxy actual  
**Tablas a deprecar**:

| Tabla | Uso Actual | Estado |
|-------|------------|--------|
| `user_blocking_status` | Contadores diarios y bloqueos | ❌ Deprecar |
| `quota_usage` | Uso mensual agregado | ❌ Deprecar |
| `request_metrics` | Métricas detalladas | ❌ Deprecar |
| `tokens` | Tokens JWT | ❌ Deprecar |
| `users` | Información de usuarios | ❌ Deprecar |

### 6.2. BASE DE DATOS NUEVA (Identity Manager)

**Conexión a BD**: AWS Secrets Manager  
**ARN del Secreto (BD)**: `arn:aws:secretsmanager:eu-west-1:701055077130:secret:identity-mgmt-dev-db-admin-mmq8Et`

**Validación JWT**: AWS Secrets Manager  
**ARN del Secreto (JWT Key)**: `arn:aws:secretsmanager:eu-west-1:701055077130:secret:identity-mgmt-dev-key-access-lHcQeF`

**Tablas de Autenticación**:

| Tabla | Propósito | Reemplaza a |
|-------|-----------|-------------|
| `identity-manager-tokens-tbl` | Tokens JWT emitidos | `tokens` |
| `identity-manager-profiles-tbl` | Perfiles de aplicación (modelo + grupo) | `users` (parcial) |
| `identity-manager-models-tbl` | Catálogo de modelos LLM | N/A (nueva) |
| `identity-manager-applications-tbl` | Aplicaciones del sistema | N/A (nueva) |

**Tablas de Control de Cuotas** (YA EXISTEN):

| Tabla | Propósito | Reemplaza a |
|-------|-----------|-------------|
| `bedrock-proxy-user-quotas-tbl` | Control de cuotas diarias | `user_blocking_status` |
| `bedrock-proxy-quota-blocks-history-tbl` | Historial de bloqueos | N/A (nueva) |
| `bedrock-proxy-usage-tracking-tbl` | Tracking detallado de uso | `request_metrics` |

**Tablas de Permisos** (para futuro):

| Tabla | Propósito |
|-------|-----------|
| `identity-manager-permission-types-tbl` | Tipos de permisos |
| `identity-manager-app-permissions-tbl` | Permisos sobre aplicaciones |
| `identity-manager-module-permissions-tbl` | Permisos sobre módulos |

**Tablas de Auditoría**:

| Tabla | Propósito |
|-------|-----------|
| `identity-manager-audit-tbl` | Registro de auditoría |
| `identity-manager-config-tbl` | Configuración de la aplicación |

---

## 7. Funciones PostgreSQL Disponibles

### 7.1. Funciones de Cuotas

```sql
-- Verificar y actualizar cuota (PRINCIPAL)
SELECT * FROM check_and_update_quota(cognito_user_id, cognito_email);

-- Obtener estado de cuota
SELECT * FROM get_user_quota_status(cognito_user_id);

-- Desbloqueo administrativo
SELECT administrative_unblock_user(cognito_user_id, admin_user_id, reason);

-- Actualizar límite diario
SELECT update_user_daily_limit(cognito_user_id, new_limit);

-- Bloqueo administrativo
SELECT administrative_block_user(cognito_user_id, admin_user_id, block_until, reason);
```

---

## 8. Resumen de Cambios

### Archivos a Crear
- ✅ `pkg/database/quota_queries.go` (nuevo)

### Archivos a Modificar
- ✅ `pkg/auth/middleware.go` (añadir verificación de cuota)
- ✅ `pkg/bedrock.go` (actualizar post-processing)

### Archivos a Deprecar (después de validación)
- ❌ Funciones en `pkg/database/queries.go`:
  - `CheckQuota()`
  - `UpdateQuotaAndCounters()`
  - `CheckAndBlockUser()`
  - `InsertMetric()`
  - `ResetDailyCounters()`

### Funciones a Actualizar
- ❌ `ValidateToken()` → **ACTUALIZAR** (cambiar a nueva BD y nuevas tablas)

---

## 9. Plan de Acción Inmediato

### Paso 1: Crear `quota_queries.go`
```bash
cd /Users/csarrion/Cline/proxy-bedrock
touch pkg/database/quota_queries.go
```

### Paso 2: Implementar Funciones
- Implementar `CheckAndUpdateQuota()`
- Implementar `InsertUsageTracking()`
- Implementar funciones administrativas

### Paso 3: Actualizar Middleware
- Añadir verificación de cuota después de autenticación
- Añadir manejo de HTTP 429
- Añadir headers de rate limit

### Paso 4: Actualizar Post-Processing
- Reemplazar `InsertMetric()` con `InsertUsageTracking()`
- Mantener ejecución asíncrona (goroutine)

### Paso 5: Tests
- Tests unitarios para `quota_queries.go`
- Tests de integración para middleware
- Tests end-to-end del flujo completo

---

## 10. Riesgos Identificados

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Incompatibilidad de datos entre sistemas | Media | Medio | Tests exhaustivos en dev |
| Cambio de comportamiento en bloqueos | Media | Alto | Validación con usuarios piloto |
| Degradación de rendimiento | Baja | Alto | Load testing antes de producción |
| Bugs en nueva implementación | Media | Alto | Tests completos + code review |

---

## 11. Próximos Pasos

1. ✅ **Análisis completado** (este documento)
2. ⏭️ **Crear `quota_queries.go`** con todas las funciones
3. ⏭️ **Actualizar `middleware.go`** con verificación de cuota
4. ⏭️ **Actualizar `bedrock.go`** con nuevo tracking
5. ⏭️ **Crear tests** unitarios e integración
6. ⏭️ **Desplegar en dev** y validar
7. ⏭️ **Desplegar en producción** gradualmente

---

## Conclusión

El análisis identifica claramente:
- **5 funciones a reemplazar/eliminar** en `queries.go`
- **1 archivo nuevo a crear** (`quota_queries.go`)
- **2 archivos a modificar** (`middleware.go`, `bedrock.go`)
- **1 endpoint principal afectado** (`/v1/messages`)
- **Riesgo controlado** con tests y despliegue gradual

La migración es factible en 1-2 semanas con el plan propuesto.