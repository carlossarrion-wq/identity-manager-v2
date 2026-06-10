-- ============================================================================
-- Migration: Fix Unknown Team in Tracking Table
-- ============================================================================
-- Description: Update team='unknown' records in bedrock-proxy-usage-tracking-tbl
--              using the correct team from other records of the same user
-- Date: 2026-06-09
-- Author: Cline
-- ============================================================================

-- PASO 1: Verificar el estado actual
-- ============================================================================
-- Ver cuántos registros tienen team='unknown' por usuario
SELECT 
    cognito_email,
    COUNT(*) FILTER (WHERE team = 'unknown') as unknown_count,
    COUNT(*) FILTER (WHERE team != 'unknown') as known_count,
    COUNT(*) as total_count
FROM "bedrock-proxy-usage-tracking-tbl"
GROUP BY cognito_email
HAVING COUNT(*) FILTER (WHERE team = 'unknown') > 0
ORDER BY unknown_count DESC;

-- PASO 2: Crear tabla temporal con el team correcto por usuario
-- ============================================================================
-- Esta tabla mapea cada cognito_user_id a su team correcto
-- (tomando el team más frecuente que no sea 'unknown')
CREATE TEMP TABLE temp_user_correct_team AS
SELECT 
    cognito_user_id,
    cognito_email,
    team as correct_team,
    COUNT(*) as usage_count
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE team != 'unknown'
  AND team IS NOT NULL
  AND team != ''
GROUP BY cognito_user_id, cognito_email, team
ORDER BY cognito_user_id, usage_count DESC;

-- Verificar la tabla temporal
SELECT * FROM temp_user_correct_team LIMIT 10;

-- PASO 3: Crear índice para optimizar el UPDATE
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_temp_user_team 
ON temp_user_correct_team(cognito_user_id);

-- PASO 4: UPDATE - Corregir team='unknown' usando el team correcto
-- ============================================================================
-- Esta query actualiza los registros con team='unknown' usando el team
-- correcto del mismo usuario obtenido de otros registros

-- IMPORTANTE: Ejecutar en transacción para poder hacer rollback si es necesario
BEGIN;

-- Actualizar registros con team='unknown'
UPDATE "bedrock-proxy-usage-tracking-tbl" AS tracking
SET 
    team = correct.correct_team,
    person = COALESCE(tracking.person, '')  -- Mantener person si existe
FROM (
    -- Subconsulta: obtener el team más usado por cada usuario (excluyendo 'unknown')
    SELECT DISTINCT ON (cognito_user_id)
        cognito_user_id,
        team as correct_team
    FROM "bedrock-proxy-usage-tracking-tbl"
    WHERE team != 'unknown'
      AND team IS NOT NULL
      AND team != ''
    ORDER BY cognito_user_id, request_timestamp DESC
) AS correct
WHERE tracking.cognito_user_id = correct.cognito_user_id
  AND tracking.team = 'unknown';

-- Verificar cuántos registros se actualizaron
SELECT 
    'Registros actualizados' as descripcion,
    COUNT(*) as cantidad
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE team != 'unknown';

-- PASO 5: Verificar el resultado
-- ============================================================================
-- Ver el estado después del update
SELECT 
    cognito_email,
    COUNT(*) FILTER (WHERE team = 'unknown') as unknown_count,
    COUNT(*) FILTER (WHERE team != 'unknown') as known_count,
    COUNT(*) as total_count
FROM "bedrock-proxy-usage-tracking-tbl"
GROUP BY cognito_email
HAVING COUNT(*) FILTER (WHERE team = 'unknown') > 0
ORDER BY unknown_count DESC;

-- Si todo está correcto, hacer COMMIT
-- Si algo salió mal, hacer ROLLBACK
COMMIT;
-- ROLLBACK;  -- Descomentar si necesitas revertir

-- PASO 6: Limpiar tabla temporal
-- ============================================================================
DROP TABLE IF EXISTS temp_user_correct_team;

-- ============================================================================
-- QUERIES DE VERIFICACIÓN POST-MIGRACIÓN
-- ============================================================================

-- 1. Contar registros con team='unknown' restantes
SELECT 
    COUNT(*) as registros_con_unknown,
    COUNT(*) * 100.0 / (SELECT COUNT(*) FROM "bedrock-proxy-usage-tracking-tbl") as porcentaje
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE team = 'unknown';

-- 2. Ver distribución de teams después de la migración
SELECT 
    team,
    COUNT(*) as cantidad,
    COUNT(*) * 100.0 / (SELECT COUNT(*) FROM "bedrock-proxy-usage-tracking-tbl") as porcentaje
FROM "bedrock-proxy-usage-tracking-tbl"
GROUP BY team
ORDER BY cantidad DESC;

-- 3. Ver usuarios que aún tienen registros con team='unknown'
-- (estos son usuarios que NUNCA tuvieron un registro con team válido)
SELECT 
    cognito_email,
    cognito_user_id,
    COUNT(*) as registros_unknown,
    MIN(request_timestamp) as primer_registro,
    MAX(request_timestamp) as ultimo_registro
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE team = 'unknown'
GROUP BY cognito_email, cognito_user_id
ORDER BY registros_unknown DESC;

-- ============================================================================
-- NOTAS IMPORTANTES
-- ============================================================================
-- 
-- 1. Esta migración solo puede corregir registros de usuarios que tienen
--    AL MENOS UN registro con team válido (diferente de 'unknown')
--
-- 2. Usuarios que SOLO tienen registros con team='unknown' NO se pueden
--    corregir con esta query. Para esos casos, necesitarás:
--    - Obtener el team de Cognito (grupos del usuario)
--    - O asignar manualmente el team correcto
--
-- 3. La query usa el team más reciente del usuario (ORDER BY request_timestamp DESC)
--    Si prefieres usar el team más frecuente, cambia a:
--    ORDER BY cognito_user_id, COUNT(*) DESC
--
-- 4. SIEMPRE ejecuta primero las queries de verificación (PASO 1)
--    antes de hacer el UPDATE
--
-- 5. El UPDATE está dentro de una transacción (BEGIN/COMMIT)
--    para poder hacer ROLLBACK si algo sale mal
--
-- ============================================================================

-- ============================================================================
-- QUERY ALTERNATIVA: Usar el team más frecuente en lugar del más reciente
-- ============================================================================
/*
UPDATE "bedrock-proxy-usage-tracking-tbl" AS tracking
SET 
    team = correct.correct_team,
    person = COALESCE(tracking.person, '')
FROM (
    SELECT 
        cognito_user_id,
        team as correct_team,
        COUNT(*) as frequency
    FROM "bedrock-proxy-usage-tracking-tbl"
    WHERE team != 'unknown'
      AND team IS NOT NULL
      AND team != ''
    GROUP BY cognito_user_id, team
    ORDER BY cognito_user_id, frequency DESC
    LIMIT 1
) AS correct
WHERE tracking.cognito_user_id = correct.cognito_user_id
  AND tracking.team = 'unknown';
*/

-- ============================================================================
-- BACKUP RECOMENDADO
-- ============================================================================
-- Antes de ejecutar esta migración, se recomienda hacer un backup:
-- 
-- pg_dump -h your-host -U your-user -d identity_manager \
--   -t "bedrock-proxy-usage-tracking-tbl" \
--   > backup_tracking_table_$(date +%Y%m%d_%H%M%S).sql
--
-- ============================================================================