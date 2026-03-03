-- =====================================================
-- CONSOLIDATED MIGRATIONS SCRIPT
-- =====================================================
-- Purpose: All migrations consolidated into a single script
-- Date: 2026-03-02
-- Includes: 006, 007, 007_fix, 008
-- =====================================================

-- =====================================================
-- MIGRATION 006: Create Usage Tracking Table
-- =====================================================

CREATE TABLE "bedrock-proxy-usage-tracking-tbl" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cognito_user_id VARCHAR(255) NOT NULL,
    cognito_email VARCHAR(255) NOT NULL,
    request_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    model_id VARCHAR(255) NOT NULL,  -- Changed from UUID to VARCHAR to support ARNs
    source_ip VARCHAR(45),
    user_agent TEXT,
    aws_region VARCHAR(50),
    tokens_input INTEGER,
    tokens_output INTEGER,
    tokens_cache_read INTEGER DEFAULT 0,
    tokens_cache_creation INTEGER DEFAULT 0,
    cost_usd DECIMAL(10, 6),
    processing_time_ms INTEGER,
    response_status VARCHAR(20) NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE "bedrock-proxy-usage-tracking-tbl" IS 
    'Registro de uso de API y modelos Bedrock con métricas de costos y rendimiento';

COMMENT ON COLUMN "bedrock-proxy-usage-tracking-tbl".model_id IS 
    'Model identifier - can be a UUID or an ARN (e.g., arn:aws:bedrock:region:account:application-inference-profile/id)';

-- Índices
CREATE INDEX idx_usage_cognito_user ON "bedrock-proxy-usage-tracking-tbl"(cognito_user_id);
CREATE INDEX idx_usage_cognito_email ON "bedrock-proxy-usage-tracking-tbl"(cognito_email);
CREATE INDEX idx_usage_request_timestamp ON "bedrock-proxy-usage-tracking-tbl"(request_timestamp DESC);
CREATE INDEX idx_usage_model ON "bedrock-proxy-usage-tracking-tbl"(model_id);
CREATE INDEX idx_usage_response_status ON "bedrock-proxy-usage-tracking-tbl"(response_status);
CREATE INDEX idx_usage_user_timestamp ON "bedrock-proxy-usage-tracking-tbl"(cognito_user_id, request_timestamp DESC);
CREATE INDEX idx_usage_model_timestamp ON "bedrock-proxy-usage-tracking-tbl"(model_id, request_timestamp DESC);
CREATE INDEX idx_usage_errors ON "bedrock-proxy-usage-tracking-tbl"(response_status, request_timestamp DESC) WHERE response_status != 'success';

-- Vistas
CREATE VIEW v_usage_by_model AS
SELECT 
    model_id,
    COUNT(*) as request_count,
    SUM(tokens_input) as total_tokens_input,
    SUM(tokens_output) as total_tokens_output,
    SUM(tokens_cache_read) as total_tokens_cache_read,
    SUM(tokens_cache_creation) as total_tokens_cache_creation,
    SUM(cost_usd) as total_cost_usd,
    AVG(processing_time_ms) as avg_processing_time_ms,
    MIN(request_timestamp) as first_request,
    MAX(request_timestamp) as last_request
FROM "bedrock-proxy-usage-tracking-tbl"
GROUP BY model_id
ORDER BY request_count DESC;

CREATE VIEW v_usage_detailed AS
SELECT 
    id, cognito_user_id, cognito_email, request_timestamp,
    model_id, source_ip, user_agent, aws_region,
    tokens_input, tokens_output, tokens_cache_read, tokens_cache_creation,
    cost_usd, processing_time_ms, response_status, error_message, created_at
FROM "bedrock-proxy-usage-tracking-tbl"
ORDER BY request_timestamp DESC;

CREATE VIEW v_recent_errors AS
SELECT 
    id, cognito_user_id, cognito_email, request_timestamp,
    model_id, response_status, error_message, created_at
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE response_status != 'success'
ORDER BY request_timestamp DESC
LIMIT 100;

-- =====================================================
-- MIGRATION 007: Create Daily Quota Control System
-- =====================================================

-- Configuración global
INSERT INTO "identity-manager-config-tbl" (config_key, config_value, description, is_sensitive)
VALUES 
    ('default_daily_request_limit', '1000', 'Límite de peticiones diarias por defecto para nuevos usuarios', false)
ON CONFLICT (config_key) DO UPDATE
SET config_value = EXCLUDED.config_value,
    description = EXCLUDED.description,
    updated_at = CURRENT_TIMESTAMP;

-- Tabla de cuotas
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
    administrative_safe BOOLEAN NOT NULL DEFAULT false,
    administrative_safe_set_by VARCHAR(255),
    administrative_safe_set_at TIMESTAMP,
    administrative_safe_reason TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_request_at TIMESTAMP
);

COMMENT ON TABLE "bedrock-proxy-user-quotas-tbl" IS 
    'Control de cuotas diarias por usuario con bloqueo automático';

-- Tabla de historial de bloqueos
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
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Índices
CREATE INDEX idx_quotas_user_id ON "bedrock-proxy-user-quotas-tbl"(cognito_user_id);
CREATE INDEX idx_quotas_blocked ON "bedrock-proxy-user-quotas-tbl"(is_blocked) WHERE is_blocked = true;
CREATE INDEX idx_quotas_date ON "bedrock-proxy-user-quotas-tbl"(quota_date);
CREATE INDEX idx_quota_history_user ON "bedrock-proxy-quota-blocks-history-tbl"(cognito_user_id);
CREATE INDEX idx_quota_history_date ON "bedrock-proxy-quota-blocks-history-tbl"(block_date DESC);

-- Función principal: check_and_update_quota
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
    v_default_limit INTEGER;
    v_effective_limit INTEGER;
BEGIN
    -- Obtener límite por defecto de configuración
    SELECT config_value::INTEGER INTO v_default_limit
    FROM "identity-manager-config-tbl"
    WHERE config_key = 'default_daily_request_limit';
    
    v_default_limit := COALESCE(v_default_limit, 1000);
    
    -- Obtener o crear registro de cuota CON daily_request_limit
    INSERT INTO "bedrock-proxy-user-quotas-tbl" (
        cognito_user_id, 
        cognito_email,
        quota_date,
        requests_today,
        daily_request_limit
    )
    VALUES (
        p_cognito_user_id, 
        p_cognito_email, 
        v_today, 
        0,
        v_default_limit
    )
    ON CONFLICT (cognito_user_id) DO UPDATE
    SET daily_request_limit = COALESCE(
            "bedrock-proxy-user-quotas-tbl".daily_request_limit,
            v_default_limit
        ),
        updated_at = CURRENT_TIMESTAMP;
    
    -- Obtener estado actual
    SELECT * INTO v_quota
    FROM "bedrock-proxy-user-quotas-tbl"
    WHERE cognito_user_id = p_cognito_user_id
    FOR UPDATE;
    
    v_effective_limit := v_quota.daily_request_limit;
    
    -- Verificar si el bloqueo ha expirado
    IF v_quota.is_blocked AND v_quota.blocked_until IS NOT NULL 
       AND v_quota.blocked_until <= CURRENT_TIMESTAMP THEN
        UPDATE "bedrock-proxy-quota-blocks-history-tbl"
        SET unblocked_at = CURRENT_TIMESTAMP,
            unblock_type = 'automatic'
        WHERE cognito_user_id = p_cognito_user_id
            AND unblocked_at IS NULL;
        
        UPDATE "bedrock-proxy-user-quotas-tbl"
        SET is_blocked = false,
            blocked_at = NULL,
            blocked_until = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE cognito_user_id = p_cognito_user_id;
        
        v_quota.is_blocked := false;
    END IF;
    
    -- Reset si es un nuevo día
    IF v_quota.quota_date < v_today THEN
        UPDATE "bedrock-proxy-user-quotas-tbl"
        SET quota_date = v_today,
            requests_today = 0,
            administrative_safe = false,
            administrative_safe_set_by = NULL,
            administrative_safe_set_at = NULL,
            administrative_safe_reason = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE cognito_user_id = p_cognito_user_id;
        
        v_quota.quota_date := v_today;
        v_quota.requests_today := 0;
        v_quota.administrative_safe := false;
    END IF;
    
    -- Verificar si está bloqueado
    IF v_quota.is_blocked AND NOT v_quota.administrative_safe THEN
        RETURN QUERY SELECT 
            false,
            v_quota.requests_today,
            v_effective_limit,
            true,
            format('Daily quota exceeded. Blocked until %s', 
                   to_char(v_quota.blocked_until, 'YYYY-MM-DD HH24:MI:SS'))::TEXT;
        RETURN;
    END IF;
    
    -- Verificar si alcanzará el límite
    IF v_quota.requests_today >= v_effective_limit AND NOT v_quota.administrative_safe THEN
        UPDATE "bedrock-proxy-user-quotas-tbl"
        SET is_blocked = true,
            blocked_at = CURRENT_TIMESTAMP,
            blocked_until = (CURRENT_DATE + INTERVAL '1 day')::TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE cognito_user_id = p_cognito_user_id;
        
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
            v_effective_limit
        );
        
        RETURN QUERY SELECT 
            false,
            v_quota.requests_today,
            v_effective_limit,
            true,
            format('Daily quota limit reached. User blocked until %s', 
                   to_char((CURRENT_DATE + INTERVAL '1 day')::TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'))::TEXT;
        RETURN;
    END IF;
    
    -- Incrementar contador
    UPDATE "bedrock-proxy-user-quotas-tbl"
    SET requests_today = "bedrock-proxy-user-quotas-tbl".requests_today + 1,
        last_request_at = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE cognito_user_id = p_cognito_user_id;
    
    RETURN QUERY SELECT 
        true,
        v_quota.requests_today + 1,
        v_effective_limit,
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
    SELECT is_blocked INTO v_was_blocked
    FROM "bedrock-proxy-user-quotas-tbl"
    WHERE cognito_user_id = p_cognito_user_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'User % not found', p_cognito_user_id;
    END IF;
    
    UPDATE "bedrock-proxy-user-quotas-tbl"
    SET administrative_safe = true,
        administrative_safe_set_by = p_admin_user_id,
        administrative_safe_set_at = CURRENT_TIMESTAMP,
        administrative_safe_reason = p_reason,
        is_blocked = false,
        updated_at = CURRENT_TIMESTAMP
    WHERE cognito_user_id = p_cognito_user_id;
    
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

-- Función: Actualizar límite diario
CREATE OR REPLACE FUNCTION update_user_daily_limit(
    p_cognito_user_id VARCHAR(255),
    p_new_limit INTEGER
)
RETURNS BOOLEAN AS $$
BEGIN
    IF p_new_limit < 0 THEN
        RAISE EXCEPTION 'Daily limit must be >= 0';
    END IF;
    
    UPDATE "bedrock-proxy-user-quotas-tbl"
    SET daily_request_limit = p_new_limit,
        updated_at = CURRENT_TIMESTAMP
    WHERE cognito_user_id = p_cognito_user_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'User % not found', p_cognito_user_id;
    END IF;
    
    RETURN true;
END;
$$ LANGUAGE plpgsql;

-- Función: Bloqueo administrativo
CREATE OR REPLACE FUNCTION administrative_block_user(
    p_cognito_user_id VARCHAR(255),
    p_admin_user_id VARCHAR(255),
    p_block_until TIMESTAMP,
    p_reason TEXT DEFAULT NULL
)
RETURNS BOOLEAN AS $$
BEGIN
    IF p_block_until <= CURRENT_TIMESTAMP THEN
        RAISE EXCEPTION 'Block until date must be in the future';
    END IF;
    
    UPDATE "bedrock-proxy-user-quotas-tbl"
    SET is_blocked = true,
        blocked_at = CURRENT_TIMESTAMP,
        blocked_until = p_block_until,
        administrative_safe = false,
        administrative_safe_set_by = p_admin_user_id,
        administrative_safe_set_at = CURRENT_TIMESTAMP,
        administrative_safe_reason = p_reason,
        updated_at = CURRENT_TIMESTAMP
    WHERE cognito_user_id = p_cognito_user_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'User % not found', p_cognito_user_id;
    END IF;
    
    INSERT INTO "bedrock-proxy-quota-blocks-history-tbl" (
        cognito_user_id,
        cognito_email,
        block_date,
        blocked_at,
        requests_count,
        daily_limit,
        unblocked_by,
        unblock_reason
    )
    SELECT 
        cognito_user_id,
        cognito_email,
        CURRENT_DATE,
        CURRENT_TIMESTAMP,
        requests_today,
        COALESCE(daily_request_limit, 1000),
        p_admin_user_id,
        p_reason
    FROM "bedrock-proxy-user-quotas-tbl"
    WHERE cognito_user_id = p_cognito_user_id;
    
    RETURN true;
END;
$$ LANGUAGE plpgsql;

-- Función: Obtener estado de cuota
CREATE OR REPLACE FUNCTION get_user_quota_status(
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
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        q.cognito_user_id,
        q.cognito_email,
        COALESCE(q.daily_request_limit, 
            (SELECT config_value::INTEGER FROM "identity-manager-config-tbl" 
             WHERE config_key = 'default_daily_request_limit'), 
            1000) as daily_limit,
        q.requests_today,
        COALESCE(q.daily_request_limit, 
            (SELECT config_value::INTEGER FROM "identity-manager-config-tbl" 
             WHERE config_key = 'default_daily_request_limit'), 
            1000) - q.requests_today as remaining_requests,
        ROUND(100.0 * q.requests_today / COALESCE(q.daily_request_limit, 
            (SELECT config_value::INTEGER FROM "identity-manager-config-tbl" 
             WHERE config_key = 'default_daily_request_limit'), 
            1000), 2) as usage_percentage,
        q.is_blocked,
        q.blocked_at,
        q.administrative_safe,
        q.last_request_at
    FROM "bedrock-proxy-user-quotas-tbl" q
    WHERE q.cognito_user_id = p_cognito_user_id;
END;
$$ LANGUAGE plpgsql;

-- Vistas de cuotas
CREATE VIEW v_users_near_limit AS
SELECT 
    cognito_user_id,
    cognito_email,
    requests_today,
    COALESCE(daily_request_limit, 
        (SELECT config_value::INTEGER FROM "identity-manager-config-tbl" 
         WHERE config_key = 'default_daily_request_limit'), 
        1000) as daily_limit,
    (COALESCE(daily_request_limit, 
        (SELECT config_value::INTEGER FROM "identity-manager-config-tbl" 
         WHERE config_key = 'default_daily_request_limit'), 
        1000) - requests_today) as remaining,
    ROUND(100.0 * requests_today / COALESCE(daily_request_limit, 
        (SELECT config_value::INTEGER FROM "identity-manager-config-tbl" 
         WHERE config_key = 'default_daily_request_limit'), 
        1000), 2) as usage_pct
FROM "bedrock-proxy-user-quotas-tbl"
WHERE requests_today >= (COALESCE(daily_request_limit, 
        (SELECT config_value::INTEGER FROM "identity-manager-config-tbl" 
         WHERE config_key = 'default_daily_request_limit'), 
        1000) * 0.8)
    AND is_blocked = false
    AND quota_date = CURRENT_DATE
ORDER BY usage_pct DESC;

-- =====================================================
-- MIGRATION 007_FIX: Actualizar registros existentes
-- =====================================================
UPDATE "bedrock-proxy-user-quotas-tbl"
SET daily_request_limit = (
    SELECT config_value::INTEGER 
    FROM "identity-manager-config-tbl" 
    WHERE config_key = 'default_daily_request_limit'
)
WHERE daily_request_limit IS NULL;

-- =====================================================
-- END OF CONSOLIDATED MIGRATIONS
-- =====================================================