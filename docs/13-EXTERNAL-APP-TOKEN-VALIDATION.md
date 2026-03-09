# 🔐 Validación de JWT por Aplicaciones Externas

## 📋 Resumen

Este documento explica cómo una **aplicación externa** debe validar el JWT generado por la Lambda de autenticación (`login-authorization-service`) que incluye permisos de aplicaciones.

---

## 🎯 Escenario

### **Flujo Completo**:

```
┌─────────────┐
│   Usuario   │
└──────┬──────┘
       │
       │ 1. Login
       ▼
┌─────────────────────────────────────┐
│  Auth Lambda (login-authorization)  │
│  - Valida con Cognito               │
│  - Obtiene permisos de BD           │
│  - Genera JWT con permisos          │
└──────┬──────────────────────────────┘
       │
       │ 2. JWT con app_permissions
       ▼
┌─────────────────────────────────────┐
│         Usuario / Cliente           │
│  Guarda JWT en localStorage         │
└──────┬──────────────────────────────┘
       │
       │ 3. Request con JWT
       ▼
┌─────────────────────────────────────┐
│      APLICACIÓN EXTERNA             │
│  ¿Cómo validar este JWT?            │
│  ¿Cómo verificar permisos?          │
└─────────────────────────────────────┘
```

---

## 🔑 Estructura del JWT

### **JWT Generado por Auth Lambda**:

```json
{
  "sub": "62d5f404-90d1-70cc-e0d6-a8cb2d156cbc",
  "email": "carlos.sarrion@es.ibm.com",
  "name": "Carlos Sarrión",
  "groups": ["lcs-sdlc-gen-group"],
  "app_permissions": [
    {
      "app_id": "e61e1af9-8992-4bdf-be65-9cad86f34da0",
      "app_name": "identity-mgmt",
      "permission_type": "admin",
      "permission_level": 100
    },
    {
      "app_id": "f72e2bf0-9003-5cef-cf76-0dbe97e45eb1",
      "app_name": "my-external-app",
      "permission_type": "user",
      "permission_level": 50
    }
  ],
  "iat": 1773048628,
  "exp": 1773052228,
  "iss": "auth-lambda",
  "aud": ["auth-login"]
}
```

### **Firmado con**:
- **Algoritmo**: HS256 (HMAC-SHA256)
- **Secret Key**: Almacenada en AWS Secrets Manager
  - Nombre: `identity-mgmt-dev-key-access`
  - Valor: Clave secreta compartida

---

## ✅ Validación del JWT por Aplicación Externa

### **Paso 1: Obtener la Secret Key**

La aplicación externa **DEBE tener acceso** a la misma secret key que usa la Lambda de autenticación.

#### **Opción A: Desde AWS Secrets Manager** (Recomendado)

```python
import boto3
import json

def get_jwt_secret_key():
    """Obtener secret key desde AWS Secrets Manager"""
    client = boto3.client('secretsmanager', region_name='eu-west-1')
    
    response = client.get_secret_value(
        SecretId='identity-mgmt-dev-key-access'
    )
    
    secret = json.loads(response['SecretString'])
    return secret['jwt_secret_key']
```

#### **Opción B: Variable de Entorno** (Para desarrollo)

```python
import os

JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
```

---

### **Paso 2: Validar el JWT**

#### **Implementación en Python**:

```python
import jwt
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class JWTValidator:
    """Validador de JWT para aplicaciones externas"""
    
    def __init__(self, secret_key: str, expected_issuer: str = 'auth-lambda'):
        self.secret_key = secret_key
        self.expected_issuer = expected_issuer
    
    def validate_token(self, token: str) -> dict:
        """
        Validar JWT y extraer claims
        
        Args:
            token: Token JWT a validar
            
        Returns:
            Dict con claims del token
            
        Raises:
            jwt.ExpiredSignatureError: Si el token expiró
            jwt.InvalidTokenError: Si el token es inválido
        """
        try:
            # Decodificar y validar token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=['HS256'],
                options={
                    'verify_signature': True,
                    'verify_exp': True,
                    'verify_iat': True,
                    'require': ['sub', 'email', 'exp', 'iat', 'iss']
                }
            )
            
            # Verificar issuer
            if payload.get('iss') != self.expected_issuer:
                raise jwt.InvalidTokenError(f'Invalid issuer: {payload.get("iss")}')
            
            logger.info(f"✅ Token válido para usuario {payload.get('email')}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("❌ Token expirado")
            raise
        except jwt.InvalidTokenError as e:
            logger.error(f"❌ Token inválido: {e}")
            raise
    
    def get_user_info(self, token: str) -> dict:
        """Obtener información del usuario desde el token"""
        payload = self.validate_token(token)
        
        return {
            'user_id': payload['sub'],
            'email': payload['email'],
            'name': payload.get('name'),
            'groups': payload.get('groups', [])
        }
    
    def get_app_permissions(self, token: str) -> list:
        """Obtener permisos de aplicaciones desde el token"""
        payload = self.validate_token(token)
        return payload.get('app_permissions', [])
    
    def has_app_permission(self, token: str, app_id: str, min_level: int = 0) -> bool:
        """
        Verificar si el usuario tiene permiso para una aplicación
        
        Args:
            token: Token JWT
            app_id: ID de la aplicación
            min_level: Nivel mínimo de permiso requerido (0-100)
            
        Returns:
            True si tiene permiso, False en caso contrario
        """
        try:
            permissions = self.get_app_permissions(token)
            
            for perm in permissions:
                if perm.get('app_id') == app_id:
                    if perm.get('permission_level', 0) >= min_level:
                        logger.info(f"✅ Usuario tiene permiso para {app_id} (nivel {perm.get('permission_level')})")
                        return True
            
            logger.warning(f"❌ Usuario NO tiene permiso para {app_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error verificando permisos: {e}")
            return False
```

---

### **Paso 3: Uso en Aplicación Externa**

#### **Ejemplo: API Flask**

```python
from flask import Flask, request, jsonify
from functools import wraps
import boto3
import json

app = Flask(__name__)

# Inicializar validador
def get_jwt_secret():
    client = boto3.client('secretsmanager', region_name='eu-west-1')
    response = client.get_secret_value(SecretId='identity-mgmt-dev-key-access')
    secret = json.loads(response['SecretString'])
    return secret['jwt_secret_key']

jwt_validator = JWTValidator(secret_key=get_jwt_secret())

# Decorador para proteger endpoints
def require_auth(app_id: str = None, min_level: int = 0):
    """
    Decorador para requerir autenticación y permisos
    
    Args:
        app_id: ID de la aplicación (opcional)
        min_level: Nivel mínimo de permiso (opcional)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 1. Extraer token del header
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({'error': 'Missing Authorization header'}), 401
            
            try:
                # Formato: "Bearer <token>"
                token = auth_header.split(' ')[1]
            except IndexError:
                return jsonify({'error': 'Invalid Authorization header format'}), 401
            
            # 2. Validar token
            try:
                user_info = jwt_validator.get_user_info(token)
            except jwt.ExpiredSignatureError:
                return jsonify({'error': 'Token expired'}), 401
            except jwt.InvalidTokenError:
                return jsonify({'error': 'Invalid token'}), 401
            
            # 3. Verificar permisos de aplicación (si se requiere)
            if app_id:
                if not jwt_validator.has_app_permission(token, app_id, min_level):
                    return jsonify({
                        'error': 'Insufficient permissions',
                        'required_app': app_id,
                        'required_level': min_level
                    }), 403
            
            # 4. Añadir info del usuario al request
            request.user = user_info
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

# Endpoints protegidos
@app.route('/api/public')
def public_endpoint():
    """Endpoint público - no requiere autenticación"""
    return jsonify({'message': 'Public endpoint'})

@app.route('/api/protected')
@require_auth()
def protected_endpoint():
    """Endpoint protegido - requiere autenticación"""
    return jsonify({
        'message': 'Protected endpoint',
        'user': request.user
    })

@app.route('/api/my-app/data')
@require_auth(app_id='f72e2bf0-9003-5cef-cf76-0dbe97e45eb1', min_level=50)
def app_specific_endpoint():
    """Endpoint que requiere permiso específico de aplicación"""
    return jsonify({
        'message': 'App-specific data',
        'user': request.user,
        'app_id': 'f72e2bf0-9003-5cef-cf76-0dbe97e45eb1'
    })

@app.route('/api/admin/settings')
@require_auth(app_id='f72e2bf0-9003-5cef-cf76-0dbe97e45eb1', min_level=100)
def admin_endpoint():
    """Endpoint que requiere permisos de administrador"""
    return jsonify({
        'message': 'Admin settings',
        'user': request.user
    })
```

---

#### **Ejemplo: API FastAPI**

```python
from fastapi import FastAPI, Depends, HTTPException, Header
from typing import Optional
import jwt

app = FastAPI()

# Inicializar validador
jwt_validator = JWTValidator(secret_key=get_jwt_secret())

# Dependency para extraer y validar token
async def get_current_user(authorization: Optional[str] = Header(None)):
    """Dependency para obtener usuario actual desde JWT"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    try:
        token = authorization.split(' ')[1]
        user_info = jwt_validator.get_user_info(token)
        return user_info
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except IndexError:
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")

# Dependency para verificar permisos de aplicación
def require_app_permission(app_id: str, min_level: int = 0):
    """Dependency factory para verificar permisos de aplicación"""
    async def check_permission(
        authorization: Optional[str] = Header(None),
        user = Depends(get_current_user)
    ):
        try:
            token = authorization.split(' ')[1]
            if not jwt_validator.has_app_permission(token, app_id, min_level):
                raise HTTPException(
                    status_code=403,
                    detail={
                        'error': 'Insufficient permissions',
                        'required_app': app_id,
                        'required_level': min_level
                    }
                )
            return user
        except IndexError:
            raise HTTPException(status_code=401, detail="Invalid Authorization header")
    
    return check_permission

# Endpoints
@app.get("/api/public")
async def public_endpoint():
    """Endpoint público"""
    return {"message": "Public endpoint"}

@app.get("/api/protected")
async def protected_endpoint(user = Depends(get_current_user)):
    """Endpoint protegido"""
    return {
        "message": "Protected endpoint",
        "user": user
    }

@app.get("/api/my-app/data")
async def app_specific_endpoint(
    user = Depends(require_app_permission('f72e2bf0-9003-5cef-cf76-0dbe97e45eb1', 50))
):
    """Endpoint con permiso específico"""
    return {
        "message": "App-specific data",
        "user": user
    }
```

---

#### **Ejemplo: Middleware Express (Node.js)**

```javascript
const jwt = require('jsonwebtoken');
const AWS = require('aws-sdk');

// Obtener secret key
async function getJWTSecret() {
    const client = new AWS.SecretsManager({ region: 'eu-west-1' });
    const response = await client.getSecretValue({
        SecretId: 'identity-mgmt-dev-key-access'
    }).promise();
    
    const secret = JSON.parse(response.SecretString);
    return secret.jwt_secret_key;
}

// Middleware de autenticación
const authenticateJWT = async (req, res, next) => {
    const authHeader = req.headers.authorization;
    
    if (!authHeader) {
        return res.status(401).json({ error: 'Missing Authorization header' });
    }
    
    const token = authHeader.split(' ')[1];
    
    try {
        const secretKey = await getJWTSecret();
        const payload = jwt.verify(token, secretKey, {
            algorithms: ['HS256'],
            issuer: 'auth-lambda'
        });
        
        req.user = {
            user_id: payload.sub,
            email: payload.email,
            name: payload.name,
            groups: payload.groups || [],
            app_permissions: payload.app_permissions || []
        };
        
        next();
    } catch (error) {
        if (error.name === 'TokenExpiredError') {
            return res.status(401).json({ error: 'Token expired' });
        }
        return res.status(401).json({ error: 'Invalid token' });
    }
};

// Middleware para verificar permisos de aplicación
const requireAppPermission = (appId, minLevel = 0) => {
    return (req, res, next) => {
        const permissions = req.user.app_permissions || [];
        
        const hasPermission = permissions.some(perm => 
            perm.app_id === appId && perm.permission_level >= minLevel
        );
        
        if (!hasPermission) {
            return res.status(403).json({
                error: 'Insufficient permissions',
                required_app: appId,
                required_level: minLevel
            });
        }
        
        next();
    };
};

// Uso en rutas
app.get('/api/public', (req, res) => {
    res.json({ message: 'Public endpoint' });
});

app.get('/api/protected', authenticateJWT, (req, res) => {
    res.json({
        message: 'Protected endpoint',
        user: req.user
    });
});

app.get('/api/my-app/data', 
    authenticateJWT,
    requireAppPermission('f72e2bf0-9003-5cef-cf76-0dbe97e45eb1', 50),
    (req, res) => {
        res.json({
            message: 'App-specific data',
            user: req.user
        });
    }
);
```

---

## 🔒 Consideraciones de Seguridad

### **1. Protección de la Secret Key**

**❌ NUNCA**:
- Hardcodear la secret key en el código
- Commitear la secret key a Git
- Exponer la secret key en logs
- Compartir la secret key por email/chat

**✅ SIEMPRE**:
- Usar AWS Secrets Manager
- Rotar la secret key periódicamente
- Usar variables de entorno en desarrollo
- Limitar acceso IAM a Secrets Manager

---

### **2. Validaciones Obligatorias**

```python
# ✅ Validaciones que DEBES hacer:
payload = jwt.decode(
    token,
    secret_key,
    algorithms=['HS256'],  # ✅ Especificar algoritmo
    options={
        'verify_signature': True,  # ✅ Verificar firma
        'verify_exp': True,         # ✅ Verificar expiración
        'verify_iat': True,         # ✅ Verificar issued at
        'require': ['sub', 'email', 'exp']  # ✅ Campos requeridos
    }
)

# ✅ Verificar issuer
if payload.get('iss') != 'auth-lambda':
    raise ValueError('Invalid issuer')

# ✅ Verificar permisos de aplicación
if not has_app_permission(payload, MY_APP_ID):
    raise PermissionError('No access to this app')
```

---

### **3. Manejo de Errores**

```python
try:
    payload = jwt_validator.validate_token(token)
except jwt.ExpiredSignatureError:
    # Token expirado - usuario debe hacer login de nuevo
    return {'error': 'Token expired', 'code': 'TOKEN_EXPIRED'}, 401
except jwt.InvalidSignatureError:
    # Firma inválida - posible manipulación
    logger.error("⚠️ Invalid signature detected!")
    return {'error': 'Invalid token', 'code': 'INVALID_SIGNATURE'}, 401
except jwt.DecodeError:
    # Token malformado
    return {'error': 'Malformed token', 'code': 'MALFORMED_TOKEN'}, 401
except Exception as e:
    # Error inesperado
    logger.error(f"Unexpected error: {e}")
    return {'error': 'Authentication error', 'code': 'AUTH_ERROR'}, 500
```

---

## 📊 Flujo Completo de Validación

```
┌─────────────────────────────────────────────────────────────┐
│                    APLICACIÓN EXTERNA                        │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ 1. Recibe request con JWT
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  PASO 1: Extraer Token                                       │
│  ────────────────────────                                    │
│  Authorization: Bearer eyJhbGc...                            │
│  token = header.split(' ')[1]                                │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ 2. Obtener Secret Key
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  PASO 2: Obtener Secret Key                                  │
│  ────────────────────────────────                            │
│  secret = get_secret_from_aws_secrets_manager()              │
│  secret_key = secret['jwt_secret_key']                       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ 3. Validar JWT
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  PASO 3: Validar Firma y Claims                              │
│  ────────────────────────────────────                        │
│  payload = jwt.decode(token, secret_key, algorithms=['HS256'])│
│  ✅ Verificar firma                                          │
│  ✅ Verificar expiración (exp)                               │
│  ✅ Verificar issuer (iss = 'auth-lambda')                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ 4. Extraer información
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  PASO 4: Extraer User Info y Permisos                        │
│  ──────────────────────────────────────                      │
│  user_id = payload['sub']                                    │
│  email = payload['email']                                    │
│  app_permissions = payload['app_permissions']                │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ 5. Verificar permisos
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  PASO 5: Verificar Permiso de Aplicación                     │
│  ─────────────────────────────────────────                   │
│  my_app_id = 'f72e2bf0-9003-5cef-cf76-0dbe97e45eb1'         │
│  has_permission = any(                                       │
│      p['app_id'] == my_app_id                                │
│      for p in app_permissions                                │
│  )                                                            │
│                                                               │
│  if not has_permission:                                      │
│      return 403 Forbidden                                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ 6. Permitir acceso
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  ✅ ACCESO PERMITIDO                                         │
│  Procesar request normalmente                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 Checklist de Implementación

Para implementar validación de JWT en tu aplicación externa:

- [ ] **Obtener Secret Key**
  - [ ] Configurar acceso a AWS Secrets Manager
  - [ ] Obtener `identity-mgmt-dev-key-access`
  - [ ] Cachear secret key (no consultar en cada request)

- [ ] **Implementar Validación**
  - [ ] Instalar librería JWT (`PyJWT`, `jsonwebtoken`, etc.)
  - [ ] Crear función de validación
  - [ ] Verificar firma (HS256)
  - [ ] Verificar expiración
  - [ ] Verificar issuer

- [ ] **Extraer Información**
  - [ ] Obtener user_id, email, name
  - [ ] Obtener app_permissions
  - [ ] Obtener groups

- [ ] **Verificar Permisos**
  - [ ] Buscar tu app_id en app_permissions
  - [ ] Verificar permission_level si es necesario
  - [ ] Retornar 403 si no tiene permiso

- [ ] **Manejo de Errores**
  - [ ] Token expirado → 401
  - [ ] Token inválido → 401
  - [ ] Sin permisos → 403
  - [ ] Logging de errores

- [ ] **Testing**
  - [ ] Probar con token válido
  - [ ] Probar con token expirado
  - [ ] Probar con token manipulado
  - [ ] Probar sin permisos

---

## 🎯 Resumen

### **Para validar el JWT en tu aplicación externa**:

1. **Obtén la secret key** desde AWS Secrets Manager
2. **Valida el JWT** usando la librería JWT de tu lenguaje
3. **Verifica** firma, expiración e issuer
4. **Extrae** `app_permissions` del payload
5. **Verifica** que tu `app_id` esté en la lista
6. **Permite o deniega** acceso según permisos

### **Secret Key compartida**:
- Nombre: `identity-mgmt-dev-key-access`
- Región: `eu-west-1`
- Formato: `{"jwt_secret_key": "..."}`

### **Algoritmo**: HS256 (HMAC-SHA256)
### **Issuer**: `auth-lambda`
### **Duración**: 1 hora