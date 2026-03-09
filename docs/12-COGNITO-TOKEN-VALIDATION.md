# 🔐 Validación de Tokens de Cognito

## 📋 Resumen

Este documento explica cómo validar correctamente los tokens JWT generados por AWS Cognito.

---

## 🎯 Situación Actual

### **¿Qué hacemos ahora?**

En `auth_service.py`, método `_authenticate_with_cognito()`:

```python
# 1. Autenticamos con Cognito
response = client.initiate_auth(
    ClientId=COGNITO_CLIENT_ID,
    AuthFlow='USER_PASSWORD_AUTH',
    AuthParameters={
        'USERNAME': email,
        'PASSWORD': password
    }
)

# 2. Obtenemos tokens
id_token = response['AuthenticationResult']['IdToken']
access_token = response['AuthenticationResult']['AccessToken']

# 3. Usamos access_token para obtener info del usuario
user_response = client.get_user(AccessToken=access_token)

# ❌ PROBLEMA: NO validamos la firma del token
# Solo confiamos en que Cognito nos lo dio
```

### **¿Por qué es un problema?**

- ✅ **Confiamos en Cognito** durante el login inicial
- ❌ **NO validamos** si el token fue realmente emitido por Cognito
- ❌ **NO verificamos** la firma del JWT
- ❌ **NO comprobamos** si el token ha sido manipulado

**Nota**: En el flujo actual esto es **relativamente seguro** porque:
1. El token viene directamente de Cognito (no del cliente)
2. Inmediatamente generamos nuestro propio JWT
3. Nuestro JWT es el que se usa en requests posteriores

---

## ✅ Cómo Validar Tokens de Cognito Correctamente

### **Paso 1: Obtener las Claves Públicas de Cognito**

Cognito publica sus claves públicas (JWKS) en:
```
https://cognito-idp.{region}.amazonaws.com/{userPoolId}/.well-known/jwks.json
```

**Ejemplo para tu User Pool**:
```
https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_UaMIbG9pD/.well-known/jwks.json
```

**Respuesta**:
```json
{
  "keys": [
    {
      "alg": "RS256",
      "e": "AQAB",
      "kid": "abcdefg1234567890",
      "kty": "RSA",
      "n": "xGOr...",
      "use": "sig"
    },
    {
      "alg": "RS256",
      "e": "AQAB",
      "kid": "xyz9876543210",
      "kty": "RSA",
      "n": "yHPs...",
      "use": "sig"
    }
  ]
}
```

---

### **Paso 2: Validar el Token**

#### **Verificaciones Necesarias**:

1. **Decodificar el header del JWT** (sin validar)
2. **Obtener el `kid` (Key ID)** del header
3. **Buscar la clave pública** correspondiente en JWKS
4. **Validar la firma** usando la clave pública
5. **Verificar claims**:
   - `iss` (issuer) = `https://cognito-idp.{region}.amazonaws.com/{userPoolId}`
   - `token_use` = `id` (para ID token) o `access` (para access token)
   - `aud` (audience) = tu `client_id` (solo para ID token)
   - `exp` (expiration) > tiempo actual
   - `iat` (issued at) < tiempo actual

---

### **Paso 3: Implementación en Python**

#### **Opción 1: Usando `python-jose` (Recomendado)**

```python
from jose import jwk, jwt
from jose.utils import base64url_decode
import requests
import json

def validate_cognito_token(token: str, region: str, user_pool_id: str, client_id: str = None) -> dict:
    """
    Validar token JWT de Cognito
    
    Args:
        token: Token JWT a validar
        region: Región AWS (e.g., 'eu-west-1')
        user_pool_id: ID del User Pool (e.g., 'eu-west-1_UaMIbG9pD')
        client_id: Client ID (opcional, solo para ID tokens)
        
    Returns:
        Dict con claims del token si es válido
        
    Raises:
        Exception si el token es inválido
    """
    # 1. Obtener JWKS de Cognito
    jwks_url = f'https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json'
    jwks = requests.get(jwks_url).json()
    
    # 2. Decodificar header del token (sin validar)
    headers = jwt.get_unverified_headers(token)
    kid = headers['kid']
    
    # 3. Buscar la clave pública correspondiente
    key = None
    for jwk_key in jwks['keys']:
        if jwk_key['kid'] == kid:
            key = jwk_key
            break
    
    if not key:
        raise Exception('Public key not found in JWKS')
    
    # 4. Construir la clave pública
    public_key = jwk.construct(key)
    
    # 5. Obtener el mensaje y la firma
    message, encoded_signature = token.rsplit('.', 1)
    decoded_signature = base64url_decode(encoded_signature.encode('utf-8'))
    
    # 6. Verificar la firma
    if not public_key.verify(message.encode('utf-8'), decoded_signature):
        raise Exception('Signature verification failed')
    
    # 7. Decodificar y validar claims
    claims = jwt.get_unverified_claims(token)
    
    # Verificar issuer
    expected_iss = f'https://cognito-idp.{region}.amazonaws.com/{user_pool_id}'
    if claims['iss'] != expected_iss:
        raise Exception(f'Invalid issuer: {claims["iss"]}')
    
    # Verificar expiración
    import time
    if claims['exp'] < time.time():
        raise Exception('Token expired')
    
    # Verificar token_use
    if 'token_use' not in claims:
        raise Exception('token_use claim missing')
    
    # Si es ID token, verificar audience
    if claims['token_use'] == 'id' and client_id:
        if claims.get('aud') != client_id:
            raise Exception(f'Invalid audience: {claims.get("aud")}')
    
    return claims
```

#### **Opción 2: Usando `python-jwt` + `cryptography`**

```python
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import requests
import json

def get_cognito_public_key(kid: str, region: str, user_pool_id: str):
    """Obtener clave pública de Cognito"""
    jwks_url = f'https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json'
    jwks = requests.get(jwks_url).json()
    
    for key in jwks['keys']:
        if key['kid'] == kid:
            return key
    
    raise Exception('Public key not found')

def validate_cognito_token_v2(token: str, region: str, user_pool_id: str, client_id: str = None) -> dict:
    """Validar token de Cognito usando PyJWT"""
    
    # 1. Decodificar header
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header['kid']
    
    # 2. Obtener clave pública
    public_key_data = get_cognito_public_key(kid, region, user_pool_id)
    
    # 3. Construir clave pública RSA
    from jwt.algorithms import RSAAlgorithm
    public_key = RSAAlgorithm.from_jwk(json.dumps(public_key_data))
    
    # 4. Validar token
    expected_iss = f'https://cognito-idp.{region}.amazonaws.com/{user_pool_id}'
    
    claims = jwt.decode(
        token,
        public_key,
        algorithms=['RS256'],
        issuer=expected_iss,
        options={
            'verify_signature': True,
            'verify_exp': True,
            'verify_iat': True,
            'verify_iss': True
        }
    )
    
    # 5. Verificar token_use
    if 'token_use' not in claims:
        raise Exception('token_use claim missing')
    
    # 6. Si es ID token, verificar audience
    if claims['token_use'] == 'id' and client_id:
        if claims.get('aud') != client_id:
            raise Exception(f'Invalid audience')
    
    return claims
```

---

### **Paso 4: Integración en auth_service.py**

```python
def _authenticate_with_cognito(self, email: str, password: str, new_password: str = None) -> Dict[str, Any]:
    """Autenticar usuario con Cognito y validar tokens"""
    
    client = boto3.client('cognito-idp', region_name=config.AWS_REGION)
    
    # 1. Autenticar
    response = client.initiate_auth(
        ClientId=config.COGNITO_CLIENT_ID,
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': email,
            'PASSWORD': password
        }
    )
    
    # 2. Obtener tokens
    auth_result = response.get('AuthenticationResult', {})
    id_token = auth_result.get('IdToken')
    access_token = auth_result.get('AccessToken')
    
    # 3. ✅ VALIDAR ID TOKEN
    try:
        id_token_claims = validate_cognito_token(
            token=id_token,
            region=config.AWS_REGION,
            user_pool_id=config.COGNITO_USER_POOL_ID,
            client_id=config.COGNITO_CLIENT_ID
        )
        logger.info(f"ID token validado correctamente para {email}")
    except Exception as e:
        logger.error(f"Error validando ID token: {e}")
        raise ValueError('Token de Cognito inválido')
    
    # 4. ✅ VALIDAR ACCESS TOKEN
    try:
        access_token_claims = validate_cognito_token(
            token=access_token,
            region=config.AWS_REGION,
            user_pool_id=config.COGNITO_USER_POOL_ID
        )
        logger.info(f"Access token validado correctamente para {email}")
    except Exception as e:
        logger.error(f"Error validando access token: {e}")
        raise ValueError('Token de Cognito inválido')
    
    # 5. Usar información validada
    user_id = id_token_claims['sub']
    email_verified = id_token_claims.get('email', email)
    
    # ... resto del código
```

---

## 📊 Comparación de Enfoques

| Aspecto | Sin Validación (Actual) | Con Validación |
|---------|-------------------------|----------------|
| **Seguridad** | ⚠️ Media | ✅ Alta |
| **Confianza** | Solo en Cognito | Verificación criptográfica |
| **Manipulación** | ❌ Posible (teórico) | ✅ Imposible |
| **Complejidad** | Baja | Media |
| **Performance** | Rápido | Ligeramente más lento |
| **Dependencias** | Ninguna extra | `python-jose` o `PyJWT` |

---

## 🎯 Recomendación

### **Para tu caso específico**:

**Opción A: Mantener como está** ✅ (Aceptable)
- El token viene directamente de Cognito (no del cliente)
- Inmediatamente generamos nuestro propio JWT
- El token de Cognito no se expone al cliente
- **Riesgo**: Bajo

**Opción B: Validar tokens** ✅✅ (Mejor práctica)
- Añade capa extra de seguridad
- Verifica que el token no fue manipulado
- Cumple con mejores prácticas de seguridad
- **Costo**: Pequeño overhead de performance

---

## 🔧 Implementación Recomendada

### **1. Añadir dependencia**

```bash
# requirements.txt
python-jose[cryptography]==3.3.0
```

### **2. Crear servicio de validación**

```python
# backend/shared/services/cognito_token_validator.py

from jose import jwk, jwt
from jose.utils import base64url_decode
import requests
import time
import logging

logger = logging.getLogger()

class CognitoTokenValidator:
    """Validador de tokens JWT de Cognito"""
    
    def __init__(self, region: str, user_pool_id: str, client_id: str = None):
        self.region = region
        self.user_pool_id = user_pool_id
        self.client_id = client_id
        self.jwks_url = f'https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json'
        self._jwks_cache = None
        self._cache_time = 0
        self._cache_ttl = 3600  # 1 hora
    
    def _get_jwks(self):
        """Obtener JWKS con cache"""
        current_time = time.time()
        
        if self._jwks_cache and (current_time - self._cache_time) < self._cache_ttl:
            return self._jwks_cache
        
        try:
            response = requests.get(self.jwks_url, timeout=5)
            response.raise_for_status()
            self._jwks_cache = response.json()
            self._cache_time = current_time
            return self._jwks_cache
        except Exception as e:
            logger.error(f"Error obteniendo JWKS: {e}")
            if self._jwks_cache:
                return self._jwks_cache
            raise
    
    def validate(self, token: str, token_use: str = None) -> dict:
        """
        Validar token de Cognito
        
        Args:
            token: Token JWT
            token_use: 'id' o 'access' (opcional)
            
        Returns:
            Claims del token
        """
        # 1. Obtener JWKS
        jwks = self._get_jwks()
        
        # 2. Decodificar header
        headers = jwt.get_unverified_headers(token)
        kid = headers['kid']
        
        # 3. Buscar clave pública
        key = None
        for jwk_key in jwks['keys']:
            if jwk_key['kid'] == kid:
                key = jwk_key
                break
        
        if not key:
            raise ValueError('Public key not found in JWKS')
        
        # 4. Construir clave pública
        public_key = jwk.construct(key)
        
        # 5. Verificar firma
        message, encoded_signature = token.rsplit('.', 1)
        decoded_signature = base64url_decode(encoded_signature.encode('utf-8'))
        
        if not public_key.verify(message.encode('utf-8'), decoded_signature):
            raise ValueError('Signature verification failed')
        
        # 6. Decodificar claims
        claims = jwt.get_unverified_claims(token)
        
        # 7. Verificar issuer
        expected_iss = f'https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}'
        if claims.get('iss') != expected_iss:
            raise ValueError(f'Invalid issuer: {claims.get("iss")}')
        
        # 8. Verificar expiración
        if claims.get('exp', 0) < time.time():
            raise ValueError('Token expired')
        
        # 9. Verificar token_use
        if token_use and claims.get('token_use') != token_use:
            raise ValueError(f'Invalid token_use: {claims.get("token_use")}')
        
        # 10. Verificar audience (solo para ID tokens)
        if claims.get('token_use') == 'id' and self.client_id:
            if claims.get('aud') != self.client_id:
                raise ValueError(f'Invalid audience: {claims.get("aud")}')
        
        return claims
```

### **3. Usar en auth_service.py**

```python
from shared.services.cognito_token_validator import CognitoTokenValidator

class AuthService:
    def __init__(self):
        # ... código existente ...
        
        # Inicializar validador de tokens
        self.token_validator = CognitoTokenValidator(
            region=config.AWS_REGION,
            user_pool_id=config.COGNITO_USER_POOL_ID,
            client_id=config.COGNITO_CLIENT_ID
        )
    
    def _authenticate_with_cognito(self, email: str, password: str, new_password: str = None):
        # ... autenticación con Cognito ...
        
        # Validar ID token
        try:
            id_claims = self.token_validator.validate(id_token, token_use='id')
            logger.info(f"✅ ID token validado para {email}")
        except Exception as e:
            logger.error(f"❌ ID token inválido: {e}")
            raise ValueError('Token de Cognito inválido')
        
        # Validar access token
        try:
            access_claims = self.token_validator.validate(access_token, token_use='access')
            logger.info(f"✅ Access token validado para {email}")
        except Exception as e:
            logger.error(f"❌ Access token inválido: {e}")
            raise ValueError('Token de Cognito inválido')
        
        # Usar claims validados
        user_id = id_claims['sub']
        # ...
```

---

## 📝 Resumen

### **¿Necesitas validar tokens de Cognito?**

**En tu caso actual**: No es crítico, pero es buena práctica.

**Cuándo SÍ es crítico**:
- Si el token viene del cliente (no de Cognito directamente)
- Si almacenas el token de Cognito para uso posterior
- Si el token se pasa entre servicios
- Si quieres máxima seguridad

**Cuándo NO es tan crítico**:
- Si el token viene directamente de Cognito
- Si inmediatamente generas tu propio JWT
- Si el token de Cognito no se expone al cliente

### **Mi recomendación**: 
Implementar la validación como **mejora de seguridad**, pero no es urgente dado tu flujo actual.