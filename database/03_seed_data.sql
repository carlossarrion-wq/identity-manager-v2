-- ============================================================================
-- IDENTITY MANAGER V2 - SEED DATA
-- ============================================================================
-- Version: 5.0
-- Date: 2026-03-05
-- Description: Datos iniciales para las tablas del sistema
-- 
-- Uso: psql -h <host> -U <user> -d <database> -f 03_seed_data.sql
-- ============================================================================

-- ============================================================================
-- 1. MODELS - Modelos LLM
-- ============================================================================

INSERT INTO "identity-manager-models-tbl" (id, model_id, model_name, model_arn, provider, description, is_active)
VALUES
    ('18b225b3-0f3c-4033-8df2-c714ebc2c98e', 'eu.anthropic.claude-3-5-sonnet-20241022-v2:0', 'Claude 3.5 Sonnet v2 (EU)', 'arn:aws:bedrock:eu-west-1::foundation-model/eu.anthropic.claude-3-5-sonnet-20241022-v2:0', 'Anthropic', 'Modelo Claude 3.5 Sonnet v2 - Región EU para cumplimiento GDPR', true),
    ('5c7ac5fa-975e-493e-ad4b-ba53727d989f', 'eu.anthropic.claude-3-5-haiku-20241022-v1:0', 'Claude 3.5 Haiku (EU)', 'arn:aws:bedrock:eu-west-1::foundation-model/eu.anthropic.claude-3-5-haiku-20241022-v1:0', 'Anthropic', 'Modelo Claude 3.5 Haiku - Región EU para cumplimiento GDPR', true),
    ('7fac19e2-aeb9-47ba-be13-6ea3746a55e8', 'eu.anthropic.claude-sonnet-4-5-v2:0', 'Claude Sonnet 4.5 v2 (EU)', 'arn:aws:bedrock:eu-west-1::foundation-model/eu.anthropic.claude-sonnet-4-5-v2:0', 'Anthropic', 'Modelo Claude Sonnet 4.5 v2 - Región EU para cumplimiento GDPR', true),
    ('18f38b61-a891-437e-9002-88c7b8a20cc7', 'eu.anthropic.claude-sonnet-4-5-20250929-v1:0', 'Claude Sonnet 4.5 (EU) - 2025-09-29', 'arn:aws:bedrock:eu-west-1::foundation-model/eu.anthropic.claude-sonnet-4-5-20250929-v1:0', 'Anthropic', 'Modelo Claude Sonnet 4.5 versión 2025-09-29 - Región EU para cumplimiento GDPR', true)
ON CONFLICT (model_id) DO UPDATE SET
    model_name = EXCLUDED.model_name,
    model_arn = EXCLUDED.model_arn,
    description = EXCLUDED.description,
    is_active = EXCLUDED.is_active,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- 2. APPLICATIONS - Aplicaciones del sistema
-- ============================================================================

INSERT INTO "identity-manager-applications-tbl" (id, name, description, is_active, display_order)
VALUES
    ('47a8122d-3ebf-4d5b-9431-312915673534', 'kb-agent', 'Agente de Conocimiento', true, 1),
    ('979246a8-3b5b-48e2-bb34-3558e554a1bf', 'bedrock-proxy', 'Proxy Bedrock', true, 2),
    ('bfb42ed5-b9dc-47e9-af9f-b80f23c919d6', 'capacity-mgmt', 'Gestor de Capacidad', true, 3),
    ('e61e1af9-8992-4bdf-be65-9cad86f34da0', 'identity-mgmt', 'Gestor de Identidades', true, 4),
    ('cb3a0ae2-bb78-4ab0-8116-cd0b8fcdae03', 'bedrock-dashboard', 'Control de Uso Bedrock', true, 5),
    ('613cbecc-d3bb-42e0-b6e5-6d95a2654ad9', 'kb-agent-dashboard', 'Control de Uso Knowledge Base', true, 6),
    ('a86fce02-5dd6-4b59-a78c-6a2b76c73e02', 'test-planner', 'Planificador de Pruebas', true, 7),
    ('62938c3a-32f8-466b-9a7b-d82eff51f685', 'user-mgmt-tools', 'Herramientas de línea de comandos para gestión de usuarios', true, 8),
    ('fdc63e70-8eb7-4bd7-86a6-3dca529f9dbe', 'cline', 'Agente de codificación Cline', true, 9)
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    is_active = EXCLUDED.is_active,
    display_order = EXCLUDED.display_order,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- 3. PERMISSION TYPES - Tipos de permisos
-- ============================================================================

INSERT INTO "identity-manager-permission-types-tbl" (id, name, description, level)
VALUES
    ('eb1c2549-5a68-4991-a5a6-1646260b79ba', 'read', 'Permiso de solo lectura', 10),
    ('b8d6d785-f8e6-48f7-9d84-5c0e9c1ec6ac', 'write', 'Permiso de lectura y escritura', 50),
    ('b74afac8-1bd9-42e0-be3d-17f00f732fa5', 'admin', 'Permiso de administración completa', 100)
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    level = EXCLUDED.level;

-- ============================================================================
-- 4. CONFIG - Configuración del sistema
-- ============================================================================

INSERT INTO "identity-manager-config-tbl" (id, config_key, config_value, description, is_sensitive)
VALUES
    ('018b0f41-6f04-4c9f-a4ce-ec63fce5f3ec', 'app_name', 'Identity Manager', 'Nombre de la aplicación', false),
    ('bab1fcc3-7b7b-4824-86c1-ed2abc52c386', 'app_version', '5.0.0', 'Versión de la aplicación (UUID Edition)', false),
    ('9dad0e35-19c1-4fdc-8d50-d558ae0f6695', 'bedrock_region', 'eu-west-1', 'Región de AWS Bedrock', false),
    ('6a376a0a-d60f-4d54-9a19-a47fe5f4274f', 'cognito_region', 'eu-west-1', 'Región de AWS donde está Cognito', false),
    ('d1e0e172-3a11-4d02-9395-3774bd9c14fd', 'cognito_user_pool_id', 'eu-west-1_UaMIbG9pD', 'ID del User Pool de Cognito', false),
    ('1efb8938-b341-4f8d-877b-f10bda0ae179', 'db_secret_name', 'identity-mgmt-dev-db-admin', 'Nombre del secreto en AWS Secrets Manager', true),
    ('788de88b-7150-486a-bd77-447cbbebdcae', 'default_daily_request_limit', '1000', 'Límite de peticiones diarias por defecto para nuevos usuarios', false),
    ('0b536362-9c75-4865-b016-33f53a8cb206', 'default_model', 'eu.anthropic.claude-sonnet-4-5-v2:0', 'Modelo LLM por defecto (Claude Sonnet 4.5)', false),
    ('1abb5987-d94f-4948-b3d9-f8152d6dbd31', 'enable_audit_log', 'true', 'Habilitar registro de auditoría', false),
    ('0d055b93-2264-47e3-a024-f12b2235272c', 'jwt_token_audiences', 'bedrock-proxy', 'Aplicaciones destino de los tokens JWT (separadas por comas)', false),
    ('5cd83db7-31bf-41f4-a42a-e0c901247477', 'max_tokens_per_user', '2', 'Máximo de tokens activos por usuario', false),
    ('f32371b8-5cc0-41b3-b54a-8510218f2baf', 'token_expiry_hours', '2160', 'Horas de validez de los tokens JWT (90 días)', false)
ON CONFLICT (config_key) DO UPDATE SET
    config_value = EXCLUDED.config_value,
    description = EXCLUDED.description,
    is_sensitive = EXCLUDED.is_sensitive,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- FIN DE SEED DATA
-- ============================================================================