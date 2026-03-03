# Propuesta: Control de Uso Diario (Daily Usage Control)

## 📋 Resumen Ejecutivo

Sistema de control de cuotas diarias por usuario para limitar el número de peticiones al proxy de Bedrock, con bloqueo automático al alcanzar el límite y desbloqueo automático a medianoche o manual por administrador.

## 🎯 Requisitos

1. **Budget diario por usuario**: Límite configurable de peticiones diarias
2. **Contabilización automática**: Incremento del contador con cada petición
3. **Bloqueo automático**: Al alcanzar el límite, bloquear al usuario
4. **Desbloqueo automático**: A las 00:00h del día siguiente
5. **Desbloqueo manual**: Administrador puede desbloquear con flag `administrative_safe`

## 🏗️ Propuesta de Arquitectura

### Opción 1: Tabla Independiente de Cuotas (⭐ RECOMENDADA)

#### Nueva Tabla: `bedrock-proxy-user-quotas-tbl`

```sql
CREATE TABLE "bedrock-proxy-user-quotas-tbl" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cognito_user_id VARCHAR(255) NOT NULL UNIQUE,
    cognito_email VARCHAR(255) NOT NULL,
    
    -- Configuración de cuota
    daily_request_limit INTEGER NOT NULL DEFAULT 1000,
    
    -- Estado actual del día
    current_date DATE NOT NULL DEFAULT CURRENT_DATE,
    requests_today INTEGER NOT NULL DEFAULT 0,
    is_blocked BOOLEAN NOT NULL DEFAULT false,
    blocked_at TIMESTAMP,
    
    -- Control administrativo
    administrative_safe BOOLEAN NOT NULL DEFAULT false,
    administrative_safe_set_by VARCHAR(255),
    administrative_safe_set_at TIMESTAMP,
    administrative_safe_reason TEXT,
    
    -- Auditoría
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_request_at TIMESTAMP
);

-- Índices
CREATE INDEX idx_quotas_user_id ON "bedrock-proxy-user-quotas-tbl"(cognito_user_id);
CREATE INDEX idx_quotas_blocked ON "bedrock-proxy-user-quotas-tbl"(is_blocked) WHERE is_blocked = true;
CREATE INDEX idx_quotas_date ON "bedrock-proxy-user-quotas-tbl"(current_date);
```

**Ventajas:**
- ✅ Separación de responsabilidades (cuotas vs. tracking)
- ✅ Consultas rápidas (tabla pequeña, solo usuarios activos)
- ✅ Fácil de mantener y escalar
- ✅ No afecta al rendimiento del tracking
- ✅ Permite configuración por usuario

**Desventajas:**
- ❌ Requiere sincronización entre tablas
- ❌ Una tabla adicional en el esquema

### Opción 2: Extensión de Tabla Existente

Añadir campos a `identity-manager-profiles-tbl` o crear tabla de configuración de usuario.

**Ventajas:**
- ✅ Menos tablas
- ✅ Datos centralizados

**Desventajas:**
- ❌ Mezcla conceptos diferentes (perfiles vs. cuotas)
- ❌ Más complejo de consultar
- ❌ Dificulta la escalabilidad

## 🔧 Implementación Detallada (Opción 1)

### 1. Estructura de Datos

#### Configuración Global en `identity-manager-config-tbl`

```sql
-- Insertar configuración de límite diario por defecto
INSERT INTO "identity-manager-config-tbl" (config_key, config_value, description)
VALUES 
    ('default_daily_request_limit', '1000', 'Límite de peticiones diarias por defecto para nuevos usuarios'),
    ('quota_warning_threshold_pct', '80', 'Porcentaje de uso para enviar advertencia (80%)'),
    ('enable_quota_notifications', 'true', 'Habilitar notificaciones de cuota');
```

#### Tabla Principal de Cuotas

```sql
-- Tabla principal de cuotas
CREATE TABLE "bedrock-proxy-user-quotas-tbl" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cognito_user_id VARCHAR(255) NOT NULL UNIQUE,
    cognito_email VARCHAR(255) NOT NULL,
    
    -- Límite diario (NULL = usar valor por defecto de config)
    daily_request_limit INTEGER,
    
    -- Estado del día actual
    current_date DATE NOT NULL DEFAULT CURRENT_DATE,
    requests_today INTEGER NOT NULL DEFAULT 0,
    is_blocked BOOLEAN NOT NULL DEFAULT false,
    blocked_at TIMESTAMP,
    
    -- Override administrativo
    administrative_safe BOOLEAN NOT NULL DEFAULT false,
    administrative_safe_set_by VARCHAR(255),
    administrative_safe_set_at TIMESTAMP,
    administrative_safe_reason TEXT,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_request_at TIMESTAMP
);

-- Tabla de historial de bloqueos (opcional, para auditoría)
CREATE TABLE "bedrock-proxy-quota-blocks-history-tbl" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cognito_user_id VARCHAR(255) NOT NULL,
    cognito_email VARCHAR(255) NOT NULL,
    block_date DATE NOT NULL,
    blocked_at TIMESTAMP NOT NULL,
    unblocked_at TIMESTAMP,
    unblock_type VARCHAR(20), -- 'automatic', 'administrative'
    requests_count INTEGER NOT NULL,
    daily_limit INTEGER NOT NULL,
    unblocked_by VARCHAR(255),
    unblock_reason TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### 2. Funciones de Control

```sql
-- Función: Verificar y actualizar cuota
CREATE OR REPLACE FUNCTION check_and_update_quota(
    p_cognito_user_id VARCHAR(255),
    p_cognito_email VARCHAR(255)
)
RETURNS TABLE (
    allowed BOOLEAN,
    requests_today INTEGER,
    daily_limit INTEGER,
    is_blocked BOOLEAN,
    block_reason TEXT
) AS $$
DECLARE
    v_quota RECORD;
    v_today DATE := CURRENT_DATE;
BEGIN
    -- Obtener o crear registro de cuota
    INSERT INTO "bedrock-proxy-user-quotas-tbl" (
        cognito_user_id, 
        cognito_email,
        current_date,
        requests_today
    )
    VALUES (p_cognito_user_id, p_cognito_email, v_today, 0)
    ON CONFLICT (cognito_user_id) DO NOTHING;
    
    -- Obtener estado actual
    SELECT * INTO v_quota
    FROM "bedrock-proxy-user-quotas-tbl"
    WHERE cognito_user_id = p_cognito_user_id
    FOR UPDATE;
    
    -- Obtener límite por defecto de configuración si el usuario no tiene uno específico
    IF v_quota.daily_request_limit IS NULL THEN
        SELECT config_value::INTEGER INTO v_quota.daily_request_limit
        FROM "identity-manager-config-tbl"
        WHERE config_key = 'default_daily_request_limit';
        
        -- Si no existe en config, usar 1000 como fallback
        IF v_quota.daily_request_limit IS NULL THEN
            v_quota.daily_request_limit := 1000;
        END IF;
    END IF;
    
    -- Reset si es un nuevo día (IMPORTANTE: También resetear administrative_safe)
    IF v_quota.current_date < v_today THEN
        UPDATE "bedrock-proxy-user-quotas-tbl"
        SET current_date = v_today,
            requests_today = 0,
            is_blocked = false,
            blocked_at = NULL,
            administrative_safe = false,  -- RESET FLAG ADMINISTRATIVO
            administrative_safe_set_by = NULL,
            administrative_safe_set_at = NULL,
            administrative_safe_reason = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE cognito_user_id = p_cognito_user_id;
        
        v_quota.current_date := v_today;
        v_quota.requests_today := 0;
        v_quota.is_blocked := false;
        v_quota.administrative_safe := false;
    END IF;
    
    -- Verificar si está bloqueado
    IF v_quota.is_blocked AND NOT v_quota.administrative_safe THEN
        RETURN QUERY SELECT 
            false,
            v_quota.requests_today,
            v_quota.daily_request_limit,
            true,
            'Daily quota exceeded. Will reset at midnight.'::TEXT;
        RETURN;
    END IF;
    
    -- Verificar si alcanzará el límite
    IF v_quota.requests_today >= v_quota.daily_request_limit AND NOT v_quota.administrative_safe THEN
        -- Bloquear usuario
        UPDATE "bedrock-proxy-user-quotas-tbl"
        SET is_blocked = true,
            blocked_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE cognito_user_id = p_cognito_user_id;
        
        -- Registrar en historial
        INSERT INTO "bedrock-proxy-quota-blocks-history-tbl" (
            cognito_user_id,
            cognito_email,
            block_date,
            blocked_at,
            requests_count,
            daily_limit
        ) VALUES (
            p_cognito_user_id,
            p_cognito_email,
            v_today,
            CURRENT_TIMESTAMP,
            v_quota.requests_today,
            v_quota.daily_request_limit
        );
        
        RETURN QUERY SELECT 
            false,
            v_quota.requests_today,
            v_quota.daily_request_limit,
            true,
            'Daily quota limit reached. User blocked until midnight.'::TEXT;
        RETURN;
    END IF;
    
    -- Incrementar contador
    UPDATE "bedrock-proxy-user-quotas-tbl"
    SET requests_today = requests_today + 1,
        last_request_at = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE cognito_user_id = p_cognito_user_id;
    
    -- Permitir petición
    RETURN QUERY SELECT 
        true,
        v_quota.requests_today + 1,
        v_quota.daily_request_limit,
        false,
        NULL::TEXT;
END;
$$ LANGUAGE plpgsql;

-- Función: Desbloqueo administrativo
CREATE OR REPLACE FUNCTION administrative_unblock_user(
    p_cognito_user_id VARCHAR(255),
    p_admin_user_id VARCHAR(255),
    p_reason TEXT DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    v_was_blocked BOOLEAN;
BEGIN
    -- Verificar si estaba bloqueado
    SELECT is_blocked INTO v_was_blocked
    FROM "bedrock-proxy-user-quotas-tbl"
    WHERE cognito_user_id = p_cognito_user_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'User not found';
    END IF;
    
    -- Activar safe mode administrativo
    UPDATE "bedrock-proxy-user-quotas-tbl"
    SET administrative_safe = true,
        administrative_safe_set_by = p_admin_user_id,
        administrative_safe_set_at = CURRENT_TIMESTAMP,
        administrative_safe_reason = p_reason,
        is_blocked = false,
        updated_at = CURRENT_TIMESTAMP
    WHERE cognito_user_id = p_cognito_user_id;
    
    -- Actualizar historial si estaba bloqueado
    IF v_was_blocked THEN
        UPDATE "bedrock-proxy-quota-blocks-history-tbl"
        SET unblocked_at = CURRENT_TIMESTAMP,
            unblock_type = 'administrative',
            unblocked_by = p_admin_user_id,
            unblock_reason = p_reason
        WHERE cognito_user_id = p_cognito_user_id
            AND block_date = CURRENT_DATE
            AND unblocked_at IS NULL;
    END IF;
    
    RETURN true;
END;
$$ LANGUAGE plpgsql;

-- Función: Actualizar límite diario de usuario
CREATE OR REPLACE FUNCTION update_user_daily_limit(
    p_cognito_user_id VARCHAR(255),
    p_new_limit INTEGER
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE "bedrock-proxy-user-quotas-tbl"
    SET daily_request_limit = p_new_limit,
        updated_at = CURRENT_TIMESTAMP
    WHERE cognito_user_id = p_cognito_user_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;
```

### 3. Vistas Útiles

```sql
-- Vista: Estado actual de cuotas
CREATE VIEW "v_quota_status" AS
SELECT 
    q.cognito_user_id,
    q.cognito_email,
    q.daily_request_limit,
    q.requests_today,
    q.daily_request_limit - q.requests_today as remaining_requests,
    ROUND(100.0 * q.requests_today / q.daily_request_limit, 2) as usage_percentage,
    q.is_blocked,
    q.blocked_at,
    q.administrative_safe,
    q.administrative_safe_set_by,
    q.administrative_safe_reason,
    q.last_request_at,
    q.current_date
FROM "bedrock-proxy-user-quotas-tbl" q;

-- Vista: Usuarios bloqueados
CREATE VIEW "v_blocked_users" AS
SELECT 
    q.cognito_user_id,
    q.cognito_email,
    q.requests_today,
    q.daily_request_limit,
    q.blocked_at,
    q.administrative_safe,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - q.blocked_at))/3600 as hours_blocked
FROM "bedrock-proxy-user-quotas-tbl" q
WHERE q.is_blocked = true;

-- Vista: Usuarios cerca del límite
CREATE VIEW "v_users_near_limit" AS
SELECT 
    q.cognito_user_id,
    q.cognito_email,
    q.requests_today,
    q.daily_request_limit,
    q.daily_request_limit - q.requests_today as remaining,
    ROUND(100.0 * q.requests_today / q.daily_request_limit, 2) as usage_pct
FROM "bedrock-proxy-user-quotas-tbl" q
WHERE q.requests_today >= (q.daily_request_limit * 0.8)
    AND q.is_blocked = false
    AND q.current_date = CURRENT_DATE
ORDER BY usage_pct DESC;
```

## 🔄 Flujo de Trabajo

### Flujo de Petición

```
1. Usuario hace petición al proxy
   ↓
2. Lambda llama a check_and_update_quota()
   ↓
3. Función verifica:
   - ¿Es un nuevo día? → Reset contador
   - ¿Está bloqueado? → Rechazar
   - ¿Tiene administrative_safe? → Permitir
   - ¿Alcanzó límite? → Bloquear y rechazar
   - ¿Dentro del límite? → Incrementar y permitir
   ↓
4. Si permitido: Procesar petición y registrar en usage-tracking
   Si bloqueado: Retornar error 429 (Too Many Requests)
```

### Flujo de Desbloqueo Administrativo

```
1. Admin accede al dashboard
   ↓
2. Ve lista de usuarios bloqueados
   ↓
3. Selecciona usuario y proporciona razón
   ↓
4. Sistema llama a administrative_unblock_user()
   ↓
5. Se activa flag administrative_safe
   ↓
6. Usuario puede hacer peticiones hasta medianoche
   ↓
7. A medianoche: Reset automático (administrative_safe = false)
```

## 💻 Integración en Lambda

```python
# services/quota_service.py

class QuotaService:
    def __init__(self, db_connection):
        self.db = db_connection
    
    def check_quota(self, cognito_user_id: str, cognito_email: str) -> dict:
        """
        Verifica y actualiza la cuota del usuario.
        Retorna: {
            'allowed': bool,
            'requests_today': int,
            'daily_limit': int,
            'is_blocked': bool,
            'block_reason': str
        }
        """
        query = """
            SELECT * FROM check_and_update_quota(%s, %s)
        """
        
        cursor = self.db.cursor()
        cursor.execute(query, (cognito_user_id, cognito_email))
        result = cursor.fetchone()
        
        return {
            'allowed': result[0],
            'requests_today': result[1],
            'daily_limit': result[2],
            'is_blocked': result[3],
            'block_reason': result[4]
        }
    
    def administrative_unblock(
        self, 
        cognito_user_id: str, 
        admin_user_id: str,
        reason: str = None
    ) -> bool:
        """Desbloquea un usuario administrativamente."""
        query = """
            SELECT administrative_unblock_user(%s, %s, %s)
        """
        
        cursor = self.db.cursor()
        cursor.execute(query, (cognito_user_id, admin_user_id, reason))
        return cursor.fetchone()[0]
    
    def update_daily_limit(self, cognito_user_id: str, new_limit: int) -> bool:
        """Actualiza el límite diario de un usuario."""
        query = """
            SELECT update_user_daily_limit(%s, %s)
        """
        
        cursor = self.db.cursor()
        cursor.execute(query, (cognito_user_id, new_limit))
        return cursor.fetchone()[0]

# lambda_function.py

def lambda_handler(event, context):
    # ... código existente ...
    
    # Verificar cuota ANTES de procesar la petición
    quota_service = QuotaService(db_connection)
    quota_check = quota_service.check_quota(
        cognito_user_id=user_id,
        cognito_email=user_email
    )
    
    if not quota_check['allowed']:
        return {
            'statusCode': 429,
            'body': json.dumps({
                'error': 'QuotaExceeded',
                'message': quota_check['block_reason'],
                'requests_today': quota_check['requests_today'],
                'daily_limit': quota_check['daily_limit']
            })
        }
    
    # Procesar petición normalmente...
    # ... código de proxy a Bedrock ...
    
    # Registrar en usage tracking
    # ...
```

## 📊 Dashboard de Administración

### Endpoints Necesarios

```python
# GET /admin/quotas/status
# Retorna estado de cuotas de todos los usuarios

# GET /admin/quotas/blocked
# Retorna lista de usuarios bloqueados

# POST /admin/quotas/unblock
# Body: { "user_id": "...", "reason": "..." }
# Desbloquea un usuario

# PUT /admin/quotas/limit
# Body: { "user_id": "...", "new_limit": 1000 }
# Actualiza límite diario de un usuario
```

## 🎯 Ventajas de Esta Propuesta

1. **Rendimiento**: Tabla pequeña y rápida, consultas optimizadas
2. **Escalabilidad**: Fácil de escalar horizontalmente
3. **Mantenibilidad**: Código limpio y separación de responsabilidades
4. **Auditoría**: Historial completo de bloqueos y desbloqueos
5. **Flexibilidad**: Límites configurables por usuario
6. **Seguridad**: Control administrativo con trazabilidad

## 📝 Consideraciones Adicionales

### 1. Límites por Defecto
- Usuarios nuevos: 1000 peticiones/día
- Usuarios premium: Configurable (ej: 10000/día)
- Administradores: Sin límite (o límite muy alto)

### 2. Notificaciones
- Email al usuario al 80% del límite
- Email al usuario al bloqueo
- Notificación a admins de bloqueos frecuentes

### 3. Métricas
- Dashboard con gráficos de uso
- Alertas de usuarios que alcanzan límites frecuentemente
- Análisis de patrones de uso

### 4. Configuración Global

Se utiliza la tabla existente `identity-manager-config-tbl` para almacenar la configuración:

```sql
-- Configuración de cuotas en identity-manager-config-tbl
INSERT INTO "identity-manager-config-tbl" (config_key, config_value, description, is_sensitive)
VALUES 
    ('default_daily_request_limit', '1000', 'Límite de peticiones diarias por defecto para nuevos usuarios', false),
    ('quota_warning_threshold_pct', '80', 'Porcentaje de uso para enviar advertencia', false),
    ('enable_quota_notifications', 'true', 'Habilitar notificaciones de cuota', false),
    ('quota_admin_override_enabled', 'true', 'Permitir desbloqueo administrativo', false);
```

**Ventajas de usar `identity-manager-config-tbl`:**
- ✅ Centralización de toda la configuración del sistema
- ✅ No requiere tabla adicional
- ✅ Fácil de modificar sin cambios en esquema
- ✅ Consistente con el diseño existente

## 🚀 Plan de Implementación

1. **Fase 1**: Crear tablas y funciones
2. **Fase 2**: Integrar en Lambda (verificación de cuota)
3. **Fase 3**: Crear endpoints de administración
4. **Fase 4**: Desarrollar dashboard de administración
5. **Fase 5**: Implementar notificaciones
6. **Fase 6**: Testing y ajustes
7. **Fase 7**: Despliegue gradual (feature flag)

## ❓ Preguntas para Decisión

1. ¿Límite por defecto para usuarios nuevos?
2. ¿Diferentes límites por tipo de usuario/grupo?
3. ¿Notificaciones automáticas?
4. ¿Límites por modelo además de límite global?
5. ¿Límites por costo además de por número de peticiones?