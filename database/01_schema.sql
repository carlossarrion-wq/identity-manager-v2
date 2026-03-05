-- ============================================================================
-- IDENTITY MANAGER V2 - SCHEMA DDL
-- ============================================================================
-- Version: 5.0
-- Date: 2026-03-05
-- Description: Esquema completo consolidado con todas las tablas, vistas,
--              funciones, índices y triggers
-- 
-- Uso: psql -h <host> -U <user> -d <database> -f 01_schema.sql
-- ============================================================================

-- ============================================================================
-- EXTENSIONES
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- TABLAS IDENTITY MANAGER
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. MODELS - Catálogo de modelos LLM
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "identity-manager-models-tbl" (
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

COMMENT ON TABLE "identity-manager-models-tbl" IS 'Catálogo de modelos LLM disponibles en AWS Bedrock';
COMMENT ON COLUMN "identity-manager-models-tbl".id IS 'UUID único del modelo';
COMMENT ON COLUMN "identity-manager-models-tbl".model_id IS 'Identificador del modelo en Bedrock';

-- ----------------------------------------------------------------------------
-- 2. APPLICATIONS - Aplicaciones del sistema
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "identity-manager-applications-tbl" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE "identity-manager-applications-tbl" IS 'Aplicaciones disponibles en el sistema';
COMMENT ON COLUMN "identity-manager-applications-tbl".id IS 'UUID único de la aplicación';

-- ----------------------------------------------------------------------------
-- 3. MODULES - Módulos de aplicaciones
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "identity-manager-modules-tbl" (
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

COMMENT ON TABLE "identity-manager-modules-tbl" IS 'Módulos específicos de cada aplicación';
COMMENT ON COLUMN "identity-manager-modules-tbl".id IS 'UUID único del módulo';

-- ----------------------------------------------------------------------------
-- 4. PROFILES - Perfiles de inferencia
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "identity-manager-profiles-tbl" (
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

COMMENT ON TABLE "identity-manager-profiles-tbl" IS 'Perfiles que asocian grupo Cognito + aplicación + modelo LLM';
COMMENT ON COLUMN "identity-manager-profiles-tbl".id IS 'UUID único del perfil';
COMMENT ON COLUMN "identity-manager-profiles-tbl".cognito_group_name IS 'Nombre del grupo en Cognito';

-- ----------------------------------------------------------------------------
-- 5. TOKENS - Tokens JWT emitidos
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "identity-manager-tokens-tbl" (
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

COMMENT ON TABLE "identity-manager-tokens-tbl" IS 'Tokens JWT emitidos a usuarios para acceso al proxy';
COMMENT ON COLUMN "identity-manager-tokens-tbl".id IS 'UUID único del token';
COMMENT ON COLUMN "identity-manager-tokens-tbl".jti IS 'JWT ID único del token';
COMMENT ON COLUMN "identity-manager-tokens-tbl".regenerated_at IS 'Timestamp cuando este token fue regenerado';
COMMENT ON COLUMN "identity-manager-tokens-tbl".regenerated_to_jti IS 'JTI del nuevo token que reemplazó a este';
COMMENT ON COLUMN "identity-manager-tokens-tbl".regenerated_from_jti IS 'JTI del token antiguo que este reemplazó';

-- ----------------------------------------------------------------------------
-- 6. PERMISSION TYPES - Tipos de permisos
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "identity-manager-permission-types-tbl" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    level INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE "identity-manager-permission-types-tbl" IS 'Catálogo de tipos de permisos';
COMMENT ON COLUMN "identity-manager-permission-types-tbl".id IS 'UUID único del tipo de permiso';
COMMENT ON COLUMN "identity-manager-permission-types-tbl".level IS 'Nivel jerárquico (10=read, 50=write, 100=admin)';

-- ----------------------------------------------------------------------------
-- 7. APP PERMISSIONS - Permisos sobre aplicaciones
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "identity-manager-app-permissions-tbl" (
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

COMMENT ON TABLE "identity-manager-app-permissions-tbl" IS 'Permisos de usuarios sobre aplicaciones completas';
COMMENT ON COLUMN "identity-manager-app-permissions-tbl".id IS 'UUID único del permiso';

-- ----------------------------------------------------------------------------
-- 8. MODULE PERMISSIONS - Permisos sobre módulos
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "identity-manager-module-permissions-tbl" (
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

COMMENT ON TABLE "identity-manager-module-permissions-tbl" IS 'Permisos de usuarios sobre módulos específicos';
COMMENT ON COLUMN "identity-manager-module-permissions-tbl".id IS 'UUID único del permiso';

-- ----------------------------------------------------------------------------
-- 9. CONFIG - Configuración del sistema
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "identity-manager-config-tbl" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value TEXT NOT NULL,
    description TEXT,
    is_sensitive BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE "identity-manager-config-tbl" IS 'Parámetros de configuración de la aplicación';
COMMENT ON COLUMN "identity-manager-config-tbl".id IS 'UUID único de la configuración';

-- ----------------------------------------------------------------------------
-- 10. AUDIT - Registro de auditoría
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "identity-manager-audit-tbl" (
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

COMMENT ON TABLE "identity-manager-audit-tbl" IS 'Registro de auditoría de todas las operaciones';
COMMENT ON COLUMN "identity-manager-audit-tbl".id IS 'UUID único del registro';
COMMENT ON COLUMN "identity-manager-audit-tbl".resource_id IS 'UUID del recurso afectado';

-- ============================================================================
-- TABLAS PROXY BEDROCK
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 11. USAGE TRACKING - Registro de uso del proxy
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "bedrock-proxy-usage-tracking-tbl" (
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

COMMENT ON TABLE "bedrock-proxy-usage-tracking-tbl" IS 'Registro de uso de API Bedrock con métricas';
COMMENT ON COLUMN "bedrock-proxy-usage-tracking-tbl".model_id IS 'ID del modelo o ARN de inference profile';
COMMENT ON COLUMN "bedrock-proxy-usage-tracking-tbl".team IS 'Equipo del usuario (del JWT)';
COMMENT ON COLUMN "bedrock-proxy-usage-tracking-tbl".person IS 'Nombre completo del usuario (del JWT)';

-- ----------------------------------------------------------------------------
-- 12. USER QUOTAS - Control de cuotas por usuario
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "bedrock-proxy-user-quotas-tbl" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cognito_user_id VARCHAR(255) NOT NULL UNIQUE,
    cognito_email VARCHAR(255) NOT NULL,
    daily_request_limit INTEGER,
    quota_date DATE NOT NULL DEFAULT CURRENT_DATE,
    requests_today INTEGER NOT NULL DEFAULT 0,
    is_blocked BOOLEAN NOT NULL DEFAULT false,
    blocked_at TIMESTAMP,
    blocked_until TIMESTAMP,
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

COMMENT ON TABLE "bedrock-proxy-user-quotas-tbl" IS 'Control de cuotas diarias con bloqueo automático';
COMMENT ON COLUMN "bedrock-proxy-user-quotas-tbl".daily_request_limit IS 'Límite específico del usuario (NULL = usar default)';
COMMENT ON COLUMN "bedrock-proxy-user-quotas-tbl".blocked_until IS 'Fecha/hora hasta la cual está bloqueado';
COMMENT ON COLUMN "bedrock-proxy-user-quotas-tbl".administrative_safe IS 'Flag que permite continuar hasta medianoche';

-- ----------------------------------------------------------------------------
-- 13. QUOTA BLOCKS HISTORY - Historial de bloqueos
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "bedrock-proxy-quota-blocks-history-tbl" (
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

COMMENT ON TABLE "bedrock-proxy-quota-blocks-history-tbl" IS 'Historial de bloqueos y desbloqueos';

-- ============================================================================
-- ÍNDICES
-- ============================================================================

-- Índices en tokens
CREATE INDEX IF NOT EXISTS idx_tokens_cognito_user ON "identity-manager-tokens-tbl"(cognito_user_id);
CREATE INDEX IF NOT EXISTS idx_tokens_jti ON "identity-manager-tokens-tbl"(jti);
CREATE INDEX IF NOT EXISTS idx_tokens_expires ON "identity-manager-tokens-tbl"(expires_at);
CREATE INDEX IF NOT EXISTS idx_tokens_active ON "identity-manager-tokens-tbl"(is_revoked, expires_at);
CREATE INDEX IF NOT EXISTS idx_tokens_regenerated ON "identity-manager-tokens-tbl"(regenerated_at) WHERE regenerated_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tokens_regenerated_from ON "identity-manager-tokens-tbl"(regenerated_from_jti) WHERE regenerated_from_jti IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tokens_regenerated_to ON "identity-manager-tokens-tbl"(regenerated_to_jti) WHERE regenerated_to_jti IS NOT NULL;

-- Índices en permisos
CREATE INDEX IF NOT EXISTS idx_app_perms_user ON "identity-manager-app-permissions-tbl"(cognito_user_id);
CREATE INDEX IF NOT EXISTS idx_mod_perms_user ON "identity-manager-module-permissions-tbl"(cognito_user_id);

-- Índices en auditoría
CREATE INDEX IF NOT EXISTS idx_audit_user ON "identity-manager-audit-tbl"(cognito_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_performed_by ON "identity-manager-audit-tbl"(performed_by_cognito_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON "identity-manager-audit-tbl"(operation_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON "identity-manager-audit-tbl"(resource_type, resource_id);

-- Índices en usage tracking
CREATE INDEX IF NOT EXISTS idx_usage_cognito_user ON "bedrock-proxy-usage-tracking-tbl"(cognito_user_id);
CREATE INDEX IF NOT EXISTS idx_usage_cognito_email ON "bedrock-proxy-usage-tracking-tbl"(cognito_email);
CREATE INDEX IF NOT EXISTS idx_usage_request_timestamp ON "bedrock-proxy-usage-tracking-tbl"(request_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_usage_model ON "bedrock-proxy-usage-tracking-tbl"(model_id);
CREATE INDEX IF NOT EXISTS idx_usage_response_status ON "bedrock-proxy-usage-tracking-tbl"(response_status);
CREATE INDEX IF NOT EXISTS idx_usage_user_timestamp ON "bedrock-proxy-usage-tracking-tbl"(cognito_user_id, request_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_usage_model_timestamp ON "bedrock-proxy-usage-tracking-tbl"(model_id, request_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_usage_errors ON "bedrock-proxy-usage-tracking-tbl"(response_status, request_timestamp DESC) WHERE response_status != 'success';
CREATE INDEX IF NOT EXISTS idx_usage_team ON "bedrock-proxy-usage-tracking-tbl"(team);
CREATE INDEX IF NOT EXISTS idx_usage_person ON "bedrock-proxy-usage-tracking-tbl"(person);

-- Índices en quotas
CREATE INDEX IF NOT EXISTS idx_quotas_user_id ON "bedrock-proxy-user-quotas-tbl"(cognito_user_id);
CREATE INDEX IF NOT EXISTS idx_quotas_blocked ON "bedrock-proxy-user-quotas-tbl"(is_blocked) WHERE is_blocked = true;
CREATE INDEX IF NOT EXISTS idx_quotas_date ON "bedrock-proxy-user-quotas-tbl"(quota_date);
CREATE INDEX IF NOT EXISTS idx_quotas_team ON "bedrock-proxy-user-quotas-tbl"(team);
CREATE INDEX IF NOT EXISTS idx_quotas_person ON "bedrock-proxy-user-quotas-tbl"(person);
CREATE INDEX IF NOT EXISTS idx_quotas_admin_safe ON "bedrock-proxy-user-quotas-tbl"(administrative_safe) WHERE administrative_safe = true;

-- Índices en quota history
CREATE INDEX IF NOT EXISTS idx_quota_history_user ON "bedrock-proxy-quota-blocks-history-tbl"(cognito_user_id);
CREATE INDEX IF NOT EXISTS idx_quota_history_date ON "bedrock-proxy-quota-blocks-history-tbl"(block_date DESC);
CREATE INDEX IF NOT EXISTS idx_quota_history_team ON "bedrock-proxy-quota-blocks-history-tbl"(team);
CREATE INDEX IF NOT EXISTS idx_quota_history_person ON "bedrock-proxy-quota-blocks-history-tbl"(person);
CREATE INDEX IF NOT EXISTS idx_quota_history_unblocked ON "bedrock-proxy-quota-blocks-history-tbl"(unblocked_at) WHERE unblocked_at IS NULL;

-- ============================================================================
-- FIN DEL ESQUEMA
-- ============================================================================