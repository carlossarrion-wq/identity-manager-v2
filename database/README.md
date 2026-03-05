# Database Scripts

Esquema y datos de Identity Manager v2 - PostgreSQL 15+

## 📁 Estructura

```
database/
├── README.md                    # Este archivo
├── 01_schema.sql               # DDL: Tablas, índices, constraints
├── 02_functions_views.sql      # Funciones PL/pgSQL, vistas y triggers
├── 03_seed_data.sql            # Datos iniciales (models, apps, config)
└── schema/
    └── EXTRACTED_FULL_SCHEMA.sql  # Esquema completo extraído de BD
```

## 🚀 Instalación Completa

Para crear una nueva base de datos desde cero:

```bash
# 1. Crear esquema (tablas, índices)
psql -h <host> -U <user> -d <database> -f 01_schema.sql

# 2. Crear funciones, vistas y triggers
psql -h <host> -U <user> -d <database> -f 02_functions_views.sql

# 3. Insertar datos iniciales
psql -h <host> -U <user> -d <database> -f 03_seed_data.sql
```

### Ejemplo con variables de entorno

```bash
export PGHOST="identity-manager-dev-rds.czuimyk2qu10.eu-west-1.rds.amazonaws.com"
export PGPORT="5432"
export PGUSER="dbadmin"
export PGDATABASE="identity_manager_dev_rds"
export PGPASSWORD="your-password"

psql -f 01_schema.sql
psql -f 02_functions_views.sql
psql -f 03_seed_data.sql
```

## 📊 Contenido de los Scripts

### 01_schema.sql
- **13 tablas principales:**
  - Identity Manager (10): models, applications, modules, profiles, tokens, permission-types, app-permissions, module-permissions, config, audit
  - Proxy Bedrock (3): usage-tracking, user-quotas, quota-blocks-history
- **40+ índices** optimizados para consultas frecuentes
- **Constraints** y foreign keys
- **Comentarios** en tablas y columnas

### 02_functions_views.sql
- **9 funciones PL/pgSQL:**
  - `check_and_update_quota()` - Control de cuotas con bloqueo automático
  - `administrative_block_user()` - Bloqueo administrativo
  - `administrative_unblock_user()` - Desbloqueo con safe mode
  - `update_user_daily_limit()` - Actualizar límites
  - `get_user_quota_status()` - Estado de cuota
  - `get_usage_stats()` - Estadísticas de uso
  - `calculate_usage_cost()` - Cálculo de costos
  - `archive_old_usage_data()` - Archivado de datos
  - `update_updated_at_column()` - Trigger function

- **13 vistas:**
  - `v_active_tokens` - Tokens activos
  - `v_user_permissions` - Permisos consolidados
  - `v_application_profiles` - Perfiles completos
  - `v_usage_by_model` - Uso por modelo
  - `v_usage_by_team` - Uso por equipo
  - `v_usage_by_person` - Uso por persona
  - `v_usage_detailed` - Detalle completo
  - `v_recent_errors` - Últimos errores
  - `v_users_near_limit` - Usuarios cerca del límite
  - `v_blocked_users` - Usuarios bloqueados
  - `v_quota_status` - Estado de cuotas
  - `v_usage_daily` - Resumen diario
  - `v_top_users_by_cost` - Top usuarios por costo

- **6 triggers** para actualizar `updated_at` automáticamente

### 03_seed_data.sql
- **4 modelos LLM** (Claude 3.5 Sonnet, Haiku, Claude 4.5)
- **9 aplicaciones** (cline, bedrock-proxy, kb-agent, etc.)
- **3 tipos de permisos** (read, write, admin)
- **12 parámetros de configuración**

## 🔧 Operaciones Comunes

### Verificar instalación

```sql
-- Contar tablas
SELECT COUNT(*) FROM information_schema.tables 
WHERE table_schema = 'public';

-- Verificar funciones
SELECT routine_name FROM information_schema.routines 
WHERE routine_schema = 'public' AND routine_type = 'FUNCTION';

-- Verificar vistas
SELECT table_name FROM information_schema.views 
WHERE table_schema = 'public';

-- Verificar datos iniciales
SELECT COUNT(*) FROM "identity-manager-models-tbl";
SELECT COUNT(*) FROM "identity-manager-applications-tbl";
SELECT COUNT(*) FROM "identity-manager-config-tbl";
```

### Backup y Restore

```bash
# Backup completo
pg_dump -h <host> -U <user> -d <database> \
  --schema=public --no-owner --no-privileges \
  > backup_$(date +%Y%m%d).sql

# Restore
psql -h <host> -U <user> -d <database> < backup_20260305.sql
```

### Extraer esquema actualizado

```bash
# Solo DDL (sin datos)
pg_dump -h <host> -U <user> -d <database> \
  --schema-only --no-owner --no-privileges --schema=public \
  > schema/EXTRACTED_FULL_SCHEMA.sql
```

## 📝 Notas Importantes

1. **Orden de ejecución:** Los scripts deben ejecutarse en orden (01, 02, 03)
2. **Idempotencia:** Los scripts usan `IF NOT EXISTS` y `ON CONFLICT` para ser re-ejecutables
3. **UUIDs:** Todas las tablas usan UUIDs como primary keys
4. **Timestamps:** Los campos `created_at` y `updated_at` se gestionan automáticamente
5. **Extensiones requeridas:** `uuid-ossp` y `pgcrypto`

## 🔗 Referencias

- [Documentación de Base de Datos](../docs/07-DATABASE.md)
- [Arquitectura del Sistema](../docs/02-ARCHITECTURE.md)
- [Guía de Instalación](../docs/03-INSTALLATION.md)

## 📅 Historial de Versiones

- **v5.0** (2026-03-05): Esquema consolidado con DDL extraído de BD
- **v4.x**: Migraciones 009-012 (team, person, regeneration, last_used_at)
- **v3.x**: Esquema base con UUIDs