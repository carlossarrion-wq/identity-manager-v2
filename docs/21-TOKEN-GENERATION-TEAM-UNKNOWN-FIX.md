# Token Generation - Team "Unknown" Root Cause Analysis

## Problem Identified

After analyzing a real JWT token from an affected user, we found:

```json
{
  "user_id": "c28514e4-9031-7020-cc7d-c0b80956946b",
  "email": "carlos.sarrion@es.ibm.com",
  "default_inference_profile": "dc1b3985-78df-4ef6-804a-2cfb50f7dee3",
  "team": "unknown",           // ❌ PROBLEMA: team es "unknown"
  "person": "",                // ❌ PROBLEMA: person está vacío
  "iss": "identity-manager",
  "sub": "c28514e4-9031-7020-cc7d-c0b80956946b",
  "aud": ["bedrock-proxy"],
  "exp": 1780995590,
  "iat": 1780909190,
  "jti": "5cf9cd6e-689f-4eae-8f97-d3c7f641431e"
}
```

**Conclusión**: El problema NO está en el proxy-bedrock, sino en la **generación del token JWT** en el backend.

## Root Cause Analysis

### 1. Flujo de Generación de Token

El flujo es el siguiente:

```
handle_create_token() 
  → get_user_info_from_cognito()
  → jwt_service.generate_token(user_info, profile_info)
  → JWT con team="unknown"
```

### 2. Código Problemático en jwt_service.py

**Archivo**: `backend/shared/services/jwt_service.py`

```python
def generate_token(
    self,
    user_info: Dict[str, Any],
    profile_info: Dict[str, Any],
    validity_period: str = '90_days',
    audiences: list = None
) -> Dict[str, Any]:
    # ...
    
    # ❌ PROBLEMA AQUÍ: Obtiene el primer grupo del usuario
    team = user_info.get('groups', ['unknown'])[0] if user_info.get('groups') else 'unknown'
    
    # Construir payload del JWT
    payload = {
        'user_id': user_info['user_id'],
        'email': user_info['email'],
        'default_inference_profile': str(profile_info['profile_id']),
        'team': team,  # ← Se usa el primer grupo como team
        'person': user_info.get('person', ''),  # ← Puede estar vacío
        # ...
    }
```

**Línea 102**: `team = user_info.get('groups', ['unknown'])[0] if user_info.get('groups') else 'unknown'`

### 3. El Problema Real

El código asume que:
1. El campo `team` debe venir del **primer grupo de Cognito** del usuario
2. Si no hay grupos, usa `'unknown'`

**Pero esto es incorrecto porque**:
- Los grupos de Cognito NO son lo mismo que el "team" del usuario
- Un usuario puede estar en múltiples grupos (ej: "developers", "admins")
- El "team" debería venir de un atributo personalizado de Cognito (`custom:team`) o de la base de datos

### 4. Comparación con Código que Funciona

En `cognito_service.py`, cuando se formatea un usuario, se intenta obtener `custom:person`:

```python
def _format_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
    attributes = {attr['Name']: attr['Value'] for attr in user_data.get('Attributes', [])}
    
    return {
        'user_id': user_data['Username'],
        'email': attributes.get('email', ''),
        'person': attributes.get('custom:person', attributes.get('name', '')),  # ✓ Correcto
        'status': user_data.get('UserStatus', 'UNKNOWN'),
        # ...
    }
```

**Pero NO hay código que obtenga `custom:team`** de los atributos de Cognito.

## Solution

### Opción 1: Usar Atributo Personalizado de Cognito (Recomendado)

Si los usuarios tienen el atributo `custom:team` en Cognito:

**1. Modificar `cognito_service.py` para incluir team:**

```python
def _format_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
    attributes = {attr['Name']: attr['Value'] for attr in user_data.get('Attributes', [])}
    
    return {
        'user_id': user_data['Username'],
        'email': attributes.get('email', ''),
        'person': attributes.get('custom:person', attributes.get('name', '')),
        'team': attributes.get('custom:team', ''),  # ← AÑADIR ESTO
        'status': user_data.get('UserStatus', 'UNKNOWN'),
        # ...
    }
```

**2. Modificar `jwt_service.py` para usar el team del user_info:**

```python
def generate_token(
    self,
    user_info: Dict[str, Any],
    profile_info: Dict[str, Any],
    validity_period: str = '90_days',
    audiences: list = None
) -> Dict[str, Any]:
    # ...
    
    # ✓ CORRECCIÓN: Usar team de user_info, con fallback al primer grupo
    team = user_info.get('team', '')
    if not team:
        # Fallback: usar primer grupo si no hay team
        team = user_info.get('groups', ['unknown'])[0] if user_info.get('groups') else 'unknown'
    
    # Construir payload del JWT
    payload = {
        'user_id': user_info['user_id'],
        'email': user_info['email'],
        'default_inference_profile': str(profile_info['profile_id']),
        'team': team,
        'person': user_info.get('person', ''),
        # ...
    }
```

### Opción 2: Usar Primer Grupo como Team (Actual, pero mejorado)

Si el diseño es que el team sea el primer grupo de Cognito:

**Modificar `jwt_service.py` para obtener grupos correctamente:**

```python
def generate_token(
    self,
    user_info: Dict[str, Any],
    profile_info: Dict[str, Any],
    validity_period: str = '90_days',
    audiences: list = None
) -> Dict[str, Any]:
    # ...
    
    # Obtener team del primer grupo, con validación
    groups = user_info.get('groups', [])
    if groups and len(groups) > 0:
        team = groups[0]
    else:
        # Si no hay grupos, intentar obtener de custom:team
        team = user_info.get('team', 'unknown')
    
    # Construir payload del JWT
    payload = {
        'user_id': user_info['user_id'],
        'email': user_info['email'],
        'default_inference_profile': str(profile_info['profile_id']),
        'team': team,
        'person': user_info.get('person', ''),
        # ...
    }
```

### Opción 3: Obtener Team de Base de Datos

Si el team está almacenado en la base de datos:

**Modificar `handle_create_token` para obtener team de BD:**

```python
def handle_create_token(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    data = body.get('data', {})
    user_id = data.get('user_id')
    
    # Obtener información del usuario de Cognito
    user_info = cognito_service.get_user(user_id)
    
    # ✓ AÑADIR: Obtener team de la base de datos
    db_user = database_service.get_user_by_id(user_id)
    if db_user and db_user.get('team'):
        user_info['team'] = db_user['team']
    
    # Obtener perfil de inferencia
    profile_info = database_service.get_profile(data.get('profile_id'))
    
    # Generar token
    token_data = jwt_service.generate_token(user_info, profile_info, ...)
```

## Verification Steps

### 1. Verificar Atributos de Cognito

Ejecutar este script para ver qué atributos tiene el usuario:

```python
import boto3

cognito = boto3.client('cognito-idp')
response = cognito.admin_get_user(
    UserPoolId='your-pool-id',
    Username='carlos.sarrion@es.ibm.com'
)

print("User Attributes:")
for attr in response['UserAttributes']:
    print(f"  {attr['Name']}: {attr['Value']}")

print("\nUser Groups:")
groups_response = cognito.admin_list_groups_for_user(
    UserPoolId='your-pool-id',
    Username='carlos.sarrion@es.ibm.com'
)
for group in groups_response['Groups']:
    print(f"  {group['GroupName']}")
```

### 2. Verificar user_info en Token Generation

Añadir logging en `jwt_service.py`:

```python
def generate_token(self, user_info: Dict[str, Any], ...):
    logger.info(f"Generating token with user_info: {json.dumps(user_info, indent=2)}")
    
    team = user_info.get('groups', ['unknown'])[0] if user_info.get('groups') else 'unknown'
    logger.info(f"Extracted team: {team}")
    
    # ...
```

## Recommended Fix (Step by Step)

### Step 1: Modificar cognito_service.py

```python
def _format_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
    attributes = {attr['Name']: attr['Value'] for attr in user_data.get('Attributes', [])}
    
    return {
        'user_id': user_data['Username'],
        'email': attributes.get('email', ''),
        'person': attributes.get('custom:person', attributes.get('name', '')),
        'team': attributes.get('custom:team', ''),  # ← AÑADIR
        'status': user_data.get('UserStatus', 'UNKNOWN'),
        'enabled': user_data.get('Enabled', True),
        'created_date': user_data.get('UserCreateDate'),
        'modified_date': user_data.get('UserLastModifiedDate'),
        'groups': []  # Se llenará después si es necesario
    }
```

### Step 2: Modificar jwt_service.py

```python
def generate_token(
    self,
    user_info: Dict[str, Any],
    profile_info: Dict[str, Any],
    validity_period: str = '90_days',
    audiences: list = None
) -> Dict[str, Any]:
    # ...
    
    # Obtener team: prioridad a custom:team, fallback a primer grupo
    team = user_info.get('team', '').strip()
    if not team:
        groups = user_info.get('groups', [])
        team = groups[0] if groups else 'unknown'
    
    # Obtener person
    person = user_info.get('person', '').strip()
    
    # Log para debugging
    logger.info(f"Token generation - user_id: {user_info['user_id']}, team: {team}, person: {person}")
    
    # Construir payload del JWT
    payload = {
        'user_id': user_info['user_id'],
        'email': user_info['email'],
        'default_inference_profile': str(profile_info['profile_id']),
        'team': team,
        'person': person,
        'iss': 'identity-manager',
        'sub': user_info['user_id'],
        'aud': audiences,
        'exp': exp,
        'iat': iat,
        'jti': jti
    }
    
    # ...
```

### Step 3: Actualizar Usuarios en Cognito

Si los usuarios no tienen `custom:team`, ejecutar script de migración:

```python
import boto3

cognito = boto3.client('cognito-idp')
user_pool_id = 'your-pool-id'

# Obtener todos los usuarios
response = cognito.list_users(UserPoolId=user_pool_id)

for user in response['Users']:
    username = user['Username']
    
    # Obtener grupos del usuario
    groups_response = cognito.admin_list_groups_for_user(
        UserPoolId=user_pool_id,
        Username=username
    )
    
    if groups_response['Groups']:
        team = groups_response['Groups'][0]['GroupName']
        
        # Actualizar custom:team
        cognito.admin_update_user_attributes(
            UserPoolId=user_pool_id,
            Username=username,
            UserAttributes=[
                {'Name': 'custom:team', 'Value': team}
            ]
        )
        
        print(f"Updated {username} with team: {team}")
```

### Step 4: Regenerar Tokens Afectados

Después de actualizar los usuarios, regenerar los tokens:

```python
# Opción 1: Revocar tokens existentes (forzar regeneración)
database_service.revoke_user_tokens(user_id)

# Opción 2: Usar el servicio de regeneración automática
token_regeneration_service.regenerate_expired_token(old_jti, user_id)
```

## Testing

### Test 1: Verificar Atributos de Usuario

```python
user_info = cognito_service.get_user('carlos.sarrion@es.ibm.com')
print(f"Team: {user_info.get('team')}")
print(f"Person: {user_info.get('person')}")
print(f"Groups: {user_info.get('groups')}")
```

### Test 2: Generar Token y Verificar

```python
token_data = jwt_service.generate_token(user_info, profile_info)
payload = jwt.decode(token_data['jwt'], options={"verify_signature": False})
print(f"Token team: {payload.get('team')}")
print(f"Token person: {payload.get('person')}")
```

### Test 3: Verificar en Base de Datos

```sql
-- Verificar registros nuevos después del fix
SELECT 
    cognito_email,
    team,
    person,
    COUNT(*) as count
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE request_timestamp > NOW() - INTERVAL '1 hour'
GROUP BY cognito_email, team, person
ORDER BY count DESC;
```

## Conclusion

El problema está en la **generación del token JWT**, específicamente en cómo se obtiene el campo `team`:

1. **Causa**: El código usa `user_info.get('groups', ['unknown'])[0]` que toma el primer grupo de Cognito
2. **Problema**: Si el usuario no tiene grupos o el grupo no representa el team, se genera `"team": "unknown"`
3. **Solución**: Obtener `team` del atributo `custom:team` de Cognito o de la base de datos

**Acción Inmediata**:
1. Verificar si los usuarios tienen `custom:team` en Cognito
2. Si no, ejecutar script de migración para poblar `custom:team`
3. Modificar `cognito_service.py` y `jwt_service.py` según la solución recomendada
4. Regenerar tokens afectados

---
**Date**: 2026-06-09
**Author**: Cline
**Status**: Root Cause Identified - Ready for Implementation