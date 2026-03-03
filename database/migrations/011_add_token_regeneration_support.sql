-- Migration 011: Add Token Regeneration Support
-- Description: Adds fields to support automatic token regeneration feature
-- Author: Identity Manager Team
-- Date: 2026-03-03

-- ============================================================================
-- 1. Add regeneration tracking fields to tokens table
-- ============================================================================

ALTER TABLE "identity-manager-tokens-tbl"
ADD COLUMN IF NOT EXISTS regenerated_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS regenerated_to_jti UUID,
ADD COLUMN IF NOT EXISTS regenerated_from_jti UUID,
ADD COLUMN IF NOT EXISTS regeneration_reason VARCHAR(100),
ADD COLUMN IF NOT EXISTS regeneration_client_ip VARCHAR(45),
ADD COLUMN IF NOT EXISTS regeneration_user_agent TEXT,
ADD COLUMN IF NOT EXISTS regeneration_email_sent BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN "identity-manager-tokens-tbl".regenerated_at IS 'Timestamp when this token was regenerated (replaced by a new one)';
COMMENT ON COLUMN "identity-manager-tokens-tbl".regenerated_to_jti IS 'JTI of the new token that replaced this one (if this token was regenerated)';
COMMENT ON COLUMN "identity-manager-tokens-tbl".regenerated_from_jti IS 'JTI of the old token that this token replaced (if this token is a regeneration)';
COMMENT ON COLUMN "identity-manager-tokens-tbl".regeneration_reason IS 'Reason for regeneration (e.g., auto_regeneration, manual)';
COMMENT ON COLUMN "identity-manager-tokens-tbl".regeneration_client_ip IS 'IP address of the client that triggered regeneration';
COMMENT ON COLUMN "identity-manager-tokens-tbl".regeneration_user_agent IS 'User agent of the client that triggered regeneration';
COMMENT ON COLUMN "identity-manager-tokens-tbl".regeneration_email_sent IS 'Whether notification email was sent successfully';

-- ============================================================================
-- 2. Create indexes for regeneration tracking
-- ============================================================================

-- Index for finding regenerated tokens (old tokens that were replaced)
CREATE INDEX IF NOT EXISTS idx_tokens_regenerated 
ON "identity-manager-tokens-tbl" (regenerated_at)
WHERE regenerated_at IS NOT NULL;

-- Index for finding tokens that are regenerations (new tokens)
CREATE INDEX IF NOT EXISTS idx_tokens_regenerated_from
ON "identity-manager-tokens-tbl" (regenerated_from_jti)
WHERE regenerated_from_jti IS NOT NULL;

-- Index for finding regeneration chains
CREATE INDEX IF NOT EXISTS idx_tokens_regenerated_to
ON "identity-manager-tokens-tbl" (regenerated_to_jti)
WHERE regenerated_to_jti IS NOT NULL;

COMMENT ON INDEX idx_tokens_regenerated IS 'Index for quickly finding tokens that were regenerated (old tokens)';
COMMENT ON INDEX idx_tokens_regenerated_from IS 'Index for finding tokens that are regenerations of other tokens (new tokens)';
COMMENT ON INDEX idx_tokens_regenerated_to IS 'Index for finding the new token that replaced an old one';

-- ============================================================================
-- 3. Grant permissions
-- ============================================================================

-- Grant permissions to application user (adjust username as needed)
-- GRANT SELECT, INSERT, UPDATE ON "identity-manager-tokens-tbl" TO identity_manager_app;

-- ============================================================================
-- Migration complete
-- ============================================================================

-- Verify migration
DO $$
BEGIN
    -- Check if columns were added
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'identity-manager-tokens-tbl' 
        AND column_name = 'regenerated_at'
    ) THEN
        RAISE NOTICE 'Migration 011: regenerated_at column added successfully';
    END IF;
    
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'identity-manager-tokens-tbl' 
        AND column_name = 'regenerated_from_jti'
    ) THEN
        RAISE NOTICE 'Migration 011: regenerated_from_jti column added successfully';
    END IF;
    
    RAISE NOTICE 'Migration 011 completed successfully';
    RAISE NOTICE 'All regeneration data will be stored in identity-manager-tokens-tbl';
END $$;