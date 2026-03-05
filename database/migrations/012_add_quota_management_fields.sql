-- ============================================================================
-- MIGRATION 012: Add Quota Management Fields
-- ============================================================================
-- Date: 2026-03-05
-- Description: Añade campos para tracking de bloqueos/desbloqueos manuales
--              en la tabla bedrock-proxy-user-quotas-tbl
-- ============================================================================

-- Añadir campos para tracking de bloqueos manuales
ALTER TABLE "bedrock-proxy-user-quotas-tbl" 
ADD COLUMN IF NOT EXISTS blocked_by VARCHAR(255),
ADD COLUMN IF NOT EXISTS block_reason TEXT,
ADD COLUMN IF NOT EXISTS unblocked_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS unblocked_by VARCHAR(255),
ADD COLUMN IF NOT EXISTS unblock_reason TEXT;

-- Comentarios para documentación
COMMENT ON COLUMN "bedrock-proxy-user-quotas-tbl".blocked_by IS 'Email del administrador que bloqueó al usuario';
COMMENT ON COLUMN "bedrock-proxy-user-quotas-tbl".block_reason IS 'Razón del bloqueo manual';
COMMENT ON COLUMN "bedrock-proxy-user-quotas-tbl".unblocked_at IS 'Timestamp del último desbloqueo';
COMMENT ON COLUMN "bedrock-proxy-user-quotas-tbl".unblocked_by IS 'Email del administrador que desbloqueó';
COMMENT ON COLUMN "bedrock-proxy-user-quotas-tbl".unblock_reason IS 'Razón del desbloqueo';

-- Verificar que los campos se añadieron correctamente
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'bedrock-proxy-user-quotas-tbl'
  AND column_name IN ('blocked_by', 'block_reason', 'unblocked_at', 'unblocked_by', 'unblock_reason')
ORDER BY ordinal_position;

-- ============================================================================
-- FIN DE MIGRACIÓN
-- ============================================================================