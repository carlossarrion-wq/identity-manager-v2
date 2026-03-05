-- ============================================================================
-- IDENTITY MANAGER V2 - FUNCTIONS, VIEWS & TRIGGERS
-- ============================================================================
-- Version: 5.0
-- Date: 2026-03-05
-- Description: Funciones PL/pgSQL, vistas y triggers del sistema
-- 
-- Uso: psql -h <host> -U <user> -d <database> -f 02_functions_views.sql
-- ============================================================================

-- ============================================================================
-- FUNCIONES PL/pgSQL
-- ============================================================================

-- ----------------------------------------------------------------------------
-- update_updated_at_column()
-- Trigger function para actualizar automáticamente el campo updated_at
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ----------------------------------------------------------------------------
-- check_and_update_quota()
-- Verifica y actualiza la cuota de un usuario con lógica de bloqueo automático
-- ----------------------------------------------------------------------------
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
    -- Obtener límite por defecto
    SELECT config_value::INTEGER INTO v_default_limit
    FROM "identity-manager-config-tbl"
    WHERE config_key = 'default_daily_request_limit';
    
    v_default_limit := COALESCE(v_default_limit, 1000);
    
    -- Obtener o crear registro de cuota
    INSERT INTO "bedrock-proxy-user-quotas-tbl" (
        cognito_user_id, cognito_email, team, person,
        quota_date, requests_today, daily_request_limit
    )
    VALUES (
        p_cognito_user_id, p_cognito_email, p_team, p_person,
        v_today, 0, v_default_limit
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
        SET unblocked_at = CURRENT_TIMESTAMP, unblock_type = 'automatic'
        WHERE cognito_user_id = p_cognito_user_id AND unblocked_at IS NULL;
        
        UPDATE "bedrock-proxy-user-quotas-tbl"
        SET is_blocked = false, blocked_at = NULL, blocked_until = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE cognito_user_id = p_cognito_user_id;
        
        v_quota.is_blocked := false;
    END IF;
    
    -- Reset si es un nuevo día
    IF v_quota.quota_date < v_today THEN
        UPDATE "bedrock-proxy-user-quotas-tbl"
        SET quota_date = v_today, requests_today = 0,
            administrative_safe = false, administrative_safe_set_by = NULL,
            administrative_safe_set_at = NULL, administrative_safe_reason = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE cognito_user_id = p_cognito_user_id;
        
        v_quota.quota_date := v_today;
        v_quota.requests_today := 0;
        v_quota.administrative_safe := false;
    END IF;
    
    -- Verificar si está bloqueado
    IF v_quota.is_blocked AND NOT v_quota.administrative_safe THEN
        RETURN QUERY SELECT 
            false, v_quota.requests_today, v_effective_limit, true,
            format('Daily quota exceeded. Blocked until %s', 
                   to_char(v_quota.blocked_until, 'YYYY-MM-DD HH24:MI:SS'))::TEXT;
        RETURN;
    END IF;
    
    -- Verificar si alcanzará el límite
    IF v_quota.requests_today >= v_effective_limit AND NOT v_quota.administrative_safe THEN
        UPDATE "bedrock-proxy-user-quotas-tbl"
        SET is_blocked = true, blocked_at = CURRENT_TIMESTAMP,
            blocked_until = (CURRENT_DATE + INTERVAL '1 day')::TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE cognito_user_id = p_cognito_user_id;
        
        INSERT INTO "bedrock-proxy-quota-blocks-history-tbl" (
            cognito_user_id, cognito_email, team, person,
            block_date, blocked_at, requests_count, daily_limit
        ) VALUES (
            p_cognito_user_id, p_cognito_email, p_team, p_person,
            v_today, CURRENT_TIMESTAMP, v_quota.requests_today, v_effective_limit
        );
        
        RETURN QUERY SELECT 
            false, v_quota.requests_today, v_effective_limit, true,
            format('Daily quota limit reached. User blocked until %s', 
                   to_char((CURRENT_DATE + INTERVAL '1 day')::TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'))::TEXT;
        RETURN;
    END IF;
    
    -- Incrementar contador
    UPDATE "bedrock-proxy-user-quotas-tbl"
    SET requests_today = requests_today + 1,
        last_request_at = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE cognito_user_id = p_cognito_user_id;
    
    RETURN QUERY SELECT 
        true, v_quota.requests_today + 1, v_effective_limit, false, NULL::TEXT;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION check_and_update_quota IS 'Verifica y actualiza cuota con team y person del JWT';

-- ----------------------------------------------------------------------------
-- administrative_block_user()
-- Bloquea un usuario administrativamente hasta una fecha específica
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION administrative_block_user(
    p_cognito_user_id VARCHAR(255),
    p_admin_user_id VARCHAR(255),
    p_block_until TIMESTAMP,
    p_reason TEXT DEFAULT NULL
) RETURNS BOOLEAN AS $$
BEGIN
    IF p_block_until <= CURRENT_TIMESTAMP THEN
        RAISE EXCEPTION 'Block until date must be in the future';
    END IF;
    
    UPDATE "bedrock-proxy-user-quotas-tbl"
    SET is_blocked = true, blocked_at = CURRENT_TIMESTAMP,
        blocked_until = p_block_until, administrative_safe = false,
        administrative_safe_set_by = p_admin_user_id,
        administrative_safe_set_at = CURRENT_TIMESTAMP,
        administrative_safe_reason = p_reason, updated_at = CURRENT_TIMESTAMP
    WHERE cognito_user_id = p_cognito_user_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'User % not found', p_cognito_user_id;
    END IF;
    
    INSERT INTO "bedrock-proxy-quota-blocks-history-tbl" (
        cognito_user_id, cognito_email, block_date, blocked_at,
        requests_count, daily_limit, unblocked_by, unblock_reason
    )
    SELECT cognito_user_id, cognito_email, CURRENT_DATE, CURRENT_TIMESTAMP,
           requests_today, COALESCE(daily_request_limit, 1000),
           p_admin_user_id, p_reason
    FROM "bedrock-proxy-user-quotas-tbl"
    WHERE cognito_user_id = p_cognito_user_id;
    
    RETURN true;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION administrative_block_user IS 'Bloquea usuario administrativamente hasta fecha específica';

-- ----------------------------------------------------------------------------
-- administrative_unblock_user()
-- Desbloquea un usuario administrativamente (activa safe mode)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION administrative_unblock_user(
    p_cognito_user_id VARCHAR(255),
    p_admin_user_id VARCHAR(255),
    p_reason TEXT DEFAULT NULL
) RETURNS BOOLEAN AS $$
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
        is_blocked = false, updated_at = CURRENT_TIMESTAMP
    WHERE cognito_user_id = p_cognito_user_id;
    
    IF v_was_blocked THEN
        UPDATE "bedrock-proxy-quota-blocks-history-tbl"
        SET unblocked_at = CURRENT_TIMESTAMP, unblock_type = 'administrative',
            unblocked_by = p_admin_user_id, unblock_reason = p_reason
        WHERE cognito_user_id = p_cognito_user_id
            AND block_date = CURRENT_DATE AND unblocked_at IS NULL;
    END IF;
    
    RETURN true;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION administrative_unblock_user IS 'Desbloquea usuario (safe mode se resetea a medianoche)';

-- ----------------------------------------------------------------------------
-- update_user_daily_limit()
-- Actualiza el límite diario de peticiones de un usuario
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_user_daily_limit(
    p_cognito_user_id VARCHAR(255),
    p_new_limit INTEGER
) RETURNS BOOLEAN AS $$
BEGIN
    IF p_new_limit < 0 THEN
        RAISE EXCEPTION 'Daily limit must be >= 0';
    END IF;
    
    UPDATE "bedrock-proxy-user-quotas-tbl"
    SET daily_request_limit = p_new_limit, updated_at = CURRENT_TIMESTAMP
    WHERE cognito_user_id = p_cognito_user_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'User % not found', p_cognito_user_id;
    END IF;
    
    RETURN true;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_user_daily_limit IS 'Actualiza límite diario de peticiones';

-- ----------------------------------------------------------------------------
-- get_user_quota_status()
-- Obtiene el estado actual de cuota de un usuario
-- ----------------------------------------------------------------------------
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
        q.cognito_user_id, q.cognito_email,
        COALESCE(q.daily_request_limit, 
            (SELECT config_value::INTEGER FROM "identity-manager-config-tbl" 
             WHERE config_key = 'default_daily_request_limit'), 1000) as daily_limit,
        q.requests_today,
        COALESCE(q.daily_request_limit, 
            (SELECT config_value::INTEGER FROM "identity-manager-config-tbl" 
             WHERE config_key = 'default_daily_request_limit'), 1000) - q.requests_today as remaining_requests,
        ROUND(100.0 * q.requests_today / COALESCE(q.daily_request_limit, 
            (SELECT config_value::INTEGER FROM "identity-manager-config-tbl" 
             WHERE config_key = 'default_daily_request_limit'), 1000), 2) as usage_percentage,
        q.is_blocked, q.blocked_at, q.administrative_safe, q.last_request_at
    FROM "bedrock-proxy-user-quotas-tbl" q
    WHERE q.cognito_user_id = p_cognito_user_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_user_quota_status IS 'Obtiene estado actual de cuota de un usuario';

-- ----------------------------------------------------------------------------
-- get_usage_stats()
-- Obtiene estadísticas de uso para un período específico
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_usage_stats(
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
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT,
        COUNT(CASE WHEN response_status = 'success' THEN 1 END)::BIGINT,
        COUNT(CASE WHEN response_status != 'success' THEN 1 END)::BIGINT,
        COALESCE(SUM(tokens_input), 0)::BIGINT,
        COALESCE(SUM(tokens_output), 0)::BIGINT,
        COALESCE(SUM(cost_usd), 0)::DECIMAL(10, 2),
        COALESCE(AVG(processing_time_ms), 0)::DECIMAL(10, 2),
        COUNT(DISTINCT cognito_user_id)::BIGINT
    FROM "bedrock-proxy-usage-tracking-tbl"
    WHERE request_timestamp BETWEEN p_start_date AND p_end_date
        AND (p_user_id IS NULL OR cognito_user_id = p_user_id);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_usage_stats IS 'Estadísticas de uso para un período';

-- ----------------------------------------------------------------------------
-- calculate_usage_cost()
-- Calcula el costo estimado basado en tokens y proveedor
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION calculate_usage_cost(
    p_tokens_input INTEGER,
    p_tokens_output INTEGER,
    p_model_provider VARCHAR
) RETURNS NUMERIC AS $$
DECLARE
    v_cost DECIMAL(10, 6);
    v_input_cost_per_1k DECIMAL(10, 6);
    v_output_cost_per_1k DECIMAL(10, 6);
BEGIN
    CASE p_model_provider
        WHEN 'anthropic' THEN
            v_input_cost_per_1k := 0.003;
            v_output_cost_per_1k := 0.015;
        WHEN 'amazon' THEN
            v_input_cost_per_1k := 0.0008;
            v_output_cost_per_1k := 0.0024;
        WHEN 'meta' THEN
            v_input_cost_per_1k := 0.0002;
            v_output_cost_per_1k := 0.0002;
        ELSE
            v_input_cost_per_1k := 0.001;
            v_output_cost_per_1k := 0.003;
    END CASE;
    
    v_cost := (p_tokens_input::DECIMAL / 1000 * v_input_cost_per_1k) + 
              (p_tokens_output::DECIMAL / 1000 * v_output_cost_per_1k);
    
    RETURN v_cost;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION calculate_usage_cost IS 'Calcula costo estimado por tokens y proveedor';

-- ----------------------------------------------------------------------------
-- archive_old_usage_data()
-- Archiva o elimina datos de uso antiguos
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION archive_old_usage_data(
    p_days_to_keep INTEGER DEFAULT 365
) RETURNS INTEGER AS $$
DECLARE
    v_deleted_count INTEGER;
    v_cutoff_date TIMESTAMP;
BEGIN
    v_cutoff_date := CURRENT_TIMESTAMP - (p_days_to_keep || ' days')::INTERVAL;
    
    -- Aquí se puede implementar lógica de archivo o eliminación
    -- Por ahora solo retorna 0
    v_deleted_count := 0;
    
    RETURN v_deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION archive_old_usage_data IS 'Archiva datos de uso antiguos';

-- ============================================================================
-- VISTAS
-- ============================================================================

-- ----------------------------------------------------------------------------
-- v_active_tokens
-- Tokens activos con información del perfil
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_active_tokens AS
SELECT 
    t.id as token_id, t.jti, t.cognito_user_id, t.cognito_email,
    t.issued_at, t.expires_at, t.last_used_at,
    ap.profile_name, ap.cognito_group_name,
    a.name as application_name,
    m.model_name, m.model_id, ap.model_arn
FROM "identity-manager-tokens-tbl" t
JOIN "identity-manager-profiles-tbl" ap ON t.application_profile_id = ap.id
LEFT JOIN "identity-manager-applications-tbl" a ON ap.application_id = a.id
JOIN "identity-manager-models-tbl" m ON ap.model_id = m.id
WHERE t.is_revoked = false AND t.expires_at > CURRENT_TIMESTAMP;

-- ----------------------------------------------------------------------------
-- v_user_permissions
-- Permisos consolidados de usuarios
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_user_permissions AS
SELECT 
    uap.cognito_user_id, uap.cognito_email,
    'application' as permission_scope,
    a.name as resource_name, a.id as resource_id,
    NULL::UUID as parent_application_id,
    pt.name as permission_type, pt.level as permission_level,
    uap.is_active, uap.granted_at, uap.expires_at
FROM "identity-manager-app-permissions-tbl" uap
JOIN "identity-manager-applications-tbl" a ON uap.application_id = a.id
JOIN "identity-manager-permission-types-tbl" pt ON uap.permission_type_id = pt.id
UNION ALL
SELECT 
    ump.cognito_user_id, ump.cognito_email,
    'module' as permission_scope,
    am.name as resource_name, am.id as resource_id,
    am.application_id as parent_application_id,
    pt.name as permission_type, pt.level as permission_level,
    ump.is_active, ump.granted_at, ump.expires_at
FROM "identity-manager-module-permissions-tbl" ump
JOIN "identity-manager-modules-tbl" am ON ump.application_module_id = am.id
JOIN "identity-manager-permission-types-tbl" pt ON ump.permission_type_id = pt.id;

-- ----------------------------------------------------------------------------
-- v_application_profiles
-- Perfiles con información completa
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_application_profiles AS
SELECT 
    ap.id, ap.profile_name, ap.cognito_group_name,
    a.name as application_name, a.id as application_id,
    m.model_name, m.model_id, m.provider,
    ap.model_arn, ap.is_active, ap.created_at, ap.updated_at
FROM "identity-manager-profiles-tbl" ap
LEFT JOIN "identity-manager-applications-tbl" a ON ap.application_id = a.id
JOIN "identity-manager-models-tbl" m ON ap.model_id = m.id;

-- ----------------------------------------------------------------------------
-- v_usage_by_model
-- Estadísticas agregadas por modelo
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_usage_by_model AS
SELECT 
    model_id, COUNT(*) as request_count,
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

-- ----------------------------------------------------------------------------
-- v_usage_by_team
-- Estadísticas agregadas por equipo
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_usage_by_team AS
SELECT 
    team, COUNT(*) as request_count,
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

-- ----------------------------------------------------------------------------
-- v_usage_by_person
-- Estadísticas agregadas por persona
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_usage_by_person AS
SELECT 
    person, cognito_email, team,
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

-- ----------------------------------------------------------------------------
-- v_usage_detailed
-- Vista detallada de uso
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_usage_detailed AS
SELECT 
    id, cognito_user_id, cognito_email, person, team, request_timestamp,
    model_id, source_ip, user_agent, aws_region,
    tokens_input, tokens_output, tokens_cache_read, tokens_cache_creation,
    cost_usd, processing_time_ms, response_status, error_message, created_at
FROM "bedrock-proxy-usage-tracking-tbl"
ORDER BY request_timestamp DESC;

-- ----------------------------------------------------------------------------
-- v_recent_errors
-- Últimos 100 errores
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_recent_errors AS
SELECT 
    id, cognito_user_id, cognito_email, person, team, request_timestamp,
    model_id, response_status, error_message, created_at
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE response_status != 'success'
ORDER BY request_timestamp DESC
LIMIT 100;

-- ----------------------------------------------------------------------------
-- v_users_near_limit
-- Usuarios cerca del límite (>80%)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_users_near_limit AS
SELECT 
    cognito_user_id, cognito_email, requests_today,
    COALESCE(daily_request_limit, 
        (SELECT config_value::INTEGER FROM "identity-manager-config-tbl" 
         WHERE config_key = 'default_daily_request_limit'), 1000) as daily_limit,
    (COALESCE(daily_request_limit, 
        (SELECT config_value::INTEGER FROM "identity-manager-config-tbl" 
         WHERE config_key = 'default_daily_request_limit'), 1000) - requests_today) as remaining,
    ROUND(100.0 * requests_today / COALESCE(daily_request_limit, 
        (SELECT config_value::INTEGER FROM "identity-manager-config-tbl" 
         WHERE config_key = 'default_daily_request_limit'), 1000), 2) as usage_pct
FROM "bedrock-proxy-user-quotas-tbl"
WHERE requests_today >= (COALESCE(daily_request_limit, 
        (SELECT config_value::INTEGER FROM "identity-manager-config-tbl" 
         WHERE config_key = 'default_daily_request_limit'), 1000) * 0.8)
    AND is_blocked = false AND quota_date = CURRENT_DATE
ORDER BY usage_pct DESC;

-- ----------------------------------------------------------------------------
-- v_blocked_users
-- Usuarios actualmente bloqueados
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_blocked_users AS
SELECT 
    cognito_user_id, cognito_email, requests_today,
    COALESCE(daily_request_limit, 
        (SELECT config_value::INTEGER FROM "identity-manager-config-tbl" 
         WHERE config_key = 'default_daily_request_limit'), 1000) as daily_request_limit,
    blocked_at, blocked_until, administrative_safe,
    EXTRACT(epoch FROM (CURRENT_TIMESTAMP - blocked_at)) / 3600 as hours_blocked,
    EXTRACT(epoch FROM (blocked_until - CURRENT_TIMESTAMP)) / 3600 as hours_remaining
FROM "bedrock-proxy-user-quotas-tbl"
WHERE is_blocked = true;

-- ----------------------------------------------------------------------------
-- v_quota_status
-- Estado consolidado de cuotas
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_quota_status AS
SELECT 
    cognito_user_id, cognito_email,
    COALESCE(daily_request_limit, 
        (SELECT config_value::INTEGER FROM "identity-manager-config-tbl" 
         WHERE config_key = 'default_daily_request_limit'), 1000) as daily_request_limit,
    requests_today,
    (COALESCE(daily_request_limit, 
        (SELECT config_value::INTEGER FROM "identity-manager-config-tbl" 
         WHERE config_key = 'default_daily_request_limit'), 1000) - requests_today) as remaining_requests,
    ROUND(100.0 * requests_today / COALESCE(daily_request_limit, 
        (SELECT config_value::INTEGER FROM "identity-manager-config-tbl" 
         WHERE config_key = 'default_daily_request_limit'), 1000), 2) as usage_percentage,
    is_blocked, blocked_at, blocked_until,
    administrative_safe, administrative_safe_set_by, administrative_safe_reason,
    last_request_at, quota_date
FROM "bedrock-proxy-user-quotas-tbl";

-- ----------------------------------------------------------------------------
-- v_usage_daily
-- Resumen agregado por día
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_usage_daily AS
SELECT 
    DATE(request_timestamp) as usage_date,
    COUNT(*) as total_requests,
    COUNT(DISTINCT cognito_user_id) as unique_users,
    COUNT(CASE WHEN response_status = 'success' THEN 1 END) as successful_requests,
    COUNT(CASE WHEN response_status != 'success' THEN 1 END) as failed_requests,
    SUM(tokens_input) as total_tokens_input,
    SUM(tokens_output) as total_tokens_output,
    SUM(tokens_cache_read) as total_tokens_cache_read,
    SUM(tokens_cache_creation) as total_tokens_cache_creation,
    SUM(cost_usd) as total_cost_usd,
    AVG(processing_time_ms) as avg_processing_time_ms
FROM "bedrock-proxy-usage-tracking-tbl"
GROUP BY DATE(request_timestamp)
ORDER BY usage_date DESC;

-- ----------------------------------------------------------------------------
-- v_top_users_by_cost
-- Top usuarios por costo
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_top_users_by_cost AS
SELECT 
    cognito_user_id, cognito_email,
    COUNT(*) as total_requests,
    SUM(cost_usd) as total_cost_usd,
    AVG(cost_usd) as avg_cost_per_request,
    SUM(tokens_input + tokens_output) as total_tokens
FROM "bedrock-proxy-usage-tracking-tbl"
GROUP BY cognito_user_id, cognito_email
ORDER BY total_cost_usd DESC;

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Triggers para actualizar updated_at
CREATE TRIGGER trg_models_updated_at
    BEFORE UPDATE ON "identity-manager-models-tbl"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_applications_updated_at
    BEFORE UPDATE ON "identity-manager-applications-tbl"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_modules_updated_at
    BEFORE UPDATE ON "identity-manager-modules-tbl"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_profiles_updated_at
    BEFORE UPDATE ON "identity-manager-profiles-tbl"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_config_updated_at
    BEFORE UPDATE ON "identity-manager-config-tbl"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_quotas_updated_at
    BEFORE UPDATE ON "bedrock-proxy-user-quotas-tbl"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- FIN DE FUNCIONES, VISTAS Y TRIGGERS
-- ============================================================================
