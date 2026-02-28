-- =====================================================
-- INSERT APPLICATIONS DATA
-- =====================================================
-- Insertar aplicaciones del sistema con sus descripciones
-- Tabla: identity-manager-applications-tbl
-- =====================================================

INSERT INTO "identity-manager-applications-tbl" (name, description, display_order, is_active) VALUES
    ('kb-agent', 'Agente de Conocimiento', 1, true),
    ('bedrock-proxy', 'Proxy Bedrock', 2, true),
    ('capacity-mgmt', 'Gestor de Capacidad', 3, true),
    ('identity-mgmt', 'Gestor de Identidades', 4, true),
    ('bedrock-dashboard', 'Control de Uso Bedrock', 5, true),
    ('kb-agent-dashboard', 'Control de Uso Knowledge Base', 6, true),
    ('test-planner', 'Planificador de Pruebas', 7, true),
    ('user-mgmt-tools', 'Herramientas de línea de comandos para gestión de usuarios', 8, true),
    ('cline', 'Agente de codificación Cline', 9, true)
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    display_order = EXCLUDED.display_order,
    updated_at = CURRENT_TIMESTAMP;

-- Verificar las aplicaciones insertadas
SELECT id, name, description, display_order, is_active, created_at 
FROM "identity-manager-applications-tbl"
ORDER BY display_order;
