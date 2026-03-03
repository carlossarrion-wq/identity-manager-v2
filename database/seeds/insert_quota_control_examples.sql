-- =====================================================
-- SEED DATA: Daily Quota Control Examples
-- =====================================================
-- Purpose: Insert example quota data for testing
-- Version: 1.0
-- Date: 2026-03-02
-- =====================================================

-- Note: This script assumes you have existing users in Cognito

-- =====================================================
-- EJEMPLO 1: Usuario con límite por defecto (1000)
-- =====================================================
INSERT INTO "bedrock-proxy-user-quotas-tbl" (
    cognito_user_id,
    cognito_email,
    daily_request_limit,  -- NULL = usar default de config
    current_date,
    requests_today,
    is_blocked,
    administrative_safe
) VALUES (
    'us-east-1_user001',
    'user001@example.com',
    NULL,  -- Usará el límite por defecto (1000)
    CURRENT_DATE,
    250,
    false,
    false
);

-- =====================================================
-- EJEMPLO 2: Usuario cerca del límite (80%)
-- =====================================================
INSERT INTO "bedrock-proxy-user-quotas-tbl" (
    cognito_user_id,
    cognito_email,
    daily_request_limit,
    current_date,
    requests_today,
    is_blocked,
    administrative_safe
) VALUES (
    'us-east-1_user002',
    'user002@example.com',
    1000,
    CURRENT_DATE,
    850,  -- 85% del límite
    false,
    false
);

-- =====================================================
-- EJEMPLO 3: Usuario bloqueado
-- =====================================================
INSERT INTO "bedrock-proxy-user-quotas-tbl" (
    cognito_user_id,
    cognito_email,
    daily_request_limit,
    current_date,
    requests_today,
    is_blocked,
    blocked_at,
    administrative_safe
) VALUES (
    'us-east-1_user003',
    'user003@example.com',
    1000,
    CURRENT_DATE,
    1000,  -- Alcanzó el límite
    true,
    CURRENT_TIMESTAMP - INTERVAL '2 hours',
    false
);

-- Registrar en historial
INSERT INTO "bedrock-proxy-quota-blocks-history-tbl" (
    cognito_user_id,
    cognito_email,
    block_date,
    blocked_at,
    requests_count,
    daily_limit
) VALUES (
    'us-east-1_user003',
    'user003@example.com',
    CURRENT_DATE,
    CURRENT_TIMESTAMP - INTERVAL '2 hours',
    1000,
    1000
);

-- =====================================================
-- EJEMPLO 4: Usuario con límite personalizado alto
-- =====================================================
INSERT INTO "bedrock-proxy-user-quotas-tbl" (
    cognito_user_id,
    cognito_email,
    daily_request_limit,
    current_date,
    requests_today,
    is_blocked,
    administrative_safe
) VALUES (
    'us-east-1_premium001',
    'premium001@example.com',
    10000,  -- Usuario premium con límite alto
    CURRENT_DATE,
    3500,
    false,
    false
);

-- =====================================================
-- EJEMPLO 5: Usuario desbloqueado administrativamente
-- =====================================================
INSERT INTO "bedrock-proxy-user-quotas-tbl" (
    cognito_user_id,
    cognito_email,
    daily_request_limit,
    current_date,
    requests_today,
    is_blocked,
    blocked_at,
    administrative_safe,
    administrative_safe_set_by,
    administrative_safe_set_at,
    administrative_safe_reason
) VALUES (
    'us-east-1_user004',
    'user004@example.com',
    1000,
    CURRENT_DATE,
    1050,  -- Superó el límite
    false,  -- Desbloqueado
    CURRENT_TIMESTAMP - INTERVAL '1 hour',
    true,  -- Flag administrativo activo
    'admin@example.com',
    CURRENT_TIMESTAMP - INTERVAL '30 minutes',
    'Usuario necesita completar tarea urgente'
);

-- Registrar bloqueo y desbloqueo en historial
INSERT INTO "bedrock-proxy-quota-blocks-history-tbl" (
    cognito_user_id,
    cognito_email,
    block_date,
    blocked_at,
    unblocked_at,
    unblock_type,
    requests_count,
    daily_limit,
    unblocked_by,
    unblock_reason
) VALUES (
    'us-east-1_user004',
    'user004@example.com',
    CURRENT_DATE,
    CURRENT_TIMESTAMP - INTERVAL '1 hour',
    CURRENT_TIMESTAMP - INTERVAL '30 minutes',
    'administrative',
    1050,
    1000,
    'admin@example.com',
    'Usuario necesita completar tarea urgente'
);

-- =====================================================
-- EJEMPLO 6: Usuario con límite bajo (testing)
-- =====================================================
INSERT INTO "bedrock-proxy-user-quotas-tbl" (
    cognito_user_id,
    cognito_email,
    daily_request_limit,
    current_date,
    requests_today,
    is_blocked,
    administrative_safe
) VALUES (
    'us-east-1_testuser',
    'testuser@example.com',
    100,  -- Límite bajo para testing
    CURRENT_DATE,
    45,
    false,
    false
);

-- =====================================================
-- CONSULTAS DE VERIFICACIÓN
-- =====================================================

-- Ver todos los usuarios con sus cuotas
-- SELECT * FROM "v_quota_status" ORDER BY usage_percentage DESC;

-- Ver usuarios bloqueados
-- SELECT * FROM "v_blocked_users";

-- Ver usuarios cerca del límite
-- SELECT * FROM "v_users_near_limit";

-- Ver historial de bloqueos
-- SELECT * FROM "bedrock-proxy-quota-blocks-history-tbl" ORDER BY blocked_at DESC;

-- =====================================================
-- EJEMPLOS DE USO DE FUNCIONES
-- =====================================================

-- Verificar cuota de un usuario
-- SELECT * FROM check_and_update_quota('us-east-1_user001', 'user001@example.com');

-- Obtener estado de cuota de un usuario
-- SELECT * FROM get_user_quota_status('us-east-1_user002');

-- Desbloquear usuario administrativamente
-- SELECT administrative_unblock_user(
--     'us-east-1_user003',
--     'admin@example.com',
--     'Desbloqueo por solicitud urgente'
-- );

-- Actualizar límite diario de un usuario
-- SELECT update_user_daily_limit('us-east-1_user001', 2000);

-- =====================================================
-- ESCENARIOS DE PRUEBA
-- =====================================================

-- Escenario 1: Simular múltiples peticiones hasta bloqueo
/*
DO $$
DECLARE
    i INTEGER;
    result RECORD;
BEGIN
    FOR i IN 1..1005 LOOP
        SELECT * INTO result FROM check_and_update_quota(
            'us-east-1_testuser',
            'testuser@example.com'
        );
        
        IF NOT result.allowed THEN
            RAISE NOTICE 'Usuario bloqueado en petición %: %', i, result.block_reason;
            EXIT;
        END IF;
    END LOOP;
END $$;
*/

-- Escenario 2: Verificar reset automático al cambiar de día
/*
-- Simular cambio de día
UPDATE "bedrock-proxy-user-quotas-tbl"
SET current_date = CURRENT_DATE - INTERVAL '1 day'
WHERE cognito_user_id = 'us-east-1_testuser';

-- Hacer una petición (debería resetear)
SELECT * FROM check_and_update_quota('us-east-1_testuser', 'testuser@example.com');

-- Verificar que se reseteó
SELECT * FROM get_user_quota_status('us-east-1_testuser');
*/

-- Escenario 3: Verificar que administrative_safe se resetea con nuevo día
/*
-- Establecer flag administrativo
SELECT administrative_unblock_user(
    'us-east-1_user003',
    'admin@example.com',
    'Test de reset automático'
);

-- Simular cambio de día
UPDATE "bedrock-proxy-user-quotas-tbl"
SET current_date = CURRENT_DATE - INTERVAL '1 day'
WHERE cognito_user_id = 'us-east-1_user003';

-- Hacer una petición (debería resetear administrative_safe)
SELECT * FROM check_and_update_quota('us-east-1_user003', 'user003@example.com');

-- Verificar que administrative_safe es false
SELECT administrative_safe FROM "bedrock-proxy-user-quotas-tbl"
WHERE cognito_user_id = 'us-east-1_user003';
*/

-- =====================================================
-- END OF SEED DATA
-- =====================================================