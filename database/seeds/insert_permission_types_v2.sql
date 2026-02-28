-- =====================================================
-- INSERT PERMISSION TYPES DATA
-- =====================================================
-- Insertar tipos de permisos predefinidos
-- Tabla: identity-manager-permission-types-tbl
-- =====================================================

INSERT INTO "identity-manager-permission-types-tbl" (name, description, level) VALUES
    ('Read-only', 'Solo lectura, sin capacidad de modificación', 10),
    ('Write', 'Lectura y escritura, puede modificar datos', 50),
    ('Admin', 'Administrador con control total', 100)
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    level = EXCLUDED.level;

-- Verificar los tipos de permisos insertados
SELECT id, name, description, level, created_at 
FROM "identity-manager-permission-types-tbl"
ORDER BY level;
