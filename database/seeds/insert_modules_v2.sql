-- =====================================================
-- INSERT APPLICATION MODULES DATA
-- =====================================================
-- Insertar módulos de aplicaciones
-- Tabla: identity-manager-modules-tbl
-- =====================================================

-- Módulos de kb-agent
INSERT INTO "identity-manager-modules-tbl" (application_id, name, description, display_order, is_active) 
VALUES
    ((SELECT id FROM "identity-manager-applications-tbl" WHERE name = 'kb-agent'), 'chat', 'Módulo de chat interactivo con el agente de conocimiento', 1, true),
    ((SELECT id FROM "identity-manager-applications-tbl" WHERE name = 'kb-agent'), 'document-management', 'Módulo para gestionar documentos del agente de conocimiento', 2, true)
ON CONFLICT (application_id, name) DO UPDATE SET
    description = EXCLUDED.description,
    display_order = EXCLUDED.display_order,
    is_active = EXCLUDED.is_active,
    updated_at = CURRENT_TIMESTAMP;

-- Verificar los módulos insertados
SELECT 
    am.id,
    a.name as application_name,
    am.name as module_name,
    am.description,
    am.display_order,
    am.is_active,
    am.created_at
FROM "identity-manager-modules-tbl" am
JOIN "identity-manager-applications-tbl" a ON am.application_id = a.id
WHERE a.name = 'kb-agent'
ORDER BY am.display_order;
