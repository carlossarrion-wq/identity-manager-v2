# Migration 015: Fix Unknown Team in Tracking Table

## Objetivo

Corregir los registros históricos en `bedrock-proxy-usage-tracking-tbl` que tienen `team='unknown'` utilizando el team correcto del mismo usuario obtenido de otros registros.

## Problema

Debido a un bug en la regeneración automática de tokens, muchos registros en la tabla de tracking tienen `team='unknown'` cuando deberían tener el team real del usuario.

## Solución

Esta migración actualiza los registros con `team='unknown'` usando el team correcto del mismo usuario obtenido de otros registros donde el team sí está poblado correctamente.

## Cómo Funciona

1. **Identifica usuarios afectados**: Encuentra usuarios que tienen registros con `team='unknown'`
2. **Obtiene team correcto**: Para cada usuario, obtiene el team más reciente de sus registros válidos
3. **Actualiza registros**: Actualiza todos los registros con `team='unknown'` de ese usuario

## Limitaciones

⚠️ **IMPORTANTE**: Esta migración solo puede corregir registros de usuarios que tienen **AL MENOS UN registro con team válido**.

Usuarios que **SOLO** tienen registros con `team='unknown'` NO se pueden corregir automáticamente. Para esos casos necesitarás:
- Obtener el team de Cognito (grupos del usuario)
- O asignar manualmente el team correcto

## Pasos de Ejecución

### 1. Backup (OBLIGATORIO)

```bash
# Hacer backup de la tabla antes de la migración
pg_dump -h your-rds-endpoint.amazonaws.com \
  -U admin \
  -d identity_manager \
  -t "bedrock-proxy-usage-tracking-tbl" \
  > backup_tracking_table_$(date +%Y%m%d_%H%M%S).sql
```

### 2. Verificación Pre-Migración

```sql
-- Ver cuántos registros tienen team='unknown'
SELECT 
    COUNT(*) as total_unknown,
    COUNT(*) * 100.0 / (SELECT COUNT(*) FROM "bedrock-proxy-usage-tracking-tbl") as porcentaje
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE team = 'unknown';

-- Ver usuarios afectados
SELECT 
    cognito_email,
    COUNT(*) FILTER (WHERE team = 'unknown') as unknown_count,
    COUNT(*) FILTER (WHERE team != 'unknown') as known_count
FROM "bedrock-proxy-usage-tracking-tbl"
GROUP BY cognito_email
HAVING COUNT(*) FILTER (WHERE team = 'unknown') > 0
ORDER BY unknown_count DESC;
```

### 3. Ejecutar Migración

```bash
# Conectar a la base de datos
psql -h your-rds-endpoint.amazonaws.com \
  -U admin \
  -d identity_manager \
  -f database/migrations/015_fix_unknown_team_in_tracking.sql
```

O ejecutar manualmente las queries del archivo.

### 4. Verificación Post-Migración

```sql
-- Verificar que se redujeron los registros con 'unknown'
SELECT 
    COUNT(*) as registros_con_unknown,
    COUNT(*) * 100.0 / (SELECT COUNT(*) FROM "bedrock-proxy-usage-tracking-tbl") as porcentaje
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE team = 'unknown';

-- Ver distribución de teams
SELECT 
    team,
    COUNT(*) as cantidad,
    COUNT(*) * 100.0 / (SELECT COUNT(*) FROM "bedrock-proxy-usage-tracking-tbl") as porcentaje
FROM "bedrock-proxy-usage-tracking-tbl"
GROUP BY team
ORDER BY cantidad DESC;
```

## Rollback

Si algo sale mal durante la migración:

```sql
-- Si aún estás en la transacción
ROLLBACK;

-- Si ya hiciste COMMIT, restaurar desde backup
psql -h your-rds-endpoint.amazonaws.com \
  -U admin \
  -d identity_manager \
  < backup_tracking_table_YYYYMMDD_HHMMSS.sql
```

## Resultados Esperados

### Antes de la Migración
```
team='unknown': 15,234 registros (45%)
team='lcs-sdlc-gen-group': 10,123 registros (30%)
team='other-team': 8,456 registros (25%)
```

### Después de la Migración
```
team='unknown': 234 registros (0.7%)  ← Solo usuarios sin registros válidos
team='lcs-sdlc-gen-group': 18,123 registros (54%)
team='other-team': 15,456 registros (45%)
```

## Casos Especiales

### Usuarios que Cambiaron de Team

Si un usuario cambió de team durante el período de tracking:
- La migración usará el team **más reciente** por defecto
- Si prefieres usar el team **más frecuente**, usa la query alternativa en el archivo de migración

### Usuarios Solo con 'unknown'

Para usuarios que SOLO tienen registros con `team='unknown'`:

```sql
-- Identificar estos usuarios
SELECT 
    cognito_email,
    cognito_user_id,
    COUNT(*) as total_registros
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE cognito_user_id NOT IN (
    SELECT DISTINCT cognito_user_id 
    FROM "bedrock-proxy-usage-tracking-tbl" 
    WHERE team != 'unknown'
)
GROUP BY cognito_email, cognito_user_id
ORDER BY total_registros DESC;

-- Para estos usuarios, necesitarás obtener el team de Cognito
-- o asignarlo manualmente
```

## Monitoreo Post-Migración

```sql
-- Monitorear nuevos registros para verificar que el fix funciona
SELECT 
    DATE(request_timestamp) as date,
    COUNT(*) FILTER (WHERE team = 'unknown') as unknown_count,
    COUNT(*) FILTER (WHERE team != 'unknown') as known_count,
    COUNT(*) FILTER (WHERE team = 'unknown') * 100.0 / COUNT(*) as unknown_percentage
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE request_timestamp > NOW() - INTERVAL '7 days'
GROUP BY DATE(request_timestamp)
ORDER BY date DESC;
```

## Notas Adicionales

1. **Performance**: La migración puede tardar varios minutos dependiendo del tamaño de la tabla
2. **Índices**: La migración crea índices temporales para optimizar el UPDATE
3. **Transaccional**: Todo el UPDATE está en una transacción para poder hacer rollback
4. **Idempotente**: Puedes ejecutar la migración múltiples veces sin problemas

## Relacionado

- `docs/22-TOKEN-REGENERATION-BUG-FIX.md` - Documentación del bug original
- `CHANGELOG-TOKEN-REGENERATION-FIX.md` - Changelog del fix implementado
- `backend/shared/services/cognito_service.py` - Fix en código

---
**Fecha**: 2026-06-09
**Autor**: Cline
**Estado**: Listo para ejecutar