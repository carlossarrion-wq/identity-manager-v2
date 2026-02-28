-- =====================================================
-- IDENTITY MANAGER DATABASE SCHEMA - UUID VERSION
-- =====================================================
-- Purpose: Gestión de permisos y tokens JWT para usuarios de Cognito
-- Version: 5.0 - UUID Edition
-- Date: 2026-02-27
-- 
-- CAMBIOS: Todos los IDs ahora son UUIDs para mejor seguridad y escalabilidad
-- =====================================================

-- Habilitar extensión para UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =====================================================
-- TABLA: identity-manager-models-tbl
-- Descripción: Modelos LLM disponibles en Bedrock
-- =====================================================
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

COMMENT ON TABLE "identity-manager-models-tbl" IS 'Catálogo de modelos LLM disponibles en AWS Bedrock';
COMMENT ON COLUMN "identity-manager-models-tbl".id IS 'UUID único del modelo';
COMMENT ON COLUMN "identity-manager-models-tbl".model_id IS 'Identificador del modelo en Bedrock (ej: anthropic.claude-3-5-sonnet-20241022-v2:0)';

-- =====================================================
-- TABLA: identity-manager-applications-tbl
-- Descripción: Aplicaciones del sistema
-- =====================================================
CREATE TABLE "identity-manager-applications-tbl" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE "identity-manager-applications-tbl" IS 'Aplicaciones disponibles en el sistema (ej: cline, kb-agent)';
COMMENT ON COLUMN "identity-manager-applications-tbl".id IS 'UUID único de la aplicación';

-- =====================================================
-- TABLA: identity-manager-modules-tbl
-- Descripción: Módulos de las aplicaciones
-- =====================================================
CREATE TABLE "identity-manager-modules-tbl" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_modules_application FOREIGN KEY (application_id) REFERENCES "identity-manager-applications-tbl"(id) ON DELETE CASCADE,
    CONSTRAINT uk_application_module_name UNIQUE (application_id, name)
);

COMMENT ON TABLE "identity-manager-modules-tbl" IS 'Módulos específicos de cada aplicación';
COMMENT ON COLUMN "identity-manager-modules-tbl".id IS 'UUID único del módulo';

-- =====================================================
-- TABLA: identity-manager-profiles-tbl
-- Descripción: Perfiles de aplicación (modelo + grupo + aplicación)
-- =====================================================
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
    CONSTRAINT fk_profiles_application FOREIGN KEY (application_id) REFERENCES "identity-manager-applications-tbl"(id) ON DELETE SET NULL,
    CONSTRAINT fk_profiles_model FOREIGN KEY (model_id) REFERENCES "identity-manager-models-tbl"(id) ON DELETE RESTRICT,
    CONSTRAINT uk_profile_group_app_model UNIQUE (cognito_group_name, application_id, model_id)
);

COMMENT ON TABLE "identity-manager-profiles-tbl" IS 'Perfiles que asocian un grupo de Cognito, aplicación y modelo LLM';
COMMENT ON COLUMN "identity-manager-profiles-tbl".id IS 'UUID único del perfil';
COMMENT ON COLUMN "identity-manager-profiles-tbl".cognito_group_name IS 'Nombre del grupo en Cognito (ej: tcs-bi-dwh-group)';

-- =====================================================
-- TABLA: identity-manager-tokens-tbl
-- Descripción: Tokens JWT emitidos a usuarios
-- =====================================================
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
    CONSTRAINT fk_tokens_profile FOREIGN KEY (application_profile_id) REFERENCES "identity-manager-profiles-tbl"(id) ON DELETE RESTRICT
);

COMMENT ON TABLE "identity-manager-tokens-tbl" IS 'Tokens JWT emitidos a usuarios para acceso al proxy de Bedrock';
COMMENT ON COLUMN "identity-manager-tokens-tbl".id IS 'UUID único del token';
COMMENT ON COLUMN "identity-manager-tokens-tbl".jti IS 'JWT ID único del token';

-- =====================================================
-- TABLA: identity-manager-permission-types-tbl
-- Descripción: Tipos de permisos disponibles
-- =====================================================
CREATE TABLE "identity-manager-permission-types-tbl" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    level INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE "identity-manager-permission-types-tbl" IS 'Catálogo de tipos de permisos (Read-only, Write, Admin, etc.)';
COMMENT ON COLUMN "identity-manager-permission-types-tbl".id IS 'UUID único del tipo de permiso';
COMMENT ON COLUMN "identity-manager-permission-types-tbl".level IS 'Nivel jerárquico del permiso (1=menor, 100=mayor)';

-- =====================================================
-- TABLA: identity-manager-app-permissions-tbl
-- Descripción: Permisos de usuarios sobre aplicaciones
-- =====================================================
CREATE TABLE "identity-manager-app-permissions-tbl" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cognito_user_id VARCHAR(255) NOT NULL,
    cognito_email VARCHAR(255) NOT NULL,
    application_id UUID NOT NULL,
    permission_type_id UUID NOT NULL,
    granted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT true,
    CONSTRAINT fk_app_perms_application FOREIGN KEY (application_id) REFERENCES "identity-manager-applications-tbl"(id) ON DELETE CASCADE,
    CONSTRAINT fk_app_perms_type FOREIGN KEY (permission_type_id) REFERENCES "identity-manager-permission-types-tbl"(id) ON DELETE RESTRICT,
    CONSTRAINT uk_user_application_permission UNIQUE (cognito_user_id, application_id)
);

COMMENT ON TABLE "identity-manager-app-permissions-tbl" IS 'Permisos de usuarios sobre aplicaciones completas';
COMMENT ON COLUMN "identity-manager-app-permissions-tbl".id IS 'UUID único del permiso';

-- =====================================================
-- TABLA: identity-manager-module-permissions-tbl
-- Descripción: Permisos de usuarios sobre módulos específicos
-- =====================================================
CREATE TABLE "identity-manager-module-permissions-tbl" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cognito_user_id VARCHAR(255) NOT NULL,
    cognito_email VARCHAR(255) NOT NULL,
    application_module_id UUID NOT NULL,
    permission_type_id UUID NOT NULL,
    granted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT true,
    CONSTRAINT fk_mod_perms_module FOREIGN KEY (application_module_id) REFERENCES "identity-manager-modules-tbl"(id) ON DELETE CASCADE,
    CONSTRAINT fk_mod_perms_type FOREIGN KEY (permission_type_id) REFERENCES "identity-manager-permission-types-tbl"(id) ON DELETE RESTRICT,
    CONSTRAINT uk_user_module_permission UNIQUE (cognito_user_id, application_module_id)
);

COMMENT ON TABLE "identity-manager-module-permissions-tbl" IS 'Permisos de usuarios sobre módulos específicos de aplicaciones';
COMMENT ON COLUMN "identity-manager-module-permissions-tbl".id IS 'UUID único del permiso';

-- =====================================================
-- TABLA: identity-manager-config-tbl
-- Descripción: Parámetros de configuración de la aplicación
-- =====================================================
CREATE TABLE "identity-manager-config-tbl" (
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

-- =====================================================
-- TABLA: identity-manager-audit-tbl
-- Descripción: Registro de auditoría de operaciones
-- =====================================================
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

COMMENT ON TABLE "identity-manager-audit-tbl" IS 'Registro de auditoría de todas las operaciones del sistema';
COMMENT ON COLUMN "identity-manager-audit-tbl".id IS 'UUID único del registro de auditoría';
COMMENT ON COLUMN "identity-manager-audit-tbl".resource_id IS 'UUID del recurso afectado';

-- =====================================================
-- ÍNDICES PARA MEJOR RENDIMIENTO
-- =====================================================

-- Índices en tokens
CREATE INDEX idx_tokens_cognito_user ON "identity-manager-tokens-tbl"(cognito_user_id);
CREATE INDEX idx_tokens_jti ON "identity-manager-tokens-tbl"(jti);
CREATE INDEX idx_tokens_expires ON "identity-manager-tokens-tbl"(expires_at);
CREATE INDEX idx_tokens_active ON "identity-manager-tokens-tbl"(is_revoked, expires_at);

-- Índices en permisos
CREATE INDEX idx_app_perms_user ON "identity-manager-app-permissions-tbl"(cognito_user_id);
CREATE INDEX idx_mod_perms_user ON "identity-manager-module-permissions-tbl"(cognito_user_id);

-- Índices en auditoría
CREATE INDEX idx_audit_user ON "identity-manager-audit-tbl"(cognito_user_id);
CREATE INDEX idx_audit_performed_by ON "identity-manager-audit-tbl"(performed_by_cognito_user_id);
CREATE INDEX idx_audit_timestamp ON "identity-manager-audit-tbl"(operation_timestamp DESC);
CREATE INDEX idx_audit_resource ON "identity-manager-audit-tbl"(resource_type, resource_id);

-- =====================================================
-- VISTAS ÚTILES
-- =====================================================

-- Vista: Tokens activos con información del perfil
CREATE VIEW "v_active_tokens" AS
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

-- Vista: Permisos de usuarios consolidados
CREATE VIEW "v_user_permissions" AS
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

-- Vista: Application profiles con información completa
CREATE VIEW "v_application_profiles" AS
SELECT 
    ap.id,
    ap.profile_name,
    ap.cognito_group_name,
    a.name as application_name,
    a.id as application_id,
    m.model_name,
    m.model_id,
    m.provider,
    ap.model_arn,
    ap.is_active,
    ap.created_at,
    ap.updated_at
FROM "identity-manager-profiles-tbl" ap
LEFT JOIN "identity-manager-applications-tbl" a ON ap.application_id = a.id
JOIN "identity-manager-models-tbl" m ON ap.model_id = m.id;

-- =====================================================
-- FUNCIONES Y TRIGGERS
-- =====================================================

-- Función para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers para actualizar updated_at
CREATE TRIGGER trg_models_updated_at
    BEFORE UPDATE ON "identity-manager-models-tbl"
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_applications_updated_at
    BEFORE UPDATE ON "identity-manager-applications-tbl"
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_modules_updated_at
    BEFORE UPDATE ON "identity-manager-modules-tbl"
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_profiles_updated_at
    BEFORE UPDATE ON "identity-manager-profiles-tbl"
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_config_updated_at
    BEFORE UPDATE ON "identity-manager-config-tbl"
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- END OF SCHEMA
-- =====================================================
