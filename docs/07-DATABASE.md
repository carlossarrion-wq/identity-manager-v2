# Base de Datos

## 📋 Visión General

Identity Manager v2 utiliza PostgreSQL 15+ en AWS RDS con un esquema basado en UUIDs para mejor seguridad y escalabilidad.

## 🗄️ Nomenclatura

### Base de Datos
**Formato:** `<aplicacion>_<entorno>_rds`

Ejemplos:
- `identity_manager_dev_rds`
- `identity_manager_pre_rds`
- `identity_manager_pro_rds`

### Tablas
**Formato:** `identity-manager-<función>-tbl`

Ejemplos:
- `identity-manager-models-tbl`
- `identity-manager-tokens-tbl`
- `identity-manager-app-permissions-tbl`

## 📊 Esquema Completo (Extraído de BD)

> **Nota:** Esquema extraído el 2026-03-05 desde `identity_manager_dev_rds`

### 🗂️ Tablas Identity Manager (10 tablas)

#### 1. identity-manager-models-tbl
Catálogo de modelos LLM disponibles en AWS Bedrock.

```sql
CREATE TABLE "identity-manager-models-tbl" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id VARCHAR(255) NOT NULL UNIQUE,
    model_name VARCHAR(255) NOT NULL,
    model_arn VARCHAR(500),
    provider VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

#### 2. identity-manager-applications-tbl
Aplicaciones disponibles en el sistema.

```sql
CREATE TABLE "identity-manager-applications-tbl" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

#### 3. identity-manager-modules-tbl
Módulos específicos de cada aplicación.

```sql
CREATE TABLE "identity-manager-modules-tbl" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_modules_application 
        FOREIGN KEY (application_id) 
        REFERENCES "identity-manager-applications-tbl"(id) 
        ON DELETE CASCADE,
    CONSTRAINT uk_application_module_name 
        UNIQUE (application_id, name)
);
```

#### 4. identity-manager-profiles-tbl
Perfiles que asocian grupo Cognito + aplicación + modelo LLM.

```sql
CREATE TABLE "identity-manager-profiles-tbl" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_name VARCHAR(100) NOT NULL,
    cognito_group_name VARCHAR(100) NOT NULL,
    application_id UUID,
    model_id UUID NOT NULL,
    model_arn TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_profiles_application 
        FOREIGN KEY (application_id) 
        REFERENCES "identity-manager-applications-tbl"(id) 
        ON DELETE SET NULL,
    CONSTRAINT fk_profiles_model 
        FOREIGN KEY (model_id) 
        REFERENCES "identity-manager-models-tbl"(id) 
        ON DELETE RESTRICT,
    CONSTRAINT uk_profile_group_app_model 
        UNIQUE (cognito_group_name, application_id, model_id)
);
```

#### 5. identity-manager-tokens-tbl
Tokens JWT emitidos a usuarios para acceso al proxy.

```sql
CREATE TABLE "identity-manager-tokens-tbl" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cognito_user_id VARCHAR(255) NOT NULL,
    cognito_email VARCHAR(255) NOT NULL,
    jti VARCHAR(255) NOT NULL UNIQUE,
    token_hash TEXT NOT NULL UNIQUE,
    application_profile_id UUID NOT NULL,
    issued_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    last_used_at TIMESTAMP,
    is_revoked BOOLEAN NOT NULL DEFAULT false,
    revoked_at TIMESTAMP,
    revocation_reason TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- Campos de regeneración de tokens
    regenerated_at TIMESTAMP,
    regenerated_to_jti UUID,
    regenerated_from_jti UUID,
    regeneration_reason VARCHAR(100),
    regeneration_client_ip VARCHAR(45),
    regeneration_user_agent TEXT,
    regeneration_email_sent BOOLEAN DEFAULT false,
    CONSTRAINT fk_tokens_profile 
        FOREIGN KEY (application_profile_id) 
        REFERENCES "identity-manager-profiles-tbl"(id) 
        ON DELETE RESTRICT
);
```

#### 6. identity-manager-permission-types-tbl
Catálogo de tipos de permisos (Read-only, Write, Admin).

```sql
CREATE TABLE "identity-manager-permission-types-tbl" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    level INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

#### 7. identity-manager-app-permissions-tbl
Permisos de usuarios sobre aplicaciones completas.

```sql
CREATE TABLE "identity-manager-app-permissions-tbl" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cognito_user_id VARCHAR(255) NOT NULL,
    cognito_email VARCHAR(255) NOT NULL,
    application_id UUID NOT NULL,
    permission_type_id UUID NOT NULL,
    granted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT true,
    CONSTRAINT fk_app_perms_application 
        FOREIGN KEY (application_id) 
        REFERENCES "identity-manager-applications-tbl"(id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_app_perms_type 
        FOREIGN KEY (permission_type_id) 
        REFERENCES "identity-manager-permission-types-tbl"(id) 
        ON DELETE RESTRICT,
    CONSTRAINT uk_user_application_permission 
        UNIQUE (cognito_user_id, application_id)
);
```

#### 8. identity-manager-module-permissions-tbl
Permisos de usuarios sobre módulos específicos.

```sql
CREATE TABLE "identity-manager-module-permissions-tbl" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cognito_user_id VARCHAR(255) NOT NULL,
    cognito_email VARCHAR(255) NOT NULL,
    application_module_id UUID NOT NULL,
    permission_type_id UUID NOT NULL,
    granted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT true,
    CONSTRAINT fk_mod_perms_module 
        FOREIGN KEY (application_module_id) 
        REFERENCES "identity-manager-modules-tbl"(id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_mod_perms_type 
        FOREIGN KEY (permission_type_id) 
        REFERENCES "identity-manager-permission-types-tbl"(id) 
        ON DELETE RESTRICT,
    CONSTRAINT uk_user_module_permission 
        UNIQUE (cognito_user_id, application_module_id)
);
```

#### 9. identity-manager-config-tbl
Parámetros de configuración de la aplicación.

```sql
CREATE TABLE "identity-manager-config-tbl" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value TEXT NOT NULL,
    description TEXT,
    is_sensitive BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

#### 10. identity-manager-audit-tbl
Registro de auditoría de todas las operaciones del sistema.

```sql
CREATE TABLE "identity-manager-audit-tbl" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cognito_user_id VARCHAR(255),
    cognito_email VARCHAR(255),
    performed_by_cognito_user_id VARCHAR(255),
    performed_by_email VARCHAR(255),
    operation_type VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    previous_value JSONB,
    new_value JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    operation_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### 🔄 Tablas Proxy Bedrock (3 tablas)

#### 1. bedrock-proxy-usage-tracking-tbl
Registro de uso de API y modelos Bedrock con métricas de costos.

```sql
CREATE TABLE "bedrock-proxy-usage-tracking-tbl" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cognito_user_id VARCHAR(255) NOT NULL,
    cognito_email VARCHAR(255) NOT NULL,
    request_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    model_id VARCHAR(255) NOT NULL,
    source_ip VARCHAR(45),
    user_agent TEXT,
    aws_region VARCHAR(50),
    tokens_input INTEGER,
    tokens_output INTEGER,
    tokens_cache_read INTEGER DEFAULT 0,
    tokens_cache_creation INTEGER DEFAULT 0,
    cost_usd NUMERIC(10,6),
    processing_time_ms INTEGER,
    response_status VARCHAR(20) NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    team VARCHAR(100),
    person VARCHAR(255)
);
```

#### 2. bedrock-proxy-user-quotas-tbl
Control de cuotas diarias por usuario con bloqueo automático y manual.

```sql
CREATE TABLE "bedrock-proxy-user-quotas-tbl" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cognito_user_id VARCHAR(255) NOT NULL UNIQUE,
    cognito_email VARCHAR(255) NOT NULL,
    daily_request_limit INTEGER,
    quota_date DATE NOT NULL DEFAULT CURRENT_DATE,
    requests_today INTEGER NOT NULL DEFAULT 0,
    is_blocked BOOLEAN NOT NULL DEFAULT false,
    blocked_at TIMESTAMP,
    blocked_until TIMESTAMP,
    blocked_by VARCHAR(255),                    -- Email del admin que bloqueó
    block_reason TEXT,                          -- Razón del bloqueo manual
    unblocked_at TIMESTAMP,                     -- Timestamp del último desbloqueo
    unblocked_by VARCHAR(255),                  -- Email del admin que desbloqueó
    unblock_reason TEXT,                        -- Razón del desbloqueo
    administrative_safe BOOLEAN NOT NULL DEFAULT false,
    administrative_safe_set_by VARCHAR(255),
    administrative_safe_set_at TIMESTAMP,
    administrative_safe_reason TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_request_at TIMESTAMP,
    team VARCHAR(100),
    person VARCHAR(255)
);
```

**Campos de Gestión Manual (Migración 012 - 2026-03-05):**
- `blocked_by`: Email del administrador que realizó el bloqueo manual
- `block_reason`: Razón detallada del bloqueo manual
- `unblocked_at`: Timestamp del último desbloqueo manual
- `unblocked_by`: Email del administrador que realizó el desbloqueo
- `unblock_reason`: Razón del desbloqueo manual

#### 3. bedrock-proxy-quota-blocks-history-tbl
Historial de bloqueos y desbloqueos de usuarios por cuota.

```sql
CREATE TABLE "bedrock-proxy-quota-blocks-history-tbl" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cognito_user_id VARCHAR(255) NOT NULL,
    cognito_email VARCHAR(255) NOT NULL,
    block_date DATE NOT NULL,
    blocked_at TIMESTAMP NOT NULL,
    unblocked_at TIMESTAMP,
    unblock_type VARCHAR(20),
    requests_count INTEGER NOT NULL,
    daily_limit INTEGER NOT NULL,
    unblocked_by VARCHAR(255),
    unblock_reason TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    team VARCHAR(100),
    person VARCHAR(255)
);
```

## 🔍 Vistas (13 vistas)

### v_active_tokens
Tokens activos con información del perfil.

```sql
CREATE VIEW v_active_tokens AS
SELECT 
    t.id as token_id,
    t.jti,
    t.cognito_user_id,
    t.cognito_email,
    t.issued_at,
    t.expires_at,
    t.last_used_at,
    ap.profile_name,
    ap.cognito_group_name,
    a.name as application_name,
    m.model_name,
    m.model_id,
    ap.model_arn
FROM "identity-manager-tokens-tbl" t
JOIN "identity-manager-profiles-tbl" ap ON t.application_profile_id = ap.id
LEFT JOIN "identity-manager-applications-tbl" a ON ap.application_id = a.id
JOIN "identity-manager-models-tbl" m ON ap.model_id = m.id
WHERE t.is_revoked = false 
  AND t.expires_at > CURRENT_TIMESTAMP;
```

### v_user_permissions
Permisos consolidados de usuarios (aplicaciones + módulos).

```sql
CREATE VIEW v_user_permissions AS
SELECT 
    uap.cognito_user_id,
    uap.cognito_email,
    'application' as permission_scope,
    a.name as resource_name,
    a.id as resource_id,
    NULL::UUID as parent_application_id,
    pt.name as permission_type,
    pt.level as permission_level,
    uap.is_active,
    uap.granted_at,
    uap.expires_at
FROM "identity-manager-app-permissions-tbl" uap
JOIN "identity-manager-applications-tbl" a ON uap.application_id = a.id
JOIN "identity-manager-permission-types-tbl" pt ON uap.permission_type_id = pt.id

UNION ALL

SELECT 
    ump.cognito_user_id,
    ump.cognito_email,
    'module' as permission_scope,
    am.name as resource_name,
    am.id as resource_id,
    am.application_id as parent_application_id,
    pt.name as permission_type,
    pt.level as permission_level,
    ump.is_active,
    ump.granted_at,
    ump.expires_at
FROM "identity-manager-module-permissions-tbl" ump
JOIN "identity-manager-modules-tbl" am ON ump.application_module_id = am.id
JOIN "identity-manager-permission-types-tbl" pt ON ump.permission_type_id = pt.id;
```

### v_application_profiles
Perfiles con información completa de aplicación y modelo.

### v_usage_by_model
Estadísticas agregadas de uso por modelo.

### v_usage_by_team
Estadísticas agregadas de uso por equipo.

### v_usage_by_person
Estadísticas agregadas de uso por persona.

### v_usage_detailed
Vista detallada de todos los registros de uso.

### v_recent_errors
Últimos 100 errores registrados.

### v_users_near_limit
Usuarios que han usado >80% de su cuota diaria.

### v_blocked_users
Lista de usuarios actualmente bloqueados.

### v_quota_status
Estado consolidado de cuotas de todos los usuarios.

### v_usage_daily
Resumen agregado de uso por día.

### v_top_users_by_cost
Top usuarios ordenados por costo total.

## ⚙️ Funciones PL/pgSQL (9 funciones)

### check_and_update_quota()
Verifica y actualiza la cuota de un usuario. Incluye lógica de bloqueo automático.

```sql
CREATE FUNCTION check_and_update_quota(
    p_cognito_user_id VARCHAR(255),
    p_cognito_email VARCHAR(255),
    p_team VARCHAR(100) DEFAULT NULL,
    p_person VARCHAR(255) DEFAULT NULL
)
RETURNS TABLE (
    allowed BOOLEAN,
    requests_today INTEGER,
    daily_limit INTEGER,
    is_blocked BOOLEAN,
    block_reason TEXT
);
```

### administrative_block_user()
Bloquea un usuario administrativamente hasta una fecha específica.

```sql
CREATE FUNCTION administrative_block_user(
    p_cognito_user_id VARCHAR(255),
    p_admin_user_id VARCHAR(255),
    p_block_until TIMESTAMP,
    p_reason TEXT DEFAULT NULL
) RETURNS BOOLEAN;
```

### administrative_unblock_user()
Desbloquea un usuario administrativamente (activa safe mode).

```sql
CREATE FUNCTION administrative_unblock_user(
    p_cognito_user_id VARCHAR(255),
    p_admin_user_id VARCHAR(255),
    p_reason TEXT DEFAULT NULL
) RETURNS BOOLEAN;
```

### update_user_daily_limit()
Actualiza el límite diario de peticiones de un usuario.

```sql
CREATE FUNCTION update_user_daily_limit(
    p_cognito_user_id VARCHAR(255),
    p_new_limit INTEGER
) RETURNS BOOLEAN;
```

### get_user_quota_status()
Obtiene el estado actual de cuota de un usuario.

```sql
CREATE FUNCTION get_user_quota_status(
    p_cognito_user_id VARCHAR(255)
)
RETURNS TABLE (
    cognito_user_id VARCHAR(255),
    cognito_email VARCHAR(255),
    daily_limit INTEGER,
    requests_today INTEGER,
    remaining_requests INTEGER,
    usage_percentage NUMERIC,
    is_blocked BOOLEAN,
    blocked_at TIMESTAMP,
    administrative_safe BOOLEAN,
    last_request_at TIMESTAMP
);
```

### get_usage_stats()
Obtiene estadísticas de uso para un período específico.

```sql
CREATE FUNCTION get_usage_stats(
    p_start_date TIMESTAMP,
    p_end_date TIMESTAMP,
    p_user_id VARCHAR(255) DEFAULT NULL
)
RETURNS TABLE (
    total_requests BIGINT,
    successful_requests BIGINT,
    failed_requests BIGINT,
    total_tokens_input BIGINT,
    total_tokens_output BIGINT,
    total_cost_usd NUMERIC,
    avg_processing_time_ms NUMERIC,
    unique_users BIGINT
);
```

### calculate_usage_cost()
Calcula el costo estimado basado en tokens y proveedor.

```sql
CREATE FUNCTION calculate_usage_cost(
    p_tokens_input INTEGER,
    p_tokens_output INTEGER,
    p_model_provider VARCHAR
) RETURNS NUMERIC;
```

### archive_old_usage_data()
Archiva o elimina datos de uso antiguos.

```sql
CREATE FUNCTION archive_old_usage_data(
    p_days_to_keep INTEGER DEFAULT 365
) RETURNS INTEGER;
```

### update_updated_at_column()
Trigger function para actualizar automáticamente `updated_at`.

## 📈 Índices

### Índices en Tokens
- `idx_tokens_cognito_user`: Por usuario
- `idx_tokens_jti`: Por JTI
- `idx_tokens_expires`: Por fecha de expiración
- `idx_tokens_active`: Por estado activo

### Índices en Permisos
- `idx_app_perms_user`: Por usuario en app permissions
- `idx_mod_perms_user`: Por usuario en module permissions

### Índices en Auditoría
- `idx_audit_user`: Por usuario
- `idx_audit_timestamp`: Por fecha/hora
- `idx_audit_resource`: Por tipo y ID de recurso

### Índices en Usage Tracking
- `idx_usage_user`: Por usuario
- `idx_usage_timestamp`: Por fecha/hora
- `idx_usage_team`: Por equipo

## 🔄 Triggers

### update_updated_at_column()
Actualiza automáticamente el campo `updated_at` en:
- identity-manager-models-tbl
- identity-manager-applications-tbl
- identity-manager-modules-tbl
- identity-manager-profiles-tbl
- identity-manager-config-tbl

## 🔐 Seguridad

### Encriptación
- RDS con encriptación en reposo
- SSL/TLS para conexiones
- Secrets Manager para credenciales

### Acceso
- Connection pooling (min: 5, max: 25)
- Credenciales rotadas periódicamente
- Acceso solo desde VPC

## 📊 Mantenimiento

### Backups
- Backups automáticos diarios
- Retención: 7-30 días según ambiente
- Point-in-time recovery habilitado

### Monitoreo
- CloudWatch métricas de RDS
- Alertas de CPU, memoria, conexiones
- Logs de queries lentas

### Limpieza
- Archivar tokens expirados > 90 días
- Archivar auditoría > 1 año
- Archivar usage tracking > 6 meses

## 🔗 Referencias

- [Arquitectura del Sistema](./02-ARCHITECTURE.md)
- [Guía de Instalación](./03-INSTALLATION.md)
- [Sistema de Permisos](./05-PERMISSIONS.md)
