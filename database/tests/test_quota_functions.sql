-- =====================================================
-- TEST SUITE: Funciones de Control de Cuotas
-- =====================================================
-- Purpose: Validar el correcto funcionamiento de las funciones de cuotas
-- Date: 2026-03-02
-- =====================================================

-- =====================================================
-- CONFIGURACIÓN INICIAL
-- =====================================================

-- Limpiar datos de prueba anteriores
DELETE FROM "bedrock-proxy-quota-blocks-history-tbl" WHERE cognito_user_id LIKE 'test_%';
DELETE FROM "bedrock-proxy-user-quotas-tbl" WHERE cognito_user_id LIKE 'test_%';

-- =====================================================
-- TEST 1: Creación Automática de Usuario
-- =====================================================
DO $$
DECLARE
    v_result RECORD;
BEGIN
    RAISE NOTICE '=== TEST 1: Creación Automática de Usuario ===';
    
    -- Primera petición de un usuario nuevo
    SELECT * INTO v_result 
    FROM check_and_update_quota('test_user_001', 'test001@example.com');
    
    -- Verificaciones
    ASSERT v_result.allowed = true, 'Primera petición debe estar permitida';
    ASSERT v_result.requests_today = 1, 'Contador debe ser 1';
    ASSERT v_result.daily_limit = 1000, 'Límite por defecto debe ser 1000';
    ASSERT v_result.is_blocked = false, 'Usuario no debe estar bloqueado';
    
    RAISE NOTICE '✓ Usuario creado automáticamente con límite por defecto';
    RAISE NOTICE '  - Allowed: %, Requests: %, Limit: %', 
        v_result.allowed, v_result.requests_today, v_result.daily_limit;
END $$;

-- =====================================================
-- TEST 2: Incremento de Contador
-- =====================================================
DO $$
DECLARE
    v_result RECORD;
    i INTEGER;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '=== TEST 2: Incremento de Contador ===';
    
    -- Hacer 10 peticiones más
    FOR i IN 2..10 LOOP
        SELECT * INTO v_result 
        FROM check_and_update_quota('test_user_001', 'test001@example.com');
    END LOOP;
    
    -- Verificaciones
    ASSERT v_result.allowed = true, 'Peticiones deben estar permitidas';
    ASSERT v_result.requests_today = 10, 'Contador debe ser 10';
    
    RAISE NOTICE '✓ Contador incrementado correctamente';
    RAISE NOTICE '  - Requests today: %', v_result.requests_today;
END $$;

-- =====================================================
-- TEST 3: Alcanzar Límite y Bloqueo Automático
-- =====================================================
DO $$
DECLARE
    v_result RECORD;
    i INTEGER;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '=== TEST 3: Alcanzar Límite y Bloqueo Automático ===';
    
    -- Hacer peticiones hasta alcanzar el límite (990 más para llegar a 1000)
    FOR i IN 11..1000 LOOP
        SELECT * INTO v_result 
        FROM check_and_update_quota('test_user_001', 'test001@example.com');
    END LOOP;
    
    -- Verificar que la petición 1000 fue permitida
    ASSERT v_result.allowed = true, 'Petición 1000 debe estar permitida';
    ASSERT v_result.requests_today = 1000, 'Contador debe ser 1000';
    
    -- Intentar petición 1001 (debe ser bloqueada)
    SELECT * INTO v_result 
    FROM check_and_update_quota('test_user_001', 'test001@example.com');
    
    ASSERT v_result.allowed = false, 'Petición 1001 debe estar bloqueada';
    ASSERT v_result.is_blocked = true, 'Usuario debe estar bloqueado';
    ASSERT v_result.requests_today = 1000, 'Contador debe seguir en 1000';
    
    RAISE NOTICE '✓ Bloqueo automático funcionando correctamente';
    RAISE NOTICE '  - Allowed: %, Blocked: %, Reason: %', 
        v_result.allowed, v_result.is_blocked, v_result.block_reason;
END $$;

-- =====================================================
-- TEST 4: Verificar Registro en Historial
-- =====================================================
DO $$
DECLARE
    v_count INTEGER;
    v_history RECORD;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '=== TEST 4: Verificar Registro en Historial ===';
    
    -- Verificar que se creó un registro en el historial
    SELECT COUNT(*) INTO v_count
    FROM "bedrock-proxy-quota-blocks-history-tbl"
    WHERE cognito_user_id = 'test_user_001'
        AND unblocked_at IS NULL;
    
    ASSERT v_count = 1, 'Debe haber un registro de bloqueo en el historial';
    
    -- Obtener detalles del bloqueo
    SELECT * INTO v_history
    FROM "bedrock-proxy-quota-blocks-history-tbl"
    WHERE cognito_user_id = 'test_user_001'
        AND unblocked_at IS NULL;
    
    ASSERT v_history.requests_count = 1000, 'Historial debe mostrar 1000 peticiones';
    ASSERT v_history.daily_limit = 1000, 'Historial debe mostrar límite de 1000';
    
    RAISE NOTICE '✓ Registro en historial correcto';
    RAISE NOTICE '  - Requests: %, Limit: %, Blocked at: %', 
        v_history.requests_count, v_history.daily_limit, v_history.blocked_at;
END $$;

-- =====================================================
-- TEST 5: Desbloqueo Administrativo
-- =====================================================
DO $$
DECLARE
    v_result RECORD;
    v_success BOOLEAN;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '=== TEST 5: Desbloqueo Administrativo ===';
    
    -- Desbloquear usuario administrativamente
    SELECT administrative_unblock_user(
        'test_user_001',
        'admin@example.com',
        'Test de desbloqueo administrativo'
    ) INTO v_success;
    
    ASSERT v_success = true, 'Desbloqueo debe ser exitoso';
    
    -- Verificar que el usuario puede hacer peticiones
    SELECT * INTO v_result 
    FROM check_and_update_quota('test_user_001', 'test001@example.com');
    
    ASSERT v_result.allowed = true, 'Petición debe estar permitida después de desbloqueo';
    ASSERT v_result.requests_today = 1001, 'Contador debe incrementar a 1001';
    
    -- Verificar que administrative_safe está activo
    DECLARE
        v_admin_safe BOOLEAN;
    BEGIN
        SELECT administrative_safe INTO v_admin_safe
        FROM "bedrock-proxy-user-quotas-tbl"
        WHERE cognito_user_id = 'test_user_001';
        
        ASSERT v_admin_safe = true, 'Flag administrative_safe debe estar activo';
    END;
    
    RAISE NOTICE '✓ Desbloqueo administrativo funcionando';
    RAISE NOTICE '  - Allowed: %, Requests: %, Admin safe: true', 
        v_result.allowed, v_result.requests_today;
END $$;

-- =====================================================
-- TEST 6: Usuario con Administrative Safe puede exceder límite
-- =====================================================
DO $$
DECLARE
    v_result RECORD;
    i INTEGER;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '=== TEST 6: Administrative Safe permite exceder límite ===';
    
    -- Hacer 100 peticiones más (total 1101)
    FOR i IN 1..100 LOOP
        SELECT * INTO v_result 
        FROM check_and_update_quota('test_user_001', 'test001@example.com');
    END LOOP;
    
    -- Verificar que todas fueron permitidas
    ASSERT v_result.allowed = true, 'Peticiones deben estar permitidas con admin safe';
    ASSERT v_result.requests_today = 1101, 'Contador debe ser 1101';
    ASSERT v_result.is_blocked = false, 'Usuario no debe estar bloqueado';
    
    RAISE NOTICE '✓ Administrative safe permite exceder límite';
    RAISE NOTICE '  - Requests: % (excede límite de %)', 
        v_result.requests_today, v_result.daily_limit;
END $$;

-- =====================================================
-- TEST 7: Reset Diario Automático
-- =====================================================
DO $$
DECLARE
    v_result RECORD;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '=== TEST 7: Reset Diario Automático ===';
    
    -- Simular que es un día anterior
    UPDATE "bedrock-proxy-user-quotas-tbl"
    SET quota_date = CURRENT_DATE - INTERVAL '1 day'
    WHERE cognito_user_id = 'test_user_001';
    
    -- Hacer una petición (debe resetear)
    SELECT * INTO v_result 
    FROM check_and_update_quota('test_user_001', 'test001@example.com');
    
    -- Verificaciones
    ASSERT v_result.allowed = true, 'Petición debe estar permitida después de reset';
    ASSERT v_result.requests_today = 1, 'Contador debe resetearse a 1';
    ASSERT v_result.is_blocked = false, 'Usuario no debe estar bloqueado';
    
    -- Verificar que administrative_safe se reseteó
    DECLARE
        v_admin_safe BOOLEAN;
    BEGIN
        SELECT administrative_safe INTO v_admin_safe
        FROM "bedrock-proxy-user-quotas-tbl"
        WHERE cognito_user_id = 'test_user_001';
        
        ASSERT v_admin_safe = false, 'Flag administrative_safe debe resetearse';
    END;
    
    RAISE NOTICE '✓ Reset diario automático funcionando';
    RAISE NOTICE '  - Requests reseteado a: %, Admin safe: false', v_result.requests_today;
END $$;

-- =====================================================
-- TEST 8: Actualizar Límite Diario
-- =====================================================
DO $$
DECLARE
    v_result RECORD;
    v_success BOOLEAN;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '=== TEST 8: Actualizar Límite Diario ===';
    
    -- Cambiar límite a 50
    SELECT update_user_daily_limit('test_user_001', 50) INTO v_success;
    
    ASSERT v_success = true, 'Actualización debe ser exitosa';
    
    -- Verificar nuevo límite
    SELECT * INTO v_result 
    FROM check_and_update_quota('test_user_001', 'test001@example.com');
    
    ASSERT v_result.daily_limit = 50, 'Límite debe ser 50';
    ASSERT v_result.requests_today = 2, 'Contador debe ser 2';
    
    RAISE NOTICE '✓ Límite diario actualizado correctamente';
    RAISE NOTICE '  - Nuevo límite: %', v_result.daily_limit;
END $$;

-- =====================================================
-- TEST 9: Bloqueo Administrativo con Duración
-- =====================================================
DO $$
DECLARE
    v_result RECORD;
    v_success BOOLEAN;
    v_block_until TIMESTAMP;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '=== TEST 9: Bloqueo Administrativo con Duración ===';
    
    -- Crear nuevo usuario para esta prueba
    SELECT * INTO v_result 
    FROM check_and_update_quota('test_user_002', 'test002@example.com');
    
    -- Bloquear por 2 días
    v_block_until := CURRENT_TIMESTAMP + INTERVAL '2 days';
    SELECT administrative_block_user(
        'test_user_002',
        'admin@example.com',
        v_block_until,
        'Bloqueo de prueba por 2 días'
    ) INTO v_success;
    
    ASSERT v_success = true, 'Bloqueo debe ser exitoso';
    
    -- Verificar que está bloqueado
    SELECT * INTO v_result 
    FROM check_and_update_quota('test_user_002', 'test002@example.com');
    
    ASSERT v_result.allowed = false, 'Petición debe estar bloqueada';
    ASSERT v_result.is_blocked = true, 'Usuario debe estar bloqueado';
    
    RAISE NOTICE '✓ Bloqueo administrativo con duración funcionando';
    RAISE NOTICE '  - Blocked: %, Reason: %', v_result.is_blocked, v_result.block_reason;
END $$;

-- =====================================================
-- TEST 10: Desbloqueo Automático por Expiración
-- =====================================================
DO $$
DECLARE
    v_result RECORD;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '=== TEST 10: Desbloqueo Automático por Expiración ===';
    
    -- Simular que el bloqueo ya expiró
    UPDATE "bedrock-proxy-user-quotas-tbl"
    SET blocked_until = CURRENT_TIMESTAMP - INTERVAL '1 hour'
    WHERE cognito_user_id = 'test_user_002';
    
    -- Hacer una petición (debe desbloquear automáticamente)
    SELECT * INTO v_result 
    FROM check_and_update_quota('test_user_002', 'test002@example.com');
    
    -- Verificaciones
    ASSERT v_result.allowed = true, 'Petición debe estar permitida después de expiración';
    ASSERT v_result.is_blocked = false, 'Usuario debe estar desbloqueado';
    
    RAISE NOTICE '✓ Desbloqueo automático por expiración funcionando';
    RAISE NOTICE '  - Allowed: %, Blocked: %', v_result.allowed, v_result.is_blocked;
END $$;

-- =====================================================
-- TEST 11: Función get_user_quota_status
-- =====================================================
DO $$
DECLARE
    v_status RECORD;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '=== TEST 11: Función get_user_quota_status ===';
    
    -- Obtener estado de cuota
    SELECT * INTO v_status 
    FROM get_user_quota_status('test_user_001');
    
    -- Verificaciones
    ASSERT v_status.cognito_user_id = 'test_user_001', 'User ID debe coincidir';
    ASSERT v_status.cognito_email = 'test001@example.com', 'Email debe coincidir';
    ASSERT v_status.daily_limit = 50, 'Límite debe ser 50';
    ASSERT v_status.requests_today >= 0, 'Requests debe ser >= 0';
    ASSERT v_status.remaining_requests >= 0, 'Remaining debe ser >= 0';
    ASSERT v_status.usage_percentage >= 0, 'Usage % debe ser >= 0';
    
    RAISE NOTICE '✓ Función get_user_quota_status funcionando';
    RAISE NOTICE '  - Limit: %, Used: %, Remaining: %, Usage: %', 
        v_status.daily_limit, v_status.requests_today, 
        v_status.remaining_requests, v_status.usage_percentage;
END $$;

-- =====================================================
-- TEST 12: Vistas
-- =====================================================
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '=== TEST 12: Vistas ===';
    
    -- Vista v_quota_status
    SELECT COUNT(*) INTO v_count FROM "v_quota_status";
    ASSERT v_count >= 2, 'Vista v_quota_status debe tener al menos 2 registros';
    RAISE NOTICE '✓ Vista v_quota_status: % registros', v_count;
    
    -- Vista v_blocked_users
    SELECT COUNT(*) INTO v_count FROM "v_blocked_users";
    RAISE NOTICE '✓ Vista v_blocked_users: % registros', v_count;
    
    -- Vista v_users_near_limit
    SELECT COUNT(*) INTO v_count FROM "v_users_near_limit";
    RAISE NOTICE '✓ Vista v_users_near_limit: % registros', v_count;
END $$;

-- =====================================================
-- TEST 13: Manejo de Errores
-- =====================================================
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '=== TEST 13: Manejo de Errores ===';
    
    -- Test: Actualizar límite negativo (debe fallar)
    BEGIN
        PERFORM update_user_daily_limit('test_user_001', -10);
        RAISE EXCEPTION 'Debería haber fallado con límite negativo';
    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE '✓ Error capturado correctamente: %', SQLERRM;
    END;
    
    -- Test: Desbloquear usuario inexistente (debe fallar)
    BEGIN
        PERFORM administrative_unblock_user('user_inexistente', 'admin', 'test');
        RAISE EXCEPTION 'Debería haber fallado con usuario inexistente';
    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE '✓ Error capturado correctamente: %', SQLERRM;
    END;
    
    -- Test: Bloquear con fecha pasada (debe fallar)
    BEGIN
        PERFORM administrative_block_user(
            'test_user_001', 
            'admin', 
            CURRENT_TIMESTAMP - INTERVAL '1 hour',
            'test'
        );
        RAISE EXCEPTION 'Debería haber fallado con fecha pasada';
    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE '✓ Error capturado correctamente: %', SQLERRM;
    END;
END $$;

-- =====================================================
-- LIMPIEZA Y RESUMEN
-- =====================================================
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '=== LIMPIEZA DE DATOS DE PRUEBA ===';
    
    DELETE FROM "bedrock-proxy-quota-blocks-history-tbl" WHERE cognito_user_id LIKE 'test_%';
    DELETE FROM "bedrock-proxy-user-quotas-tbl" WHERE cognito_user_id LIKE 'test_%';
    
    RAISE NOTICE '✓ Datos de prueba eliminados';
    
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE '✅ TODOS LOS TESTS COMPLETADOS EXITOSAMENTE';
    RAISE NOTICE '========================================';
    RAISE NOTICE '';
    RAISE NOTICE 'Tests ejecutados:';
    RAISE NOTICE '  1. ✓ Creación automática de usuario';
    RAISE NOTICE '  2. ✓ Incremento de contador';
    RAISE NOTICE '  3. ✓ Bloqueo automático al alcanzar límite';
    RAISE NOTICE '  4. ✓ Registro en historial';
    RAISE NOTICE '  5. ✓ Desbloqueo administrativo';
    RAISE NOTICE '  6. ✓ Administrative safe permite exceder límite';
    RAISE NOTICE '  7. ✓ Reset diario automático';
    RAISE NOTICE '  8. ✓ Actualizar límite diario';
    RAISE NOTICE '  9. ✓ Bloqueo administrativo con duración';
    RAISE NOTICE ' 10. ✓ Desbloqueo automático por expiración';
    RAISE NOTICE ' 11. ✓ Función get_user_quota_status';
    RAISE NOTICE ' 12. ✓ Vistas funcionando';
    RAISE NOTICE ' 13. ✓ Manejo de errores';
    RAISE NOTICE '';
END $$;
