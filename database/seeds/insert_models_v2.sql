-- =====================================================
-- INSERT BEDROCK MODELS DATA
-- =====================================================
-- Insertar modelos de inferencia de AWS Bedrock
-- Tabla: identity-manager-models-tbl
-- =====================================================

INSERT INTO "identity-manager-models-tbl" (model_id, model_name, provider, description, is_active) VALUES
    ('eu.anthropic.claude-sonnet-4-5-20250929-v1:0', 'Claude Sonnet 4.5', 'Anthropic', 'Modelo Claude Sonnet 4.5 (EU)', true),
    ('eu.anthropic.claude-sonnet-4-6', 'Claude Sonnet 4.6', 'Anthropic', 'Modelo Claude Sonnet 4.6 (EU)', true),
    ('eu.anthropic.claude-haiku-4-5-20251001-v1:0', 'Claude Haiku 4.5', 'Anthropic', 'Modelo Claude Haiku 4.5 (EU)', true)
ON CONFLICT (model_id) DO UPDATE SET
    model_name = EXCLUDED.model_name,
    description = EXCLUDED.description,
    is_active = EXCLUDED.is_active,
    updated_at = CURRENT_TIMESTAMP;

-- Verificar los modelos insertados
SELECT id, model_id, model_name, provider, description, is_active, created_at 
FROM "identity-manager-models-tbl"
ORDER BY model_name;
