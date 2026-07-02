-- ============================================================================
-- Migration 016: Crear tabla de tokens MCP (Remedy MCP Server)
-- ============================================================================
-- Descripción: Tabla INDEPENDIENTE para los tokens JWT que los usuarios
--              configuran en Cline para acceder al servidor MCP de Remedy F1.
--              Es un flujo SEPARADO de "identity-manager-tokens-tbl" (proxy
--              Bedrock) para no impactar lo productivo existente.
--
--              El token lleva en sus claims: email, person (nombre) y el
--              usuario 900 de Naturgy (naturgy_user_900), que el MCP server
--              lee directamente del JWT (validación HS256 con secreto
--              compartido). NO usa perfiles de inferencia.
-- Fecha: 2026-06-29
-- ============================================================================

CREATE TABLE IF NOT EXISTS "identity-manager-mcp-tokens-tbl" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cognito_user_id VARCHAR(255) NOT NULL,
    cognito_email VARCHAR(255) NOT NULL,
    person VARCHAR(255),
    naturgy_user_900 VARCHAR(50),
    allowed_groups TEXT[] NOT NULL DEFAULT '{}',
    jti VARCHAR(255) NOT NULL UNIQUE,
    token_hash TEXT NOT NULL UNIQUE,
    issued_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    last_used_at TIMESTAMP,
    is_revoked BOOLEAN NOT NULL DEFAULT false,
    revoked_at TIMESTAMP,
    revocation_reason TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- Campos de regeneración (mismo modelo que la tabla de tokens del proxy)
    regenerated_at TIMESTAMP,
    regenerated_to_jti UUID,
    regenerated_from_jti UUID,
    regeneration_reason VARCHAR(100),
    regeneration_client_ip VARCHAR(45),
    regeneration_user_agent TEXT,
    regeneration_email_sent BOOLEAN DEFAULT false
);

COMMENT ON TABLE "identity-manager-mcp-tokens-tbl" IS 'Tokens JWT emitidos a usuarios para acceso al servidor MCP de Remedy F1 (independiente del proxy Bedrock)';
COMMENT ON COLUMN "identity-manager-mcp-tokens-tbl".naturgy_user_900 IS 'Usuario 900 de Naturgy; viaja en el claim del JWT para que el MCP lo lea';
COMMENT ON COLUMN "identity-manager-mcp-tokens-tbl".allowed_groups IS 'Grupos de Remedy a los que el usuario tiene acceso; viajan en el claim allowed_groups del JWT';
COMMENT ON COLUMN "identity-manager-mcp-tokens-tbl".person IS 'Nombre completo del usuario; viaja en el claim del JWT';

-- Índices (espejo de los de la tabla de tokens del proxy)
CREATE INDEX IF NOT EXISTS idx_mcp_tokens_cognito_user ON "identity-manager-mcp-tokens-tbl"(cognito_user_id);
CREATE INDEX IF NOT EXISTS idx_mcp_tokens_jti ON "identity-manager-mcp-tokens-tbl"(jti);
CREATE INDEX IF NOT EXISTS idx_mcp_tokens_expires ON "identity-manager-mcp-tokens-tbl"(expires_at);
CREATE INDEX IF NOT EXISTS idx_mcp_tokens_active ON "identity-manager-mcp-tokens-tbl"(is_revoked, expires_at);
CREATE INDEX IF NOT EXISTS idx_mcp_tokens_regenerated ON "identity-manager-mcp-tokens-tbl"(regenerated_at) WHERE regenerated_at IS NOT NULL;
