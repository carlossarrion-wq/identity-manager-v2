-- =====================================================
-- INSERT PROFILE: LCS SDLC Gen - Cline - Claude Sonnet 4.5
-- =====================================================
-- Fecha: 2026-02-28
-- Inference Profile ARN: arn:aws:bedrock:eu-west-1:701055077130:application-inference-profile/invmw8994b4y
-- Inference Profile Name: lcs-claude_sonnet_4_5-sdlc-gen-cline-profile
-- =====================================================

-- =====================================================
-- 1. INSERTAR MODELO SI NO EXISTE
-- =====================================================
INSERT INTO "identity-manager-models-tbl" (
    model_id, 
    model_name, 
    model_arn, 
    provider, 
    description,
    is_active
) VALUES (
    'eu.anthropic.claude-sonnet-4-5-20250929-v1:0',
    'Claude Sonnet 4.5 (EU) - 2025-09-29',
    'arn:aws:bedrock:eu-west-1::foundation-model/eu.anthropic.claude-sonnet-4-5-20250929-v1:0',
    'Anthropic',
    'Modelo Claude Sonnet 4.5 versión 2025-09-29 - Región EU para cumplimiento GDPR',
    true
)
ON CONFLICT (model_id) DO UPDATE SET
    model_name = EXCLUDED.model_name,
    model_arn = EXCLUDED.model_arn,
    description = EXCLUDED.description,
    updated_at = CURRENT_TIMESTAMP;

-- =====================================================
-- 2. INSERTAR APLICACIÓN CLINE SI NO EXISTE
-- =====================================================
INSERT INTO "identity-manager-applications-tbl" (
    name, 
    description, 
    is_active,
    display_order
) VALUES (
    'cline',
    'Asistente de desarrollo con IA - Generación y revisión de código',
    true,
    1
)
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    updated_at = CURRENT_TIMESTAMP;

-- =====================================================
-- 3. INSERTAR PERFIL DE APLICACIÓN
-- =====================================================
DO $$
DECLARE
    v_app_id UUID;
    v_model_id UUID;
    v_profile_id UUID;
BEGIN
    -- Obtener ID de la aplicación Cline
    SELECT id INTO v_app_id 
    FROM "identity-manager-applications-tbl" 
    WHERE name = 'cline';
    
    -- Obtener ID del modelo
    SELECT id INTO v_model_id 
    FROM "identity-manager-models-tbl" 
    WHERE model_id = 'eu.anthropic.claude-sonnet-4-5-20250929-v1:0';
    
    -- Verificar que ambos existen
    IF v_app_id IS NULL THEN
        RAISE EXCEPTION 'Aplicación "cline" no encontrada';
    END IF;
    
    IF v_model_id IS NULL THEN
        RAISE EXCEPTION 'Modelo "eu.anthropic.claude-sonnet-4-5-20250929-v1:0" no encontrado';
    END IF;
    
    -- Insertar o actualizar el perfil
    INSERT INTO "identity-manager-profiles-tbl" (
        profile_name,
        cognito_group_name,
        application_id,
        model_id,
        model_arn,
        description,
        is_active
    ) VALUES (
        'lcs-claude_sonnet_4_5-sdlc-gen-cline-profile',
        'lcs-sdlc-gen-group',
        v_app_id,
        v_model_id,
        'arn:aws:bedrock:eu-west-1:701055077130:application-inference-profile/invmw8994b4y',
        'Perfil de inferencia para el equipo LCS SDLC Gen usando Cline con Claude Sonnet 4.5',
        true
    )
    ON CONFLICT (cognito_group_name, application_id, model_id) 
    DO UPDATE SET
        profile_name = EXCLUDED.profile_name,
        model_arn = EXCLUDED.model_arn,
        description = EXCLUDED.description,
        is_active = EXCLUDED.is_active,
        updated_at = CURRENT_TIMESTAMP
    RETURNING id INTO v_profile_id;
    
    -- Mostrar resultado
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'PERFIL INSERTADO/ACTUALIZADO CORRECTAMENTE';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Profile ID: %', v_profile_id;
    RAISE NOTICE 'Profile Name: lcs-claude_sonnet_4_5-sdlc-gen-cline-profile';
    RAISE NOTICE 'Cognito Group: lcs-sdlc-gen-group';
    RAISE NOTICE 'Application: cline (ID: %)', v_app_id;
    RAISE NOTICE 'Model: Claude Sonnet 4.5 (ID: %)', v_model_id;
    RAISE NOTICE 'Inference Profile ARN: arn:aws:bedrock:eu-west-1:701055077130:application-inference-profile/invmw8994b4y';
    RAISE NOTICE '==============================================';
    
END $$;

-- =====================================================
-- 4. VERIFICACIÓN
-- =====================================================
-- Mostrar el perfil creado
SELECT 
    p.id,
    p.profile_name,
    p.cognito_group_name,
    a.name as application_name,
    m.model_name,
    m.model_id,
    p.model_arn,
    p.is_active,
    p.created_at,
    p.updated_at
FROM "identity-manager-profiles-tbl" p
LEFT JOIN "identity-manager-applications-tbl" a ON p.application_id = a.id
JOIN "identity-manager-models-tbl" m ON p.model_id = m.id
WHERE p.profile_name = 'lcs-claude_sonnet_4_5-sdlc-gen-cline-profile';

-- =====================================================
-- COMANDOS ÚTILES
-- =====================================================

-- Para ejecutar este script desde la EC2:
-- psql -h identity-manager-dev-rds.czuimyk2qu10.eu-west-1.rds.amazonaws.com \
--      -p 5432 \
--      -U dbadmin \
--      -d identity_manager_dev_rds \
--      -f insert_lcs_cline_profile.sql

-- Para verificar el perfil:
-- SELECT * FROM "v_application_profiles" 
-- WHERE profile_name = 'lcs-claude_sonnet_4_5-sdlc-gen-cline-profile';

-- =====================================================
-- END OF SCRIPT
-- =====================================================
