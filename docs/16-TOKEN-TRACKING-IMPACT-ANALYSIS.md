# Análisis de Impacto: Registro de Token JWT en Tabla de Tracking

**Fecha:** 23 de marzo de 2026  
**Autor:** Análisis técnico del sistema  
**Versión:** 1.0

## 1. Resumen Ejecutivo

Este documento analiza el impacto de añadir el token JWT (o su JTI) como campo en la tabla `bedrock-proxy-usage-tracking-tbl` para registrar qué token específico utilizó cada usuario en cada petición al proxy de Bedrock.

**Recomendación:** ⚠️ **NO RECOMENDADO** - Los riesgos de seguridad y privacidad superan significativamente los beneficios potenciales.

---

## 2. Contexto Actual

### 2.1. Estructura Actual de la Tabla

```sql
CREATE TABLE "bedrock-proxy-usage-tracking-tbl" (
    id uuid PRIMARY KEY,
    cognito_user_id varchar(255) NOT NULL,
    cognito_email varchar(255) NOT NULL,
    request_timestamp timestamp NOT NULL,
    model_id varchar(255) NOT NULL,
    source_ip varchar(45),
    user_agent text,
    aws_region varchar(50),
    tokens_input integer,
    tokens_output integer,
    tokens_cache_read integer DEFAULT 0,
    tokens_cache_creation integer DEFAULT 0,
    cost_usd numeric(10,6),
    processing_time_ms integer,
    response_status varchar(20) NOT NULL,
    error_message text,
    created_at timestamp DEFAULT CURRENT_TIMESTAMP,
    team varchar(100),
    person varchar(255)
);
```

### 2.2. Información Actualmente Registrada

- ✅ **Identidad del usuario**: `cognito_user_id`, `cognito_email`
- ✅ **Contexto organizacional**: `team`, `person` (extraídos del JWT)
- ✅ **Métricas de uso**: tokens, costos, tiempos
- ✅ **Información técnica**: IP, user agent, región
- ❌ **Token JWT o JTI**: NO se registra actualmente

---

## 3. Propuesta de Cambio

Añadir uno de estos campos a la tabla:

### Opción A: Registrar el JTI (JWT ID)
```sql
ALTER TABLE "bedrock-proxy-usage-tracking-tbl" 
ADD COLUMN jti varchar(255);
```

### Opción B: Registrar el token completo (hash)
```sql
ALTER TABLE "bedrock-proxy-usage-tracking-tbl" 
ADD COLUMN token_hash text;
```

---

## 4. Análisis de Impactos

### 4.1. 🔴 IMPACTO EN SEGURIDAD (CRÍTICO)

#### 4.1.1. Riesgo de Exposición de Credenciales

**Problema:**
- El token JWT es una credencial de acceso válida
- Si se registra el token completo (incluso hasheado), existe riesgo de:
  - Exposición en logs de base de datos
  - Acceso no autorizado a través de backups
  - Filtración en dumps de base de datos
  - Exposición en herramientas de monitoreo

**Severidad:** 🔴 CRÍTICA

**Mitigación parcial con JTI:**
- El JTI por sí solo no es una credencial válida
- Pero permite correlacionar actividad con tokens específicos
- Sigue siendo información sensible para auditoría

#### 4.1.2. Superficie de Ataque Ampliada

**Problema:**
- Cada registro adicional de credenciales aumenta la superficie de ataque
- La tabla de tracking tiene:
  - Alto volumen de registros (millones de filas)
  - Acceso frecuente desde múltiples servicios
  - Retención prolongada de datos

**Riesgo:**
- Mayor probabilidad de exposición accidental
- Más puntos de acceso potenciales para atacantes

#### 4.1.3. Correlación de Actividad

**Problema:**
- Permite rastrear todas las actividades de un token específico
- Si un token es comprometido, el atacante puede:
  - Ver todo el historial de uso del token
  - Identificar patrones de uso
  - Planificar ataques más sofisticados

### 4.2. 🟡 IMPACTO EN PRIVACIDAD Y CUMPLIMIENTO

#### 4.2.1. GDPR y Protección de Datos

**Consideraciones:**
- El token JWT contiene información personal (email, nombre, equipo)
- Registrar el token/JTI crea un registro adicional de datos personales
- Aumenta la complejidad del cumplimiento GDPR:
  - Derecho al olvido (más difícil de implementar)
  - Minimización de datos (principio violado)
  - Propósito específico (¿cuál es el propósito real?)

**Obligaciones adicionales:**
- Documentar el propósito específico del registro
- Justificar la necesidad legal o contractual
- Implementar mecanismos de anonimización/pseudonimización
- Actualizar políticas de privacidad

#### 4.2.2. Retención de Datos

**Problema actual:**
- La tabla de tracking retiene datos por 365 días (configurable)
- Añadir JTI/token extiende la vida útil de información sensible
- Conflicto con principio de minimización de datos

**Impacto:**
```sql
-- Función actual de archivo
CREATE FUNCTION archive_old_usage_data(p_days_to_keep integer DEFAULT 365)
```

### 4.3. 🟠 IMPACTO EN ALMACENAMIENTO

#### 4.3.1. Crecimiento de la Base de Datos

**Estimaciones:**

```
Escenario actual (sin JTI):
- Tamaño promedio por registro: ~500 bytes
- 1,000 peticiones/día: ~500 KB/día = ~180 MB/año
- 10,000 peticiones/día: ~5 MB/día = ~1.8 GB/año
- 100,000 peticiones/día: ~50 MB/día = ~18 GB/año

Con JTI (varchar(255)):
- Tamaño adicional por registro: ~40 bytes (UUID típico)
- Incremento: ~8% del tamaño total
- 100,000 peticiones/día: +4 MB/día = +1.4 GB/año

Con token_hash (text):
- Tamaño adicional por registro: ~64-128 bytes (SHA-256)
- Incremento: ~15% del tamaño total
- 100,000 peticiones/día: +8 MB/día = +2.9 GB/año
```

**Impacto en índices:**
```sql
-- Índice adicional necesario
CREATE INDEX idx_usage_jti ON "bedrock-proxy-usage-tracking-tbl" (jti);
-- Tamaño adicional del índice: ~20% del tamaño de los datos
```

#### 4.3.2. Costos de AWS RDS

**Estimación de costos adicionales:**
- Almacenamiento: $0.115/GB-mes (RDS PostgreSQL)
- Para 100K peticiones/día con JTI:
  - Año 1: +1.4 GB = +$1.61/mes = ~$19/año
  - Año 2: +2.8 GB = +$3.22/mes = ~$39/año
  - Año 3: +4.2 GB = +$4.83/mes = ~$58/año

**Nota:** Costos modestos pero acumulativos

### 4.4. 🟡 IMPACTO EN RENDIMIENTO

#### 4.4.1. Escritura de Datos

**Impacto en INSERT:**
```go
// Código actual
func (db *Database) InsertUsageTracking(ctx context.Context, data *UsageTrackingData) error {
    query := `INSERT INTO "bedrock-proxy-usage-tracking-tbl" (...) VALUES (...)`
    // 17 parámetros actuales
}

// Con JTI añadido
func (db *Database) InsertUsageTracking(ctx context.Context, data *UsageTrackingData) error {
    query := `INSERT INTO "bedrock-proxy-usage-tracking-tbl" (..., jti) VALUES (..., $18)`
    // 18 parámetros
}
```

**Impacto estimado:**
- Tiempo de INSERT: +2-5% (campo adicional + índice)
- Operación asíncrona, impacto mínimo en latencia del usuario
- Pero aumenta carga en el worker de métricas

#### 4.4.2. Consultas de Lectura

**Impacto en queries existentes:**
- Queries sin filtro por JTI: Sin impacto significativo
- Queries con filtro por JTI: Beneficio de índice

**Ejemplo de query nueva posible:**
```sql
-- Buscar todas las peticiones de un token específico
SELECT * FROM "bedrock-proxy-usage-tracking-tbl"
WHERE jti = 'abc-123-def-456'
ORDER BY request_timestamp DESC;
```

### 4.5. 🟢 IMPACTO EN AUDITORÍA Y TRAZABILIDAD

#### 4.5.1. Beneficios Potenciales

**Casos de uso positivos:**

1. **Investigación de Incidentes de Seguridad**
   ```sql
   -- Si un token es comprometido, ver todo su uso
   SELECT 
       request_timestamp,
       source_ip,
       model_id,
       response_status
   FROM "bedrock-proxy-usage-tracking-tbl"
   WHERE jti = 'compromised-token-jti'
   ORDER BY request_timestamp;
   ```

2. **Análisis de Regeneración de Tokens**
   ```sql
   -- Correlacionar uso antes y después de regeneración
   SELECT 
       old.jti as old_token,
       new.jti as new_token,
       COUNT(*) as requests_with_old_token
   FROM "bedrock-proxy-usage-tracking-tbl" old
   JOIN "identity-manager-tokens-tbl" t ON old.jti = t.jti
   WHERE t.regenerated_to_jti IS NOT NULL;
   ```

3. **Detección de Uso Anómalo**
   ```sql
   -- Detectar si un token se usa desde múltiples IPs
   SELECT 
       jti,
       COUNT(DISTINCT source_ip) as unique_ips,
       array_agg(DISTINCT source_ip) as ips
   FROM "bedrock-proxy-usage-tracking-tbl"
   WHERE request_timestamp > NOW() - INTERVAL '1 day'
   GROUP BY jti
   HAVING COUNT(DISTINCT source_ip) > 3;
   ```

#### 4.5.2. Limitaciones de los Beneficios

**Problema:** La mayoría de estos casos de uso ya están cubiertos

**Alternativas existentes:**

1. **Ya tenemos `cognito_user_id`** - Podemos rastrear por usuario
2. **Ya tenemos `source_ip`** - Podemos detectar anomalías de IP
3. **Ya tenemos `team` y `person`** - Contexto organizacional
4. **Tabla `identity-manager-tokens-tbl`** - Ya registra:
   - `last_used_at` - Última vez que se usó el token
   - `regenerated_at` - Cuándo se regeneró
   - `is_revoked` - Si está revocado

**Conclusión:** El valor añadido es marginal

---

## 5. Alternativas Recomendadas

### 5.1. ✅ Solución Actual (Mantener Status Quo)

**Ventajas:**
