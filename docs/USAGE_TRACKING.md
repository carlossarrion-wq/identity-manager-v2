# Bedrock Proxy Usage Tracking

## Descripción General

El sistema de seguimiento de uso (`bedrock-proxy-usage-tracking-tbl`) registra todas las peticiones realizadas al proxy de Bedrock, incluyendo métricas de tokens, costos, rendimiento y errores. Esta información es esencial para:

- **Monitoreo de costos**: Seguimiento detallado del gasto por usuario y modelo
- **Análisis de rendimiento**: Identificación de cuellos de botella y optimización
- **Auditoría**: Registro completo de todas las peticiones
- **Detección de errores**: Identificación rápida de problemas
- **Planificación de capacidad**: Análisis de patrones de uso

## Estructura de la Tabla

### Tabla Principal: `bedrock-proxy-usage-tracking-tbl`

```sql
CREATE TABLE "bedrock-proxy-usage-tracking-tbl" (
    id UUID PRIMARY KEY,
    cognito_user_id VARCHAR(255) NOT NULL,
    cognito_email VARCHAR(255) NOT NULL,
    request_timestamp TIMESTAMP NOT NULL,
    model_id UUID NOT NULL,  -- FK a identity-manager-profiles-tbl
    source_ip VARCHAR(45),
    user_agent TEXT,
    aws_region VARCHAR(50),
    tokens_input INTEGER,
    tokens_output INTEGER,
    tokens_cache_read INTEGER DEFAULT 0,
    tokens_cache_creation INTEGER DEFAULT 0,
    cost_usd DECIMAL(10, 6),
    processing_time_ms INTEGER,
    response_status VARCHAR(20) NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL
);
```

### Campos Principales

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | UUID | Identificador único del registro |
| `cognito_user_id` | VARCHAR(255) | ID del usuario de Cognito |
| `cognito_email` | VARCHAR(255) | Email del usuario |
| `request_timestamp` | TIMESTAMP | Momento de la petición |
| `model_id` | UUID | Referencia al perfil de modelo usado |
| `source_ip` | VARCHAR(45) | IP de origen de la petición |
| `user_agent` | TEXT | User agent del cliente |
| `aws_region` | VARCHAR(50) | Región de AWS donde se procesó |
| `tokens_input` | INTEGER | Tokens de entrada procesados |
| `tokens_output` | INTEGER | Tokens de salida generados |
| `tokens_cache_read` | INTEGER | Tokens leídos desde caché |
| `tokens_cache_creation` | INTEGER | Tokens escritos en caché |
| `cost_usd` | DECIMAL(10,6) | Costo aproximado en USD |
| `processing_time_ms` | INTEGER | Tiempo de procesamiento en ms |
| `response_status` | VARCHAR(20) | Estado: success, error, timeout |
| `error_message` | TEXT | Mensaje de error si aplica |

## Índices

La tabla incluye índices optimizados para consultas comunes:

```sql
-- Búsquedas por usuario
CREATE INDEX idx_usage_cognito_user ON "bedrock-proxy-usage-tracking-tbl"(cognito_user_id);

-- Búsquedas por timestamp (análisis temporal)
CREATE INDEX idx_usage_request_timestamp ON "bedrock-proxy-usage-tracking-tbl"(request_timestamp DESC);

-- Búsquedas por modelo
CREATE INDEX idx_usage_model ON "bedrock-proxy-usage-tracking-tbl"(model_id);

-- Análisis de uso por usuario y fecha
CREATE INDEX idx_usage_user_timestamp ON "bedrock-proxy-usage-tracking-tbl"(cognito_user_id, request_timestamp DESC);

-- Análisis de costos por modelo y fecha
CREATE INDEX idx_usage_model_timestamp ON "bedrock-proxy-usage-tracking-tbl"(model_id, request_timestamp DESC);

-- Búsqueda de errores
CREATE INDEX idx_usage_errors ON "bedrock-proxy-usage-tracking-tbl"(response_status, request_timestamp DESC)
    WHERE response_status != 'success';
```

## Vistas Analíticas

### 1. `v_usage_by_user` - Resumen por Usuario

Agrega el uso total por usuario:

```sql
SELECT * FROM v_usage_by_user;
```

**Campos retornados:**
- `cognito_user_id`, `cognito_email`
- `total_requests`, `successful_requests`, `failed_requests`
- `total_tokens_input`, `total_tokens_output`
- `total_tokens_cache_read`, `total_tokens_cache_creation`
- `total_cost_usd`, `avg_processing_time_ms`
- `first_request`, `last_request`

### 2. `v_usage_by_model` - Resumen por Modelo

Agrega el uso total por modelo:

```sql
SELECT * FROM v_usage_by_model;
```

**Campos retornados:**
- `model_id`, `profile_name`, `model_name`, `provider`
- Métricas agregadas similares a `v_usage_by_user`

### 3. `v_usage_daily` - Resumen Diario

Agrega el uso por día:

```sql
SELECT * FROM v_usage_daily
WHERE usage_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY usage_date DESC;
```

**Campos retornados:**
- `usage_date`
- `total_requests`, `unique_users`
- `successful_requests`, `failed_requests`
- Métricas de tokens y costos agregadas

### 4. `v_usage_detailed` - Vista Detallada

Combina información de múltiples tablas:

```sql
SELECT * FROM v_usage_detailed
WHERE request_timestamp >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
ORDER BY request_timestamp DESC;
```

### 5. `v_top_users_by_cost` - Top Usuarios por Costo

Usuarios ordenados por gasto total:

```sql
SELECT * FROM v_top_users_by_cost
LIMIT 10;
```

### 6. `v_recent_errors` - Errores Recientes

Últimos 100 errores registrados:

```sql
SELECT * FROM v_recent_errors;
```

## Funciones Útiles

### 1. `calculate_usage_cost()` - Calcular Costo

Calcula el costo estimado basado en tokens y proveedor:

```sql
SELECT calculate_usage_cost(
    1000,        -- tokens_input
    500,         -- tokens_output
    'anthropic'  -- provider
);
```

**Precios por defecto (por 1K tokens):**
- **Anthropic**: Input $0.003, Output $0.015
- **Amazon**: Input $0.0008, Output $0.0024
- **Meta**: Input $0.0002, Output $0.0002
- **Otros**: Input $0.001, Output $0.003

### 2. `get_usage_stats()` - Estadísticas de Uso

Obtiene estadísticas agregadas para un período:

```sql
-- Estadísticas de todos los usuarios en las últimas 24 horas
SELECT * FROM get_usage_stats(
    CURRENT_TIMESTAMP - INTERVAL '24 hours',
    CURRENT_TIMESTAMP
);

-- Estadísticas de un usuario específico
SELECT * FROM get_usage_stats(
    CURRENT_TIMESTAMP - INTERVAL '7 days',
    CURRENT_TIMESTAMP,
    'us-east-1_abc123def'  -- cognito_user_id
);
```

**Retorna:**
- `total_requests`, `successful_requests`, `failed_requests`
- `total_tokens_input`, `total_tokens_output`
- `total_cost_usd`, `avg_processing_time_ms`
- `unique_users`

### 3. `archive_old_usage_data()` - Archivar Datos Antiguos

Función para gestionar la retención de datos:

```sql
-- Archivar datos más antiguos de 365 días
SELECT archive_old_usage_data(365);
```

**Nota:** Por defecto está comentada. Descomentar según política de retención.

## Consultas Comunes

### Uso por Usuario en el Último Mes

```sql
SELECT 
    cognito_email,
    COUNT(*) as requests,
    SUM(tokens_input + tokens_output) as total_tokens,
    SUM(cost_usd) as total_cost,
    AVG(processing_time_ms) as avg_time_ms
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE request_timestamp >= CURRENT_TIMESTAMP - INTERVAL '30 days'
GROUP BY cognito_email
ORDER BY total_cost DESC;
```

### Tasa de Errores por Modelo

```sql
SELECT 
    p.profile_name,
    m.model_name,
    COUNT(*) as total_requests,
    COUNT(CASE WHEN u.response_status = 'success' THEN 1 END) as successful,
    COUNT(CASE WHEN u.response_status != 'success' THEN 1 END) as failed,
    ROUND(100.0 * COUNT(CASE WHEN u.response_status != 'success' THEN 1 END) / COUNT(*), 2) as error_rate_pct
FROM "bedrock-proxy-usage-tracking-tbl" u
JOIN "identity-manager-profiles-tbl" p ON u.model_id = p.id
JOIN "identity-manager-models-tbl" m ON p.model_id = m.id
WHERE u.request_timestamp >= CURRENT_TIMESTAMP - INTERVAL '7 days'
GROUP BY p.profile_name, m.model_name
ORDER BY error_rate_pct DESC;
```

### Análisis de Rendimiento por Hora del Día

```sql
SELECT 
    EXTRACT(HOUR FROM request_timestamp) as hour_of_day,
    COUNT(*) as requests,
    AVG(processing_time_ms) as avg_time_ms,
    MAX(processing_time_ms) as max_time_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY processing_time_ms) as p95_time_ms
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE request_timestamp >= CURRENT_TIMESTAMP - INTERVAL '7 days'
    AND response_status = 'success'
GROUP BY EXTRACT(HOUR FROM request_timestamp)
ORDER BY hour_of_day;
```

### Uso de Caché

```sql
SELECT 
    DATE(request_timestamp) as date,
    COUNT(*) as total_requests,
    COUNT(CASE WHEN tokens_cache_read > 0 THEN 1 END) as requests_with_cache,
    SUM(tokens_cache_read) as total_cache_reads,
    SUM(tokens_cache_creation) as total_cache_writes,
    ROUND(100.0 * COUNT(CASE WHEN tokens_cache_read > 0 THEN 1 END) / COUNT(*), 2) as cache_hit_rate_pct
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE request_timestamp >= CURRENT_TIMESTAMP - INTERVAL '30 days'
GROUP BY DATE(request_timestamp)
ORDER BY date DESC;
```

### Top 10 Peticiones Más Costosas

```sql
SELECT 
    u.id,
    u.cognito_email,
    u.request_timestamp,
    p.profile_name,
    m.model_name,
    u.tokens_input,
    u.tokens_output,
    u.cost_usd,
    u.processing_time_ms
FROM "bedrock-proxy-usage-tracking-tbl" u
JOIN "identity-manager-profiles-tbl" p ON u.model_id = p.id
JOIN "identity-manager-models-tbl" m ON p.model_id = m.id
WHERE u.response_status = 'success'
ORDER BY u.cost_usd DESC
LIMIT 10;
```

## Integración con la Aplicación

### Insertar Registro de Uso

```python
def log_usage(
    cognito_user_id: str,
    cognito_email: str,
    model_id: str,
    source_ip: str,
    user_agent: str,
    aws_region: str,
    tokens_input: int,
    tokens_output: int,
    tokens_cache_read: int,
    tokens_cache_creation: int,
    cost_usd: float,
    processing_time_ms: int,
    response_status: str,
    error_message: str = None
):
    query = """
        INSERT INTO "bedrock-proxy-usage-tracking-tbl" (
            cognito_user_id, cognito_email, model_id,
            source_ip, user_agent, aws_region,
            tokens_input, tokens_output,
            tokens_cache_read, tokens_cache_creation,
            cost_usd, processing_time_ms,
            response_status, error_message
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """
    
    cursor.execute(query, (
        cognito_user_id, cognito_email, model_id,
        source_ip, user_agent, aws_region,
        tokens_input, tokens_output,
        tokens_cache_read, tokens_cache_creation,
        cost_usd, processing_time_ms,
        response_status, error_message
    ))
```

### Obtener Estadísticas de Usuario

```python
def get_user_usage_stats(cognito_user_id: str, days: int = 30):
    query = """
        SELECT * FROM get_usage_stats(
            CURRENT_TIMESTAMP - INTERVAL '%s days',
            CURRENT_TIMESTAMP,
            %s
        )
    """
    
    cursor.execute(query, (days, cognito_user_id))
    return cursor.fetchone()
```

## Mantenimiento

### Política de Retención

Se recomienda implementar una política de retención de datos:

1. **Datos recientes (< 90 días)**: Mantener en tabla principal
2. **Datos históricos (90-365 días)**: Considerar agregación
3. **Datos antiguos (> 365 días)**: Archivar o eliminar

### Monitoreo de Tamaño

```sql
-- Verificar tamaño de la tabla
SELECT 
    pg_size_pretty(pg_total_relation_size('"bedrock-proxy-usage-tracking-tbl"')) as total_size,
    pg_size_pretty(pg_relation_size('"bedrock-proxy-usage-tracking-tbl"')) as table_size,
    pg_size_pretty(pg_indexes_size('"bedrock-proxy-usage-tracking-tbl"')) as indexes_size;

-- Contar registros por mes
SELECT 
    DATE_TRUNC('month', request_timestamp) as month,
    COUNT(*) as records
FROM "bedrock-proxy-usage-tracking-tbl"
GROUP BY DATE_TRUNC('month', request_timestamp)
ORDER BY month DESC;
```

### Optimización de Índices

```sql
-- Analizar uso de índices
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE tablename = 'bedrock-proxy-usage-tracking-tbl'
ORDER BY idx_scan DESC;

-- Reindexar si es necesario
REINDEX TABLE "bedrock-proxy-usage-tracking-tbl";
```

## Migración

### Aplicar Migración

```bash
# Conectar a la base de datos
psql -h <host> -U <user> -d <database>

# Ejecutar migración
\i database/migrations/006_create_usage_tracking_table.sql

# Verificar
\dt bedrock-proxy-usage-tracking-tbl
\d+ bedrock-proxy-usage-tracking-tbl
```

### Rollback

```bash
# Ejecutar rollback
\i database/migrations/006_rollback_usage_tracking_table.sql
```

### Datos de Prueba

```bash
# Insertar datos de ejemplo
\i database/seeds/insert_usage_tracking_examples.sql
```

## Consideraciones de Seguridad

1. **Datos Sensibles**: La tabla contiene información de usuarios y patrones de uso
2. **Acceso Restringido**: Limitar permisos solo a roles necesarios
3. **Encriptación**: Considerar encriptación en reposo para datos sensibles
4. **Auditoría**: Los accesos a esta tabla deben ser auditados
5. **GDPR/Privacidad**: Implementar políticas de retención y eliminación

## Próximos Pasos

1. Integrar logging en el proxy de Bedrock
2. Crear dashboard de visualización
3. Configurar alertas para:
   - Costos anormales
   - Tasas de error elevadas
   - Tiempos de respuesta lentos
4. Implementar política de retención automatizada
5. Crear reportes periódicos automatizados