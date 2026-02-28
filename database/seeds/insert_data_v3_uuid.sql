-- =====================================================
-- IDENTITY MANAGER - DATOS INICIALES (UUID VERSION)
-- =====================================================
-- Version: 3.0 - UUID Edition
-- Date: 2026-02-27
-- 
-- Este script inserta todos los datos iniciales necesarios
-- Los UUIDs se generan automáticamente
-- =====================================================

-- =====================================================
-- 1. TIPOS DE PERMISOS
-- =====================================================
INSERT INTO "identity-manager-permission-types-tbl" (name, description, level) VALUES
    ('read', 'Permiso de solo lectura', 10),
    ('write', 'Permiso de lectura y escritura', 50),
    ('admin', 'Permiso de administración completa', 100)
ON CONFLICT (name) DO NOTHING;

-- =====================================================
-- 2. MODELOS LLM (EU Compliance)
-- =====================================================
INSERT INTO "identity-manager-models-tbl" (model_id, model_name, model_arn, provider, description) VALUES
    (
        'eu.anthropic.claude-3-5-sonnet-20241022-v2:0',
        'Claude 3.5 Sonnet v2 (EU)',
        'arn:aws:bedrock:eu-west-1::foundation-model/eu.anthropic.claude-3-5-sonnet-20241022-v2:0',
        'Anthropic',
        'Modelo Claude 3.5 Sonnet v2 - Región EU para cumplimiento GDPR'
    ),
    (
        'eu.anthropic.claude-3-5-haiku-20241022-v1:0',
        'Claude 3.5 Haiku (EU)',
        'arn:aws:bedrock:eu-west-1::foundation-model/eu.anthropic.claude-3-5-haiku-20241022-v1:0',
        'Anthropic',
        'Modelo Claude 3.5 Haiku - Región EU para cumplimiento GDPR'
    ),
    (
        'eu.anthropic.claude-sonnet-4-5-v2:0',
        'Claude Sonnet 4.5 v2 (EU)',
        'arn:aws:bedrock:eu-west-1::foundation-model/eu.anthropic.claude-sonnet-4-5-v2:0',
        'Anthropic',
        'Modelo Claude Sonnet 4.5 v2 - Región EU para cumplimiento GDPR'
    )
ON CONFLICT (model_id) DO NOTHING;

-- =====================================================
-- 3. APLICACIONES
-- =====================================================
INSERT INTO "identity-manager-applications-tbl" (name, description, display_order, is_active) VALUES
    ('kb-agent', 'Agente de Conocimiento', 1, true),
    ('bedrock-proxy', 'Proxy Bedrock', 2, true),
    ('capacity-mgmt', 'Gestor de Capacidad', 3, true),
    ('identity-mgmt', 'Gestor de Identidades', 4, true),
    ('bedrock-dashboard', 'Control de Uso Bedrock', 5, true),
    ('kb-agent-dashboard', 'Control de Uso Knowledge Base', 6, true),
    ('test-planner', 'Planificador de Pruebas', 7, true),
    ('user-mgmt-tools', 'Herramientas de línea de comandos para gestión de usuarios', 8, true),
    ('cline', 'Agente de codificación Cline', 9, true)
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    display_order = EXCLUDED.display_order,
    updated_at = CURRENT_TIMESTAMP;

-- =====================================================
-- 4. MÓDULOS (para aplicación kb-agent)
-- =====================================================
-- Obtenemos el UUID de la aplicación kb-agent
DO $$
DECLARE
    kb_agent_app_id UUID;
BEGIN
    SELECT id INTO kb_agent_app_id 
    FROM "identity-manager-applications-tbl" 
    WHERE name = 'kb-agent';
    
    IF kb_agent_app_id IS NOT NULL THEN
        INSERT INTO "identity-manager-modules-tbl" (application_id, name, description, display_order) VALUES
            (kb_agent_app_id, 'chat', 'Módulo de chat interactivo con la base de conocimiento', 1),
            (kb_agent_app_id, 'document-management', 'Módulo de gestión de documentos', 2)
        ON CONFLICT (application_id, name) DO NOTHING;
    END IF;
END $$;

-- =====================================================
-- 5. PARÁMETROS DE CONFIGURACIÓN
-- =====================================================
INSERT INTO "identity-manager-config-tbl" (config_key, config_value, description, is_sensitive) VALUES
    ('db_secret_name', 'identity-mgmt-dev-db-admin', 'Nombre del secreto en AWS Secrets Manager', true),
    ('cognito_user_pool_id', 'eu-west-1_UaMIbG9pD', 'ID del User Pool de Cognito', false),
    ('cognito_region', 'eu-west-1', 'Región de AWS donde está Cognito', false),
    ('app_name', 'Identity Manager', 'Nombre de la aplicación', false),
    ('app_version', '5.0.0', 'Versión de la aplicación (UUID Edition)', false),
    ('token_expiry_hours', '2160', 'Horas de validez de los tokens JWT (90 días)', false),
    ('max_tokens_per_user', '2', 'Máximo de tokens activos por usuario', false),
    ('enable_audit_log', 'true', 'Habilitar registro de auditoría', false),
    ('bedrock_region', 'eu-west-1', 'Región de AWS Bedrock', false),
    ('default_model', 'eu.anthropic.claude-sonnet-4-5-v2:0', 'Modelo LLM por defecto (Claude Sonnet 4.5)', false),
    ('jwt_token_audiences', 'bedrock-proxy', 'Aplicaciones destino de los tokens JWT (separadas por comas)', false)
ON CONFLICT (config_key) DO UPDATE SET
    config_value = EXCLUDED.config_value,
    updated_at = CURRENT_TIMESTAMP;

-- =====================================================
-- 6. PERFIL DE EJEMPLO (OPCIONAL - COMENTADO)
-- =====================================================
-- Descomentar si quieres crear un perfil de ejemplo
/*
DO $$
DECLARE
    app_id UUID;
    model_id UUID;
BEGIN
    -- Obtener IDs
    SELECT id INTO app_id FROM "identity-manager-applications-tbl" WHERE name = 'cline';
    SELECT id INTO model_id FROM "identity-manager-models-tbl" WHERE model_id = 'eu.anthropic.claude-3-5-sonnet-20241022-v2:0';
    
    IF app_id IS NOT NULL AND model_id IS NOT NULL THEN
        INSERT INTO "identity-manager-profiles-tbl" 
            (profile_name, cognito_group_name, application_id, model_id, model_arn, description)
        VALUES
            (
                'Developers - Cline - Claude 3.5 Sonnet',
                'developers-group',
                app_id,
                model_id,
                'arn:aws:bedrock:eu-west-1::foundation-model/eu.anthropic.claude-3-5-sonnet-20241022-v2:0',
                'Perfil para desarrolladores usando Cline con Claude 3.5 Sonnet'
            )
        ON CONFLICT (cognito_group_name, application_id, model_id) DO NOTHING;
    END IF;
END $$;
*/

-- =====================================================
-- VERIFICACIÓN
-- =====================================================
-- Mostrar resumen de datos insertados
DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'DATOS INICIALES INSERTADOS CORRECTAMENTE';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Tipos de permisos: %', (SELECT COUNT(*) FROM "identity-manager-permission-types-tbl");
    RAISE NOTICE 'Modelos LLM: %', (SELECT COUNT(*) FROM "identity-manager-models-tbl");
    RAISE NOTICE 'Aplicaciones: %', (SELECT COUNT(*) FROM "identity-manager-applications-tbl");
    RAISE NOTICE 'Módulos: %', (SELECT COUNT(*) FROM "identity-manager-modules-tbl");
    RAISE NOTICE 'Configuraciones: %', (SELECT COUNT(*) FROM "identity-manager-config-tbl");
    RAISE NOTICE '==============================================';
END $$;

-- =====================================================
-- END OF SEEDS
-- =====================================================
