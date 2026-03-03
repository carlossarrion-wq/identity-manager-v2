# Plan de Migración: Proxy-Bedrock al Nuevo Sistema de Control de Cuotas

## Objetivo

Migrar el proxy-bedrock desde el sistema actual de control de cuotas a la nueva arquitectura basada en funciones PostgreSQL, manteniendo compatibilidad durante la transición y sin interrumpir el servicio.

## Resumen Ejecutivo

- **Duración Estimada**: 1-2 semanas
- **Riesgo**: Bajo-Medio (BD separada, solo cambios en código Go)
- **Estrategia**: Desarrollo incremental con tests
- **Downtime**: 0 (migración sin interrupción)
- **Base de Datos**: Separada del proxy (ya existe con nuevas tablas)

## Fases de Migración

### FASE 0: Preparación (Día 1)

#### 0.1. Análisis de Código Actual

**Tareas:**
- [ ] Crear branch de desarrollo en Git
- [ ] Identificar queries que usan tablas antiguas
- [ ] Listar funciones Go a actualizar
- [ ] Identificar endpoints afectados

**Comandos:**
```bash
cd /Users/csarrion/Cline/proxy-bedrock
git checkout -b feature/new-quota-system
git push -u origin feature/new-quota-system
```

**Archivos a Analizar:**
```
proxy-bedrock/
├── pkg/database/queries.go          → Queries a migrar
├── pkg/auth/middleware.go           → Integración de cuotas
├── pkg/bedrock.go                   → Post-processing
└── pkg/quota/                       → Módulo de cuotas (si existe)
```

**Entregables:**
- ✅ Branch de Git creado
- ✅ Lista de queries a migrar
- ✅ Lista de funciones Go a actualizar

---

### FASE 1: Desarrollo en Go (Días 2-6)

#### 2.1. Crear Nuevo Módulo de Queries

**Tareas:**
- [ ] Crear archivo `pkg/database/quota_queries.go`
- [ ] Implementar structs de datos
- [ ] Implementar funciones de queries
- [ ] Añadir manejo de errores
- [ ] Añadir logging

**Archivo a Crear:**
```go
// Archivo: pkg/database/quota_queries.go
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
func (db *Database) CheckAndUpdateQuota(ctx context.Context, cognitoUserID, cognitoEmail string) (*QuotaCheckResult, error) {
	query := `SELECT * FROM check_and_update_quota($1, $2)`
	
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

// ... (resto de funciones según documento de integración)
```

**Comandos:**
```bash
cd /Users/csarrion/Cline/proxy-bedrock

# Crear archivo
touch pkg/database/quota_queries.go

# Editar archivo
code pkg/database/quota_queries.go
```

**Entregables:**
- ✅ Archivo `quota_queries.go` creado
- ✅ Funciones implementadas
- ✅ Tests unitarios

#### 2.2. Actualizar Middleware de Autenticación

**Tareas:**
- [ ] Modificar `pkg/auth/middleware.go`
- [ ] Integrar llamada a `CheckAndUpdateQuota()`
- [ ] Añadir manejo de respuesta 429
- [ ] Añadir headers de rate limit
- [ ] Actualizar logging

**Cambios en `middleware.go`:**
```go
// Después de la autenticación exitosa (línea ~150)

// NUEVO: Verificar cuota
quotaResult, err := am.db.CheckAndUpdateQuota(r.Context(), userCtx.UserID, userCtx.Email)
if err != nil {
	Logger.ErrorContext(r.Context(), amslog.Event{
		Name:    "QUOTA_CHECK_ERROR",
		Message: "Failed to check quota",
		Error: &amslog.ErrorInfo{
			Type:    "QuotaCheckError",
			Message: err.Error(),
		},
	})
	am.respondError(w, r, http.StatusInternalServerError, 
		"quota check failed", "quota_check_error")
	return
}

// Si no está permitido, rechazar
if !quotaResult.Allowed {
	Logger.WarningContext(r.Context(), amslog.Event{
		Name:    "QUOTA_EXCEEDED",
		Message: quotaResult.BlockReason,
		Outcome: amslog.OutcomeFailure,
		Fields: map[string]interface{}{
			"user.id":        userCtx.UserID,
			"requests_today": quotaResult.RequestsToday,
			"daily_limit":    quotaResult.DailyLimit,
		},
	})
	
	// Headers de rate limit
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("X-RateLimit-Limit", fmt.Sprintf("%d", quotaResult.DailyLimit))
	w.Header().Set("X-RateLimit-Remaining", "0")
	w.Header().Set("X-RateLimit-Reset", "midnight")
	w.WriteHeader(http.StatusTooManyRequests)
	
	fmt.Fprintf(w, `{"error":"%s","requests_today":%d,"daily_limit":%d}`, 
		quotaResult.BlockReason, quotaResult.RequestsToday, quotaResult.DailyLimit)
	return
}

// Añadir info de cuota al contexto
ctx = context.WithValue(ctx, "quota_info", quotaResult)

// Continuar con el siguiente handler...
```

**Entregables:**
- ✅ Middleware actualizado
- ✅ Tests de integración
- ✅ Documentación actualizada

#### 2.3. Actualizar Registro de Uso

**Tareas:**
- [ ] Crear función `InsertUsageTracking()` en `database.go`
- [ ] Actualizar `bedrock.go` para usar nueva función
- [ ] Mantener registro asíncrono (goroutine)
- [ ] Añadir retry logic para fallos

**Nueva Función en `database.go`:**
```go
// UsageTrackingData contiene los datos de uso a registrar
type UsageTrackingData struct {
	CognitoUserID       string
	CognitoEmail        string
	RequestTimestamp    time.Time
	ModelID             string
	SourceIP            string
	UserAgent           string
	AWSRegion           string
	TokensInput         int
	TokensOutput        int
	TokensCacheRead     int
	TokensCacheCreation int
	CostUSD             float64
	ProcessingTimeMS    int
	ResponseStatus      string
	ErrorMessage        string
}

// InsertUsageTracking inserta un registro de uso en la tabla de tracking
func (db *Database) InsertUsageTracking(ctx context.Context, usage *UsageTrackingData) error {
	query := `
		INSERT INTO "bedrock-proxy-usage-tracking-tbl" (
			cognito_user_id, cognito_email, request_timestamp, model_id,
			source_ip, user_agent, aws_region, tokens_input, tokens_output,
			tokens_cache_read, tokens_cache_creation, cost_usd,
			processing_time_ms, response_status, error_message
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
	`
	
	_, err := db.pool.Exec(ctx, query,
		usage.CognitoUserID, usage.CognitoEmail, usage.RequestTimestamp,
		usage.ModelID, usage.SourceIP, usage.UserAgent, usage.AWSRegion,
		usage.TokensInput, usage.TokensOutput, usage.TokensCacheRead,
		usage.TokensCacheCreation, usage.CostUSD, usage.ProcessingTimeMS,
		usage.ResponseStatus, usage.ErrorMessage,
	)
	
	return err
}
```

**Actualización en `bedrock.go`:**
```go
// En la goroutine de post-processing (línea ~1150)
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
	
	// Insertar con retry
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

**Entregables:**
- ✅ Función de tracking implementada
- ✅ Integración en bedrock.go
- ✅ Tests de registro asíncrono

#### 2.4. Tests Unitarios e Integración

**Tareas:**
- [ ] Tests unitarios para `quota_queries.go`
- [ ] Tests de integración para middleware
- [ ] Tests end-to-end del flujo completo
- [ ] Tests de carga (opcional)

**Archivos de Test:**
```bash
# Crear archivos de test
touch pkg/database/quota_queries_test.go
touch pkg/auth/middleware_quota_test.go
touch tests/integration/quota_flow_test.go
```

**Ejemplo de Test:**
```go
// pkg/database/quota_queries_test.go
package database

import (
	"context"
	"testing"
)

func TestCheckAndUpdateQuota(t *testing.T) {
	// Setup
	db := setupTestDB(t)
	defer db.Close()
	
	ctx := context.Background()
	userID := "test_user_001"
	email := "test@example.com"
	
	// Test 1: Primera petición
	result, err := db.CheckAndUpdateQuota(ctx, userID, email)
	if err != nil {
		t.Fatalf("Error: %v", err)
	}
	if !result.Allowed {
		t.Error("Primera petición debería estar permitida")
	}
	if result.RequestsToday != 1 {
		t.Errorf("Esperado requests_today=1, obtenido=%d", result.RequestsToday)
	}
	
	// Test 2: Alcanzar límite
	for i := 2; i <= 1000; i++ {
		db.CheckAndUpdateQuota(ctx, userID, email)
	}
	
	result, _ = db.CheckAndUpdateQuota(ctx, userID, email)
	if result.Allowed {
		t.Error("Petición 1001 debería estar bloqueada")
	}
	if !result.IsBlocked {
		t.Error("Usuario debería estar bloqueado")
	}
	
	// Cleanup
	cleanupTestUser(t, db, userID)
}
```

**Comandos:**
```bash
# Ejecutar tests
cd /Users/csarrion/Cline/proxy-bedrock

# Tests unitarios
go test ./pkg/database/... -v

# Tests de integración
go test ./tests/integration/... -v

# Coverage
go test ./... -cover
```

**Entregables:**
- ✅ Tests unitarios pasando
- ✅ Tests de integración pasando
- ✅ Reporte de coverage

---

### FASE 3: Despliegue y Validación (Días 11-14)

#### 3.1. Despliegue en Entorno de Desarrollo

**Tareas:**
- [ ] Build de nueva versión
- [ ] Desplegar en entorno dev
- [ ] Verificar conectividad a BD
- [ ] Ejecutar smoke tests
- [ ] Monitorear logs

**Comandos:**
```bash
cd /Users/csarrion/Cline/proxy-bedrock

# Build
go build -o proxy-bedrock-new cmd/proxy/main.go

# Verificar build
./proxy-bedrock-new --version

# Desplegar (ejemplo con systemd)
sudo systemctl stop proxy-bedrock
sudo cp proxy-bedrock-new /usr/local/bin/proxy-bedrock
sudo systemctl start proxy-bedrock

# Verificar logs
sudo journalctl -u proxy-bedrock -f
```

**Smoke Tests:**
```bash
# Test 1: Health check
curl http://localhost:8080/health

# Test 2: Request con token válido
curl -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"model":"claude-3-5-sonnet-20241022","messages":[{"role":"user","content":"test"}]}' \
     http://localhost:8080/v1/messages

# Test 3: Verificar headers de rate limit
curl -I -H "Authorization: Bearer <token>" \
     http://localhost:8080/v1/messages
```

**Entregables:**
- ✅ Aplicación desplegada en dev
- ✅ Smoke tests pasando
- ✅ Logs sin errores

#### 3.2. Testing de Compatibilidad

**Tareas:**
- [ ] Verificar que sistema antiguo sigue funcionando
- [ ] Comparar resultados entre sistemas
- [ ] Validar que no hay regresiones
- [ ] Documentar diferencias

**Script de Comparación:**
```sql
-- Comparar contadores entre sistemas
SELECT 
    'Antiguo' as sistema,
    user_id,
    daily_requests,
    is_blocked
FROM user_blocking_status
WHERE user_id IN (SELECT cognito_user_id FROM "bedrock-proxy-user-quotas-tbl")

UNION ALL

SELECT 
    'Nuevo' as sistema,
    cognito_user_id,
    requests_today,
    is_blocked
FROM "bedrock-proxy-user-quotas-tbl"
WHERE cognito_user_id IN (SELECT user_id FROM user_blocking_status)
ORDER BY user_id, sistema;
```

**Entregables:**
- ✅ Reporte de compatibilidad
- ✅ Diferencias documentadas
- ✅ Plan de corrección si hay issues

#### 3.3. Monitoreo y Métricas

**Tareas:**
- [ ] Configurar dashboards de Grafana
- [ ] Configurar alertas de Prometheus
- [ ] Monitorear latencia de queries
- [ ] Monitorear tasa de errores

**Métricas a Monitorear:**
```go
// Prometheus metrics
var (
	quotaChecksTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "quota_checks_total",
			Help: "Total quota checks",
		},
		[]string{"result"}, // allowed, blocked, error
	)
	
	quotaCheckDuration = prometheus.NewHistogram(
		prometheus.HistogramOpts{
			Name:    "quota_check_duration_seconds",
			Help:    "Duration of quota checks",
			Buckets: prometheus.DefBuckets,
		},
	)
	
	usersBlockedTotal = prometheus.NewCounter(
		prometheus.CounterOpts{
			Name: "users_blocked_total",
			Help: "Total users blocked",
		},
	)
)
```

**Queries de Grafana:**
```promql
# Tasa de peticiones permitidas vs bloqueadas
rate(quota_checks_total{result="allowed"}[5m])
rate(quota_checks_total{result="blocked"}[5m])

# Latencia p95 de verificación de cuota
histogram_quantile(0.95, rate(quota_check_duration_seconds_bucket[5m]))

# Usuarios bloqueados en las últimas 24h
increase(users_blocked_total[24h])
```

**Entregables:**
- ✅ Dashboards configurados
- ✅ Alertas configuradas
- ✅ Documentación de métricas

---

### FASE 4: Migración a Producción (Días 15-18)

#### 4.1. Preparación de Producción

**Tareas:**
- [ ] Backup completo de producción
- [ ] Crear plan de rollback
- [ ] Preparar scripts de migración
- [ ] Coordinar ventana de mantenimiento
- [ ] Notificar a usuarios

**Plan de Rollback:**
```bash
# Archivo: rollback_plan.sh

#!/bin/bash
set -e

echo "=== INICIANDO ROLLBACK ==="

# 1. Detener nueva versión
sudo systemctl stop proxy-bedrock

# 2. Restaurar versión anterior
sudo cp /backup/proxy-bedrock-old /usr/local/bin/proxy-bedrock

# 3. Rollback de BD (si es necesario)
psql -h <host> -U <user> -d <database> -f database/migrations/007_rollback_daily_quota_control.sql
psql -h <host> -U <user> -d <database> -f database/migrations/006_rollback_usage_tracking_table.sql

# 4. Iniciar versión anterior
sudo systemctl start proxy-bedrock

# 5. Verificar
curl http://localhost:8080/health

echo "=== ROLLBACK COMPLETADO ==="
```

**Entregables:**
- ✅ Backup de producción
- ✅ Plan de rollback documentado
- ✅ Scripts preparados

#### 4.2. Despliegue en Producción

**Tareas:**
- [ ] Aplicar migraciones de BD
- [ ] Migrar datos
- [ ] Desplegar nueva versión del proxy
- [ ] Verificar funcionamiento
- [ ] Monitorear durante 24h

**Procedimiento de Despliegue:**
```bash
# 1. Backup
pg_dump -h <prod-host> -U <user> -d <database> -F c -f backup_prod_$(date +%Y%m%d_%H%M%S).dump

# 2. Aplicar migraciones
psql -h <prod-host> -U <user> -d <database> -f database/migrations/006_create_usage_tracking_table.sql
psql -h <prod-host> -U <user> -d <database> -f database/migrations/007_create_daily_quota_control.sql
psql -h <prod-host> -U <user> -d <database> -f database/migrations/008_migrate_quota_data.sql

# 3. Verificar migraciones
psql -h <prod-host> -U <user> -d <database> -c "\dt bedrock-proxy*"

# 4. Desplegar proxy (blue-green deployment)
# Mantener versión antigua corriendo
# Desplegar nueva versión en paralelo
# Cambiar tráfico gradualmente

# 5. Monitorear
watch -n 5 'curl -s http://localhost:8080/metrics | grep quota'
```

**Entregables:**
- ✅ Migraciones aplicadas
- ✅ Proxy desplegado
- ✅ Verificación exitosa

#### 4.3. Validación Post-Despliegue

**Tareas:**
- [ ] Ejecutar tests de humo en producción
- [ ] Verificar métricas de negocio
- [ ] Revisar logs de errores
- [ ] Validar con usuarios piloto
- [ ] Documentar issues encontrados

**Checklist de Validación:**
```
✅ Health check responde OK
✅ Autenticación funciona correctamente
✅ Verificación de cuota funciona
✅ Bloqueo automático funciona
✅ Registro de uso funciona (asíncrono)
✅ Métricas se reportan correctamente
✅ No hay errores en logs
✅ Latencia dentro de SLA
✅ Usuarios piloto confirman funcionamiento
```

**Entregables:**
- ✅ Checklist completado
- ✅ Reporte de validación
- ✅ Issues documentados

---

### FASE 5: Limpieza y Documentación (Días 19-21)

#### 5.1. Deprecar Sistema Antiguo

**Tareas:**
- [ ] Mantener sistema antiguo 2 semanas en paralelo
- [ ] Monitorear que no se use
- [ ] Eliminar código antiguo
- [ ] Eliminar tablas antiguas (después de validación)

**Script de Limpieza:**
```sql
-- Archivo: database/migrations/009_cleanup_old_system.sql
-- EJECUTAR SOLO DESPUÉS DE 2 SEMANAS DE VALIDACIÓN

BEGIN;

-- 1. Backup de tablas antiguas
CREATE TABLE user_blocking_status_backup AS SELECT * FROM user_blocking_status;
CREATE TABLE quota_usage_backup AS SELECT * FROM quota_usage;

-- 2. Eliminar tablas antiguas
DROP TABLE IF EXISTS user_blocking_status CASCADE;
DROP TABLE IF EXISTS quota_usage CASCADE;

-- 3. Eliminar funciones antiguas (si existen)
DROP FUNCTION IF EXISTS check_user_quota_old CASCADE;
DROP FUNCTION IF EXISTS update_quota_old CASCADE;

COMMIT;

-- Verificar
SELECT table_name FROM information_schema.tables 
WHERE table_name LIKE '%backup%';
```

**Entregables:**
- ✅ Sistema antiguo deprecado
- ✅ Código limpio
- ✅ Tablas eliminadas

#### 5.2. Documentación Final

**Tareas:**
- [ ] Actualizar README del proxy
- [ ] Documentar nueva arquitectura
- [ ] Crear guía de troubleshooting
- [ ] Documentar procedimientos operativos
- [ ] Crear runbook

**Documentos a Crear/Actualizar:**
```
docs/
├── ARCHITECTURE.md              → Arquitectura actualizada
├── QUOTA_SYSTEM.md              → Sistema de cuotas
├── TROUBLESHOOTING.md           → Guía de problemas comunes
├── RUNBOOK.md                   → Procedimientos operativos
└── MIGRATION_REPORT.md          → Reporte de migración
```

**Entregables:**
- ✅ Documentación actualizada
- ✅ Guías operativas
- ✅ Runbook completo

#### 5.3. Retrospectiva y Lecciones Aprendidas

**Tareas:**
- [ ] Reunión de retrospectiva
- [ ] Documentar lecciones aprendidas
- [ ] Identificar mejoras para futuras migraciones
- [ ] Actualizar proceso de migración

**Entregables:**
- ✅ Documento de lecciones aprendidas
- ✅ Mejoras identificadas
- ✅ Proceso actualizado

---

## Criterios de Éxito

### Funcionales
- ✅ Sistema de cuotas funciona correctamente
- ✅ Bloqueo automático funciona
- ✅ Reset diario funciona
- ✅ Desbloqueo administrativo funciona
- ✅ Registro de uso funciona (asíncrono)

### No Funcionales
- ✅ Latencia < 50ms para verificación de cuota
- ✅ 0 downtime durante migración
- ✅ 0 pérdida de datos
- ✅ Coverage de tests > 80%
- ✅ Documentación completa

### Operacionales
- ✅ Monitoreo configurado
- ✅ Alertas configuradas
- ✅ Runbook disponible
- ✅ Plan de rollback probado

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Pérdida de datos durante migración | Baja | Alto | Backups completos antes de cada paso |
| Incompatibilidad de datos | Media | Medio | Tests exhaustivos en dev |
| Degradación de rendimiento | Media | Alto | Load testing antes de producción |
| Bugs en nueva implementación | Media | Alto | Tests unitarios + integración + E2E |
| Rollback necesario | Baja | Alto | Plan de rollback documentado y probado |

## Recursos Necesarios

### Humanos
- 1 Desarrollador Go (full-time)
- 1 DBA (part-time)
- 1 DevOps (part-time)
- 1 QA (part-time)

### Infraestructura
- Entorno de desarrollo
- Entorno de staging
- Acceso a producción
- Herramientas de monitoreo

### Tiempo
- **Total**: 15-21 días laborables
- **Esfuerzo**: ~120-160 horas

## Conclusión

Este plan de migración proporciona una ruta clara y segura para migrar el proxy-bedrock al nuevo sistema de control de cuotas, minimizando riesgos y asegurando una transición sin interrupciones del servicio.