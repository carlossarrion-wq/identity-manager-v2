-- =====================================================
-- DROP ALL TABLES - IDENTITY MANAGER
-- =====================================================
-- Purpose: Eliminar todas las tablas, vistas y funciones
-- Version: 1.0
-- Date: 2026-02-27
-- 
-- ADVERTENCIA: Este script eliminará TODOS los datos
-- =====================================================

-- Eliminar vistas primero (para evitar dependencias)
DROP VIEW IF EXISTS v_user_permissions CASCADE;
DROP VIEW IF EXISTS v_active_tokens CASCADE;
DROP VIEW IF EXISTS v_application_profiles CASCADE;

-- Eliminar tablas en orden correcto (respetando foreign keys)
DROP TABLE IF EXISTS "identity-manager-tokens-tbl" CASCADE;
DROP TABLE IF EXISTS "identity-manager-module-permissions-tbl" CASCADE;
DROP TABLE IF EXISTS "identity-manager-app-permissions-tbl" CASCADE;
DROP TABLE IF EXISTS "identity-manager-profiles-tbl" CASCADE;
DROP TABLE IF EXISTS "identity-manager-modules-tbl" CASCADE;
DROP TABLE IF EXISTS "identity-manager-applications-tbl" CASCADE;
DROP TABLE IF EXISTS "identity-manager-models-tbl" CASCADE;
DROP TABLE IF EXISTS "identity-manager-permission-types-tbl" CASCADE;
DROP TABLE IF EXISTS "identity-manager-config-tbl" CASCADE;
DROP TABLE IF EXISTS "identity-manager-audit-tbl" CASCADE;

-- Eliminar función
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

-- Mensaje de confirmación
SELECT 'Todas las tablas, vistas y funciones eliminadas correctamente' as status;

-- =====================================================
-- END OF DROP SCRIPT
-- =====================================================
