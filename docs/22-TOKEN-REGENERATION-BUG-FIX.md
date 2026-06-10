# Token Regeneration Bug - Team/Person Fields Lost

## Problem Identified

**Tokens iniciales**: ✅ Funcionan correctamente
```json
{
  "team": "lcs-sdlc-gen-group",  // ✓ Correcto
  "person": "c.s.",               // ✓ Correcto
}
```

**Tokens regenerados automáticamente**: ❌ Pierden información
```json
{
  "team": "unknown",  // ❌ Se pierde
  "person": "",       // ❌ Se pierde
}
```

## Root Cause Analysis

### Código del Servicio de Regeneración

**Archivo**: `backend/lambdas/identity-mgmt-api/services/token_regeneration_service.py`

```python
def regenerate_expired_token(
    self,
    expired_token_jti: str,
    user_id: str,
    client_ip: str = None,
    user_agent: str = None
) -> Dict[str, Any]:
    """
    Regenerar un token expirado automáticamente
    """
    # 1. Obtener información del token expirado
    old_token = self.database_service.get_token_by_jti(expired_token_jti)
    
    # 2. Obtener información del usuario de Cognito
    user_info = self.cognito_service.get_user(user_id)  # ← AQUÍ ESTÁ EL PROBLEMA
    
    # 3. Obtener perfil de inferencia
    profile_info = self.database_service.get_profile(old_token['application_profile_id'])
    
    # 4. Generar nuevo token
    token_data = self.jwt_service.generate_token(
        user_info=user_info,      # ← user_info NO tiene 'groups' poblado
        profile_info=profile_info,
        validity_period=old_token.get('validity_period', '90_days')
    )
```

### El Problema

El método `cognito_service.get_user(user_id)` **NO incluye los grupos del usuario** en el `user_info` que retorna.

Veamos el código de `get_user`:

```python
def get_user(self, username: str) -> Dict[str, Any]:
    """Obtener información de un usuario específico"""
    try:
        response = self.client.admin_get_user(
            UserPoolId=self.user_pool_id,
            Username=username
        )
        
        user = self._format_user(response)
        
        # ❌ PROBLEMA: NO se obtienen los grupos aquí
        # Los grupos solo se obtienen en list_users() con batch fetching
        
        return user
```

Cuando se llama a `get_user()`, el usuario retornado tiene:
- ✅ `user_id`
- ✅ `email`
- ✅ `person` (de `custom:person`)
- ❌ `groups` = [] (vacío)
- ❌ `team` = '' (vacío, porque no hay `custom:team`)

Luego, en `jwt_service.generate_token()`:

```python
# Línea 102 de jwt_service.py
team = user_info.get('groups', ['unknown'])[0] if user_info.get('groups') else 'unknown'
```

Como `user_info['groups']` está vacío, se asigna `team = 'unknown'`.

## Solution

### Opción 1: Obtener Grupos en get_user() (Recomendado)

Modificar `cognito_service.py` para que `get_user()` también obtenga los grupos:

```python
def get_user(self, username: str) -> Dict[str, Any]:
    """Obtener información de un usuario específico"""
    try:
        response = self.client.admin_get_user(
            UserPoolId=self.user_pool_id,
            Username=username
        )
        
        user = self._format_user(response)
        
        # ✓ AÑADIR: Obtener grupos del usuario
        try:
            groups_response = self.client.admin_list_groups_for_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )
            user['groups'] = [g['GroupName'] for g in groups_response.get('Groups', [])]
        except ClientError as e:
            logger.warning(f"Could not fetch groups for user {username}: {e}")
            user['groups'] = []
        
        return user
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'UserNotFoundException':
            raise ValueError(f'Usuario no encontrado: {username}')
        logger.error(f"Error obteniendo usuario: {e}")
        raise Exception(f"Error de Cognito: {e.response['Error']['Message']}")
```

### Opción 2: Usar Información del Token Viejo

Modificar `token_regeneration_service.py` para reutilizar team/person del token expirado:

```python
def regenerate_expired_token(
    self,
    expired_token_jti: str,
    user_id: str,
    client_ip: str = None,
    user_agent: str = None
) -> Dict[str, Any]:
    """
    Regenerar un token expirado automáticamente
    """
    # 1. Obtener información del token expirado
    old_token = self.database_service.get_token_by_jti(expired_token_jti)
    
    # 2. Decodificar el token viejo para obtener team/person
    old_jwt = old_token.get('jwt_token')  # Si está almacenado
    if old_jwt:
        old_payload = jwt.decode(old_jwt, options={"verify_signature": False})
        old_team = old_payload.get('team', 'unknown')
        old_person = old_payload.get('person', '')
    else:
        old_team = 'unknown'
        old_person = ''
    
    # 3. Obtener información del usuario de Cognito
    user_info = self.cognito_service.get_user(user_id)
    
    # ✓ AÑADIR: Preservar team y person del token viejo si no están en user_info
    if not user_info.get('groups'):
        user_info['groups'] = [old_team] if old_team != 'unknown' else []
    if not user_info.get('person'):
        user_info['person'] = old_person
    
    # 4. Obtener perfil de inferencia
    profile_info = self.database_service.get_profile(old_token['application_profile_id'])
    
    # 5. Generar nuevo token
    token_data = self.jwt_service.generate_token(
        user_info=user_info,
        profile_info=profile_info,
        validity_period=old_token.get('validity_period', '90_days')
    )
```

### Opción 3: Almacenar Team/Person en Base de Datos

Añadir campos `team` y `person` a la tabla de tokens para preservarlos:

```sql
ALTER TABLE "identity-manager-jwt-tokens-tbl" 
ADD COLUMN team VARCHAR(255),
ADD COLUMN person VARCHAR(255);
```

Luego en `token_regeneration_service.py`:

```python
def regenerate_expired_token(...):
    # Obtener token viejo
    old_token = self.database_service.get_token_by_jti(expired_token_jti)
    
    # Obtener user_info
    user_info = self.cognito_service.get_user(user_id)
    
    # ✓ Usar team/person almacenados en BD
    if old_token.get('team'):
        user_info['groups'] = [old_token['team']]
    if old_token.get('person'):
        user_info['person'] = old_token['person']
    
    # Generar nuevo token...
```

## Recommended Fix (Opción 1 - Más Simple)

### Step 1: Modificar cognito_service.py

```python
def get_user(self, username: str) -> Dict[str, Any]:
    """
    Obtener información de un usuario específico
    
    Args:
        username: Username o email del usuario
        
    Returns:
        Dict con información del usuario incluyendo grupos
    """
    try:
        response = self.client.admin_get_user(
            UserPoolId=self.user_pool_id,
            Username=username
        )
        
        user = self._format_user(response)
        
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
        
        return user
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'UserNotFoundException':
            raise ValueError(f'Usuario no encontrado: {username}')
        logger.error(f"Error obteniendo usuario: {e}")
        raise Exception(f"Error de Cognito: {e.response['Error']['Message']}")
```

### Step 2: Añadir Logging en jwt_service.py

Para debugging, añadir logs:

```python
def generate_token(
    self,
    user_info: Dict[str, Any],
    profile_info: Dict[str, Any],
    validity_period: str = '90_days',
    audiences: list = None
) -> Dict[str, Any]:
    # ...
    
    # Obtener primer grupo del usuario (team)
    groups = user_info.get('groups', [])
    team = groups[0] if groups else 'unknown'
    person = user_info.get('person', '')
    
    # Log para debugging
    logger.info(f"Generating token - user_id: {user_info['user_id']}, "
                f"groups: {groups}, team: {team}, person: {person}")
    
    # Construir payload del JWT según especificación
    payload = {
        'user_id': user_info['user_id'],
        'email': user_info['email'],
        'default_inference_profile': str(profile_info['profile_id']),
        'team': team,
        'person': person,
        # ...
    }
```

## Testing

### Test 1: Verificar get_user() incluye grupos

```python
from services.cognito_service import CognitoService

cognito_service = CognitoService()
user_info = cognito_service.get_user('csarrion@gmail.com')

print(f"User ID: {user_info['user_id']}")
print(f"Email: {user_info['email']}")
print(f"Groups: {user_info.get('groups', [])}")
print(f"Person: {user_info.get('person', '')}")
```

**Resultado esperado**:
```
User ID: 22454414-00f1-7014-cbd4-2b37c6c678b8
Email: csarrion@gmail.com
Groups: ['lcs-sdlc-gen-group']
Person: c.s.
```

### Test 2: Regenerar Token y Verificar

```python
from services.token_regeneration_service import TokenRegenerationService

service = TokenRegenerationService(database_service, cognito_service, email_service)

result = service.regenerate_expired_token(
    expired_token_jti='old-jti-here',
    user_id='22454414-00f1-7014-cbd4-2b37c6c678b8'
)

# Decodificar nuevo token
import jwt
new_payload = jwt.decode(result['new_token'], options={"verify_signature": False})

print(f"New token team: {new_payload.get('team')}")
print(f"New token person: {new_payload.get('person')}")
```

**Resultado esperado**:
```
New token team: lcs-sdlc-gen-group
New token person: c.s.
```

### Test 3: Verificar en Base de Datos

```sql
-- Verificar registros después de regeneración
SELECT 
    cognito_email,
    team,
    person,
    request_timestamp,
    COUNT(*) as count
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE cognito_email = 'csarrion@gmail.com'
  AND request_timestamp > NOW() - INTERVAL '1 hour'
GROUP BY cognito_email, team, person, request_timestamp
ORDER BY request_timestamp DESC;
```

## Implementation Steps

1. **Modificar `backend/shared/services/cognito_service.py`**
   - Añadir obtención de grupos en método `get_user()`

2. **Añadir logging en `backend/shared/services/jwt_service.py`**
   - Para verificar que team/person se están generando correctamente

3. **Testing**
   - Probar `get_user()` para verificar que incluye grupos
   - Forzar regeneración de un token y verificar payload
   - Verificar registros en base de datos

4. **Deploy**
   - Desplegar cambios en Lambda
   - Monitorear logs para verificar corrección

## Verification Queries

```sql
-- Contar tokens con team unknown por usuario
SELECT 
    cognito_email,
    COUNT(*) FILTER (WHERE team = 'unknown') as unknown_count,
    COUNT(*) FILTER (WHERE team != 'unknown') as known_count,
    COUNT(*) as total
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE request_timestamp > NOW() - INTERVAL '7 days'
GROUP BY cognito_email
HAVING COUNT(*) FILTER (WHERE team = 'unknown') > 0
ORDER BY unknown_count DESC;

-- Ver evolución temporal
SELECT 
    DATE(request_timestamp) as date,
    COUNT(*) FILTER (WHERE team = 'unknown') as unknown_count,
    COUNT(*) FILTER (WHERE team != 'unknown') as known_count
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE request_timestamp > NOW() - INTERVAL '30 days'
GROUP BY DATE(request_timestamp)
ORDER BY date DESC;
```

## Conclusion

**Root Cause**: El método `cognito_service.get_user()` NO obtiene los grupos del usuario, causando que los tokens regenerados tengan `team: "unknown"`.

**Solution**: Modificar `get_user()` para que también obtenga los grupos del usuario mediante `admin_list_groups_for_user()`.

**Impact**: 
- ✅ Tokens iniciales: Ya funcionan correctamente
- ✅ Tokens regenerados: Funcionarán correctamente después del fix
- ⚠️ Tokens existentes con "unknown": Seguirán así hasta que expiren y se regeneren

---
**Date**: 2026-06-09
**Author**: Cline
**Status**: Bug Identified - Ready for Fix