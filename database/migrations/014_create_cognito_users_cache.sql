-- ============================================================================
-- Migration 014: Crear tabla de caché de usuarios de Cognito
-- ============================================================================
-- Descripción: Tabla para cachear usuarios de Cognito y evitar llamadas lentas
-- Fecha: 2026-03-18
-- ============================================================================

-- Tabla de caché de usuarios de Cognito
CREATE TABLE IF NOT EXISTS "identity-manager-cognito-users-cache-tbl" (
    cognito_user_id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    person VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    created_date TIMESTAMP,
    groups TEXT[], -- Array de grupos
    auto_regenerate_tokens BOOLEAN DEFAULT TRUE,
    
    -- Metadatos de caché
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cache_expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '5 minutes'),
    
    -- Índices para búsquedas rápidas
    CONSTRAINT unique_email UNIQUE (email)
);

-- Índices para optimizar búsquedas
CREATE INDEX IF NOT EXISTS idx_cognito_cache_email ON "identity-manager-cognito-users-cache-tbl" (email);
CREATE INDEX IF NOT EXISTS idx_cognito_cache_status ON "identity-manager-cognito-users-cache-tbl" (status);
CREATE INDEX IF NOT EXISTS idx_cognito_cache_groups ON "identity-manager-cognito-users-cache-tbl" USING GIN (groups);
CREATE INDEX IF NOT EXISTS idx_cognito_cache_expires ON "identity-manager-cognito-users-cache-tbl" (cache_expires_at);

-- Comentarios
COMMENT ON TABLE "identity-manager-cognito-users-cache-tbl" IS 'Caché de usuarios de Cognito para mejorar rendimiento de listados';
COMMENT ON COLUMN "identity-manager-cognito-users-cache-tbl".cached_at IS 'Timestamp de cuando se cacheó el usuario';
COMMENT ON COLUMN "identity-manager-cognito-users-cache-tbl".cache_expires_at IS 'Timestamp de expiración del caché (5 minutos por defecto)';