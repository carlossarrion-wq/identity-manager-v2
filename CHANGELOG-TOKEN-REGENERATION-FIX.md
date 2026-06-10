# Token Regeneration Fix - Changelog

## Date: 2026-06-09

## Problem
Los tokens regenerados automáticamente perdían la información de `team` y `person`, resultando en:
- `team: "unknown"` en lugar del grupo real del usuario
- `person: ""` en lugar del nombre de la persona

## Root Cause
El método `cognito_service.get_user()` no obtenía los grupos del usuario de Cognito, causando que `user_info['groups']` estuviera vacío durante la regeneración de tokens.

## Solution Implemented

### 1. Modified `backend/shared/services/cognito_service.py`

**Método**: `get_user()`

**Cambio**: Añadida obtención de grupos del usuario mediante `admin_list_groups_for_user()`

```python
# Obtener grupos del usuario
try:
    groups_response = self.client.admin_list_groups_for_user(
        UserPoolId=self.user_pool_id,
        Username=username
    )
    user['groups'] = [g['GroupName'] for g in groups_response.get('Groups', [])]
    logger.info(f"User {username} has groups: {user['groups']}")
except ClientError as e:
    logger.warning(f"Could not fetch groups for user {username}: {e}")
    user['groups'] = []
```

### 2. Modified `backend/shared/services/jwt_service.py`

**Método**: `generate_token()`

**Cambio**: Añadido logging para debugging y mejor manejo de variables

```python
# Obtener primer grupo del usuario (team)
groups = user_info.get('groups', [])
team = groups[0] if groups else 'unknown'
person = user_info.get('person', '')

# Log para debugging
logger.info(f"Generating token - user_id: {user_info['user_id']}, "
            f"groups: {groups}, team: {team}, person: {person}")
```

## Files Modified

1. `backend/shared/services/cognito_service.py` - Líneas ~300-330
2. `backend/shared/services/jwt_service.py` - Líneas ~98-120

## Testing Required

### Test 1: Verificar get_user() incluye grupos
```python
from services.cognito_service import CognitoService

cognito_service = CognitoService()
user_info = cognito_service.get_user('test@example.com')

assert 'groups' in user_info
assert len(user_info['groups']) > 0
print(f"✓ User has groups: {user_info['groups']}")
```

### Test 2: Regenerar token y verificar
```python
from services.token_regeneration_service import TokenRegenerationService
import jwt

service = TokenRegenerationService(db, cognito, email)
result = service.regenerate_expired_token(
    expired_token_jti='old-jti',
    user_id='user-id'
)

payload = jwt.decode(result['new_token'], options={"verify_signature": False})
assert payload['team'] != 'unknown'
assert payload['person'] != ''
print(f"✓ Token has team: {payload['team']}, person: {payload['person']}")
```

### Test 3: Verificar en base de datos
```sql
-- Verificar que nuevos registros tienen team correcto
SELECT 
    cognito_email,
    team,
    person,
    COUNT(*) as count
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE request_timestamp > NOW() - INTERVAL '1 hour'
  AND team != 'unknown'
GROUP BY cognito_email, team, person;
```

## Deployment Steps

1. **Backup**: Crear backup de los archivos modificados
2. **Deploy**: Desplegar cambios en Lambda functions
3. **Monitor**: Verificar logs de CloudWatch para confirmar:
   - Logs de "User X has groups: [...]"
   - Logs de "Generating token - ... team: X, person: Y"
4. **Verify**: Ejecutar queries de verificación en base de datos

## Expected Impact

### Immediate
- ✅ Nuevos tokens regenerados tendrán `team` y `person` correctos
- ✅ Logs mostrarán información de grupos y team durante generación

### Long-term
- ✅ Reducción de registros con `team: "unknown"` en base de datos
- ✅ Mejor trazabilidad de uso por equipo
- ✅ Datos más precisos para análisis y reportes

### No Impact
- ⚠️ Registros históricos con `team: "unknown"` permanecerán sin cambios
- ⚠️ Tokens existentes mantendrán sus valores hasta que expiren y se regeneren

## Rollback Plan

Si se detectan problemas:

1. Revertir cambios en `cognito_service.py`:
```python
# Remover el bloque de obtención de grupos
user = self._format_user(response)
return user  # Sin obtener grupos
```

2. Revertir cambios en `jwt_service.py`:
```python
# Volver a código original
team = user_info.get('groups', ['unknown'])[0] if user_info.get('groups') else 'unknown'
```

3. Redesplegar versión anterior

## Monitoring

### CloudWatch Logs to Watch
- `"User X has groups:"` - Confirmar que se obtienen grupos
- `"Generating token - ... team:"` - Verificar team correcto
- `"Could not fetch groups"` - Alertar si hay errores

### Database Queries
```sql
-- Monitorear ratio de unknown vs known
SELECT 
    DATE(request_timestamp) as date,
    COUNT(*) FILTER (WHERE team = 'unknown') * 100.0 / COUNT(*) as unknown_percentage
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE request_timestamp > NOW() - INTERVAL '7 days'
GROUP BY DATE(request_timestamp)
ORDER BY date DESC;
```

## Related Documentation
- `docs/22-TOKEN-REGENERATION-BUG-FIX.md` - Análisis detallado del bug
- `docs/20-TEAM-FIELD-UNKNOWN-ANALYSIS.md` - Análisis inicial del problema
- `docs/21-TOKEN-GENERATION-TEAM-UNKNOWN-FIX.md` - Primera investigación

---
**Status**: ✅ Implemented
**Reviewed by**: Pending
**Deployed to**: Pending