-- =====================================================
-- MIGRATION 010: Add person field to proxy tables
-- =====================================================
-- Purpose: Add person field from JWT token to proxy tables
-- Date: 2026-03-03
-- =====================================================

-- Add person column to usage tracking table
ALTER TABLE "bedrock-proxy-usage-tracking-tbl"
ADD COLUMN person VARCHAR(255);

COMMENT ON COLUMN "bedrock-proxy-usage-tracking-tbl".person IS 
    'Person name from JWT token (e.g., Carlos Sarrión)';

-- Add person column to user quotas table
ALTER TABLE "bedrock-proxy-user-quotas-tbl"
ADD COLUMN person VARCHAR(255);

COMMENT ON COLUMN "bedrock-proxy-user-quotas-tbl".person IS 
    'Person name from JWT token (e.g., Carlos Sarrión)';

-- Add person column to quota blocks history table
ALTER TABLE "bedrock-proxy-quota-blocks-history-tbl"
ADD COLUMN person VARCHAR(255);

COMMENT ON COLUMN "bedrock-proxy-quota-blocks-history-tbl".person IS 
    'Person name from JWT token (e.g., Carlos Sarrión)';

-- Create index on person for better query performance
CREATE INDEX idx_usage_person ON "bedrock-proxy-usage-tracking-tbl"(person);
CREATE INDEX idx_quotas_person ON "bedrock-proxy-user-quotas-tbl"(person);
CREATE INDEX idx_quota_history_person ON "bedrock-proxy-quota-blocks-history-tbl"(person);

-- Update existing view to include person
DROP VIEW IF EXISTS v_usage_detailed;
CREATE VIEW v_usage_detailed AS
SELECT 
    id, cognito_user_id, cognito_email, person, team, request_timestamp,
    model_id, source_ip, user_agent, aws_region,
    tokens_input, tokens_output, tokens_cache_read, tokens_cache_creation,
    cost_usd, processing_time_ms, response_status, error_message, created_at
FROM "bedrock-proxy-usage-tracking-tbl"
ORDER BY request_timestamp DESC;

-- Update recent errors view to include person
DROP VIEW IF EXISTS v_recent_errors;
CREATE VIEW v_recent_errors AS
SELECT 
    id, cognito_user_id, cognito_email, person, team, request_timestamp,
    model_id, response_status, error_message, created_at
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE response_status != 'success'
ORDER BY request_timestamp DESC
LIMIT 100;

-- Update usage by team view to include person info
DROP VIEW IF EXISTS v_usage_by_team;
CREATE VIEW v_usage_by_team AS
SELECT 
    team,
    COUNT(*) as request_count,
    COUNT(DISTINCT cognito_user_id) as unique_users,
    COUNT(DISTINCT person) as unique_persons,
    SUM(tokens_input) as total_tokens_input,
    SUM(tokens_output) as total_tokens_output,
    SUM(tokens_cache_read) as total_tokens_cache_read,
    SUM(tokens_cache_creation) as total_tokens_cache_creation,
    SUM(cost_usd) as total_cost_usd,
    AVG(processing_time_ms) as avg_processing_time_ms,
    MIN(request_timestamp) as first_request,
    MAX(request_timestamp) as last_request
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE team IS NOT NULL
GROUP BY team
ORDER BY request_count DESC;

COMMENT ON VIEW v_usage_by_team IS 
    'Aggregated usage statistics by team including person count';

-- Create new view for usage by person
CREATE VIEW v_usage_by_person AS
SELECT 
    person,
    cognito_email,
    team,
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
WHERE person IS NOT NULL
GROUP BY person, cognito_email, team
ORDER BY request_count DESC;

COMMENT ON VIEW v_usage_by_person IS 
    'Aggregated usage statistics by person';

-- Drop existing function first (with old signature)
DROP FUNCTION IF EXISTS check_and_update_quota(VARCHAR(255), VARCHAR(255), VARCHAR(100));

-- Create new function with person parameter
CREATE OR REPLACE FUNCTION check_and_update_quota(
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
    
    -- Obtener o crear registro de cuota CON daily_request_limit, team y person
    INSERT INTO "bedrock-proxy-user-quotas-tbl" (
        cognito_user_id, 
        cognito_email,
        team,
        person,
        quota_date,
        requests_today,
        daily_request_limit
    )
    VALUES (
        p_cognito_user_id, 
        p_cognito_email,
        p_team,
        p_person,
        v_today, 
        0,
        v_default_limit
    )
    ON CONFLICT (cognito_user_id) DO UPDATE
    SET daily_request_limit = COALESCE(
            "bedrock-proxy-user-quotas-tbl".daily_request_limit,
            v_default_limit
        ),
        team = COALESCE(EXCLUDED.team, "bedrock-proxy-user-quotas-tbl".team),
        person = COALESCE(EXCLUDED.person, "bedrock-proxy-user-quotas-tbl".person),
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
            team,
            person,
            block_date,
            blocked_at,
            requests_count,
            daily_limit
        ) VALUES (
            p_cognito_user_id,
            p_cognito_email,
            p_team,
            p_person,
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

COMMENT ON FUNCTION check_and_update_quota IS 
    'Check and update user quota with team and person information from JWT token';

-- =====================================================
-- END OF MIGRATION 010
-- =====================================================