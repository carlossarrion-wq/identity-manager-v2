# Auth Lambda - Diseño de Implementación
## Lambda de Autenticación Simplificada

---

## 📋 Resumen Ejecutivo

Lambda dedicada para autenticación de usuarios con **2 endpoints simples**:
1. **Login**: Autenticación con Cognito + Permisos en token
2. **Verify**: Validación de token JWT

**Objetivo**: Proporcionar autenticación centralizada para todas las aplicaciones de la plataforma.

---

## 🏗️ Arquitectura

### Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                      AUTH LAMBDA                             │
│                   (auth-api-lmbd)                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Endpoints:                                                  │
│  ├─ POST /auth/login                                        │
│  │   └─ Autentica usuario con Cognito                      │
│  │   └─ Consulta permisos en RDS                           │
│  │   └─ Retorna: Token JWT con permisos incluidos          │
│  │                                                           │
│  └─ POST /auth/verify                                       │
│      └─ Valida token JWT                                    │
│      └─ Retorna: Claims del usuario + permisos             │
│                                                              │
│  Servicios Reutilizados:                                    │
│  ├─ CognitoService (autenticación)                         │
│  ├─ DatabaseService (consulta permisos)                    │
│  └─ PermissionsService (lógica de permisos)                │
│                                                              │
│  Servicios Nuevos:                                          │
│  └─ AuthService (generación y validación de tokens)        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Flujos Detallados

### Flujo 1: Login

```
┌──────────┐         ┌──────────┐         ┌──────────┐         ┌──────────┐
│          │         │          │         │          │         │          │
│  App     │────1───▶│  Auth    │────2───▶│ Cognito  │         │   RDS    │
│  Client  │         │  Lambda  │         │          │         │ Postgres │
│          │         │          │────3───▶│          │────4───▶│          │
│          │◀───7────│          │◀───6────│          │◀───5────│          │
└──────────┘         └──────────┘         └──────────┘         └──────────┘

1. POST /auth/login
   {
     "email": "user@example.com",
     "password": "SecurePass123!"
   }

2. Auth Lambda → Cognito: InitiateAuth
   - Valida credenciales
   - Obtiene tokens de Cognito

3. Cognito retorna:
   - IdToken (identidad del usuario)
   - AccessToken (acceso a recursos AWS)
   - RefreshToken (renovar sesión)

4. Auth Lambda → RDS: Consulta permisos
   - Permisos de aplicaciones
   - Permisos de módulos

5. RDS retorna permisos activos del usuario

6. Auth Lambda genera token JWT propio con:
   - Claims de Cognito
   - Permisos incluidos
   - Firma con clave privada

7. Retorna a App:
   {
     "success": true,
     "token": "eyJhbGc...",  // Token JWT con permisos
     "user": {
       "userId": "uuid-123",
       "email": "user@example.com",
       "name": "John Doe",
       "groups": ["developers"]
     },
     "permissions": {
       "applications": [...],
       "modules": [...]
     },
     "expiresAt": "2026-03-02T12:00:00Z"
   }
```

### Flujo 2: Verify

```
┌──────────┐         ┌──────────┐
│          │         │          │
│  App     │────1───▶│  Auth    │
│  Client  │         │  Lambda  │
│          │◀───3────│          │
└──────────┘         └──────────┘

1. POST /auth/verify
   {
     "token": "eyJhbGc..."
   }

2. Auth Lambda valida:
   - Firma del token (usando clave pública)
   - Expiración
   - Estructura del payload

3. Retorna:
   {
     "valid": true,
     "user": {
       "userId": "uuid-123",
       "email": "user@example.com",
       "name": "John Doe"
     },
     "permissions": {
       "applications": [...],
       "modules": [...]
     },
     "expiresAt": "2026-03-02T12:00:00Z"
   }
```

---

## 📁 Estructura de Archivos

```
backend/
├── shared/                              # Código compartido
│   ├── services/
│   │   ├── cognito_service.py          # Reutilizado
│   │   ├── database_service.py         # Reutilizado
│   │   └── permissions_service.py      # Reutilizado
│   └── utils/
│       ├── validators.py                # Reutilizado
│       └── response_builder.py         # Reutilizado
│
└── lambdas/
    ├── identity-mgmt-api/              # Lambda administrativa (existente)
    │   └── ...
    │
    └── auth-api/                        # Nueva Lambda de autenticación
        ├── lambda_function.py           # Handler principal
        ├── requirements.txt             # Dependencias
        ├── README.md                    # Documentación
        │
        ├── services/
        │   └── auth_service.py          # Nuevo: Lógica de autenticación
        │
        ├── utils/
        │   ├── token_generator.py       # Nuevo: Generación de JWT
        │   └── token_validator.py       # Nuevo: Validación de JWT
        │
        └── config/
            └── keys/                    # Claves RSA para JWT
                ├── private_key.pem      # Clave privada (en Secrets Manager)
                └── public_key.pem       # Clave pública (en código)
```

---

## 🔧 Implementación Detallada

### 1. Lambda Handler (`lambda_function.py`)

```python
"""
Auth API Lambda Function
========================
Lambda para autenticación de usuarios en aplicaciones de la plataforma.

Endpoints:
- POST /auth/login: Autenticación con Cognito
- POST /auth/verify: Validación de token JWT
"""

import json
import logging
from typing import Dict, Any

# Configurar logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Importar servicios
from services.auth_service import AuthService
from utils.response_builder import build_response, build_error_response
from utils.validators import validate_request

# Inicializar servicio
auth_service = None


def initialize_services():
    """Inicializar servicios en el primer invocación (lazy loading)"""
    global auth_service
    
    if auth_service is None:
        auth_service = AuthService()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handler principal de la Lambda
    
    Args:
        event: Evento de API Gateway
        context: Contexto de ejecución
        
    Returns:
        Response HTTP
    """
    request_id = context.aws_request_id if context else 'local'
    
    logger.info(f"[{request_id}] Iniciando procesamiento de request")
    
    try:
        # Inicializar servicios
        initialize_services()
        
        # Parsear body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extraer operación del path
        path = event.get('path', '')
        http_method = event.get('httpMethod', 'POST')
        
        logger.info(f"[{request_id}] {http_method} {path}")
        
        # Routing
        if path == '/auth/login' and http_method == 'POST':
            result = handle_login(body, request_id)
        elif path == '/auth/verify' and http_method == 'POST':
            result = handle_verify(body, request_id)
        else:
            return build_error_response(
                'NOT_FOUND',
                f'Endpoint no encontrado: {http_method} {path}',
                404
            )
        
        logger.info(f"[{request_id}] Operación completada exitosamente")
        return build_response(result)
        
    except ValueError as e:
        logger.error(f"[{request_id}] Error de validación: {str(e)}")
        return build_error_response('VALIDATION_ERROR', str(e), 400)
        
    except Exception as e:
        logger.error(f"[{request_id}] Error inesperado: {str(e)}", exc_info=True)
        return build_error_response(
            'INTERNAL_ERROR',
            'Error interno del servidor',
            500,
            {'detail': str(e)}
        )


def handle_login(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """
    Handler para login
    
    Args:
        body: Datos del request
        request_id: ID del request
        
    Returns:
        Resultado del login
    """
    logger.info(f"[{request_id}] Procesando login")
    
    # Validar parámetros
    email = body.get('email')
    password = body.get('password')
    
    if not email or not password:
        raise ValueError('Los parámetros "email" y "password" son requeridos')
    
    # Autenticar
    result = auth_service.login(email, password)
    
    logger.info(f"[{request_id}] Login exitoso para {email}")
    
    return result


def handle_verify(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """
    Handler para verificación de token
    
    Args:
        body: Datos del request
        request_id: ID del request
        
    Returns:
        Resultado de la verificación
    """
    logger.info(f"[{request_id}] Verificando token")
    
    # Validar parámetros
    token = body.get('token')
    
    if not token:
        raise ValueError('El parámetro "token" es requerido')
    
    # Verificar
    result = auth_service.verify_token(token)
    
    logger.info(f"[{request_id}] Token verificado exitosamente")
    
    return result
```

### 2. Auth Service (`services/auth_service.py`)

```python
"""
Auth Service
============
Servicio para autenticación y generación de tokens JWT
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any

# Importar servicios compartidos
import sys
sys.path.append('/opt/python')  # Layer con código compartido

from services.cognito_service import CognitoService
from services.database_service import DatabaseService
from services.permissions_service import PermissionsService
from utils.token_generator import TokenGenerator
from utils.token_validator import TokenValidator

logger = logging.getLogger()


class AuthService:
    """Servicio de autenticación"""
    
    def __init__(self):
        """Inicializar servicios"""
        self.cognito_service = CognitoService()
        self.database_service = DatabaseService()
        self.permissions_service = PermissionsService()
        self.token_generator = TokenGenerator()
        self.token_validator = TokenValidator()
    
    def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Autenticar usuario y generar token con permisos
        
        Args:
            email: Email del usuario
            password: Contraseña
            
        Returns:
            Dict con token y datos del usuario
        """
        logger.info(f"Autenticando usuario: {email}")
        
        # 1. Autenticar con Cognito
        try:
            cognito_response = self.cognito_service.authenticate_user(email, password)
        except Exception as e:
            logger.error(f"Error en autenticación Cognito: {e}")
            raise ValueError(f'Credenciales inválidas: {str(e)}')
        
        # Extraer información del usuario
        user_id = cognito_response['user_id']
        user_attributes = cognito_response.get('attributes', {})
        
        # 2. Obtener permisos del usuario
        try:
            permissions = self.permissions_service.get_user_permissions(user_id)
        except Exception as e:
            logger.warning(f"Error obteniendo permisos: {e}")
            permissions = {'permissions': []}
        
        # 3. Preparar datos del usuario
        user_data = {
            'userId': user_id,
            'email': email,
            'name': user_attributes.get('name', email),
            'groups': cognito_response.get('groups', [])
        }
        
        # 4. Generar token JWT con permisos
        token_payload = {
            'sub': user_id,
            'email': email,
            'name': user_data['name'],
            'groups': user_data['groups'],
            'permissions': permissions.get('permissions', []),
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(minutes=30)  # 30 minutos
        }
        
        token = self.token_generator.generate(token_payload)
        
        # 5. Preparar respuesta
        result = {
            'success': True,
            'token': token,
            'user': user_data,
            'permissions': permissions.get('permissions', []),
            'expiresAt': token_payload['exp'].isoformat() + 'Z'
        }
        
        logger.info(f"Login exitoso para {email}")
        
        return result
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verificar y decodificar token JWT
        
        Args:
            token: Token JWT a verificar
            
        Returns:
            Dict con información del token
        """
        logger.info("Verificando token")
        
        try:
            # Validar y decodificar token
            payload = self.token_validator.validate(token)
            
            # Preparar respuesta
            result = {
                'valid': True,
                'user': {
                    'userId': payload['sub'],
                    'email': payload['email'],
                    'name': payload.get('name', payload['email']),
                    'groups': payload.get('groups', [])
                },
                'permissions': payload.get('permissions', []),
                'expiresAt': datetime.fromtimestamp(payload['exp']).isoformat() + 'Z'
            }
            
            logger.info(f"Token válido para usuario {payload['email']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Token inválido: {e}")
            return {
                'valid': False,
                'error': str(e)
            }
```

### 3. Token Generator (`utils/token_generator.py`)

```python
"""
Token Generator
===============
Generador de tokens JWT con firma RSA
"""

import jwt
import logging
from datetime import datetime
from typing import Dict, Any
import boto3
import json

logger = logging.getLogger()


class TokenGenerator:
    """Generador de tokens JWT"""
    
    def __init__(self):
        """Inicializar generador"""
        self.private_key = self._load_private_key()
        self.algorithm = 'RS256'
    
    def _load_private_key(self) -> str:
        """
        Cargar clave privada desde Secrets Manager
        
        Returns:
            Clave privada en formato PEM
        """
        try:
            secrets_client = boto3.client('secretsmanager', region_name='eu-west-1')
            response = secrets_client.get_secret_value(
                SecretId='auth-jwt-private-key'
            )
            secret = json.loads(response['SecretString'])
            return secret['private_key']
        except Exception as e:
            logger.error(f"Error cargando clave privada: {e}")
            raise Exception("No se pudo cargar la clave privada para firmar tokens")
    
    def generate(self, payload: Dict[str, Any]) -> str:
        """
        Generar token JWT
        
        Args:
            payload: Datos a incluir en el token
            
        Returns:
            Token JWT firmado
        """
        try:
            # Convertir datetime a timestamp
            if isinstance(payload.get('iat'), datetime):
                payload['iat'] = int(payload['iat'].timestamp())
            if isinstance(payload.get('exp'), datetime):
                payload['exp'] = int(payload['exp'].timestamp())
            
            # Generar token
            token = jwt.encode(
                payload,
                self.private_key,
                algorithm=self.algorithm
            )
            
            return token
            
        except Exception as e:
            logger.error(f"Error generando token: {e}")
            raise Exception(f"Error generando token: {str(e)}")
```

### 4. Token Validator (`utils/token_validator.py`)

```python
"""
Token Validator
===============
Validador de tokens JWT con verificación de firma RSA
"""

import jwt
import logging
from typing import Dict, Any

logger = logging.getLogger()

# Clave pública (puede estar en el código o en S3)
PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
-----END PUBLIC KEY-----"""


class TokenValidator:
    """Validador de tokens JWT"""
    
    def __init__(self):
        """Inicializar validador"""
        self.public_key = PUBLIC_KEY
        self.algorithm = 'RS256'
    
    def validate(self, token: str) -> Dict[str, Any]:
        """
        Validar y decodificar token JWT
        
        Args:
            token: Token JWT a validar
            
        Returns:
            Payload del token
            
        Raises:
            Exception: Si el token es inválido
        """
        try:
            # Decodificar y validar token
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.algorithm]
            )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise Exception("Token expirado")
        except jwt.InvalidTokenError as e:
            raise Exception(f"Token inválido: {str(e)}")
        except Exception as e:
            raise Exception(f"Error validando token: {str(e)}")
```

### 5. Requirements (`requirements.txt`)

```txt
# AWS SDK
boto3==1.42.59
botocore==1.42.59

# JWT
PyJWT==2.11.0
cryptography==42.0.5

# Database
psycopg2-binary==2.9.9

# Utilities
python-dateutil==2.9.0
```

---

## 🔐 Gestión de Claves RSA

### Generar Par de Claves

```bash
# Generar clave privada
openssl genrsa -out private_key.pem 2048

# Extraer clave pública
openssl rsa -in private_key.pem -pubout -out public_key.pem

# Ver clave privada
cat private_key.pem

# Ver clave pública
cat public_key.pem
```

### Almacenar Clave Privada en Secrets Manager

```bash
# Crear secret con clave privada
aws secretsmanager create-secret \
  --name auth-jwt-private-key \
  --description "Clave privada para firmar tokens JWT de Auth Lambda" \
  --secret-string "{\"private_key\":\"$(cat private_key.pem | sed ':a;N;$!ba;s/\n/\\n/g')\"}" \
  --region eu-west-1
```

### Clave Pública en Código

```python
# La clave pública puede estar en el código (no es sensible)
# O en S3 para facilitar rotación

PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
-----END PUBLIC KEY-----"""
```

---

## 📦 Estructura del Token JWT

### Payload del Token

```json
{
  "sub": "user-uuid-123",
  "email": "user@example.com",
  "name": "John Doe",
  "groups": ["developers", "admins"],
  "permissions": [
    {
      "type": "application",
      "id": "app-1",
      "name": "Gestión Demanda",
      "permission_type": "read_write",
      "is_active": true,
      "granted_at": "2026-01-01T00:00:00Z",
      "expires_at": null
    },
    {
      "type": "module",
      "id": "module-1",
      "app_id": "app-1",
      "name": "Solicitudes",
      "permission_type": "admin",
      "is_active": true,
      "granted_at": "2026-01-01T00:00:00Z",
      "expires_at": "2026-12-31T23:59:59Z"
    }
  ],
  "iat": 1709370000,
  "exp": 1709371800
}
```

### Token Completo

```
eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLXV1aWQtMTIzIiwiZW1haWwiOiJ1c2VyQGV4YW1wbGUuY29tIiwibmFtZSI6IkpvaG4gRG9lIiwiZ3JvdXBzIjpbImRldmVsb3BlcnMiLCJhZG1pbnMiXSwicGVybWlzc2lvbnMiOlt7InR5cGUiOiJhcHBsaWNhdGlvbiIsImlkIjoiYXBwLTEiLCJuYW1lIjoiR2VzdGnDs24gRGVtYW5kYSIsInBlcm1pc3Npb25fdHlwZSI6InJlYWRfd3JpdGUiLCJpc19hY3RpdmUiOnRydWUsImdyYW50ZWRfYXQiOiIyMDI2LTAxLTAxVDAwOjAwOjAwWiIsImV4cGlyZXNfYXQiOm51bGx9XSwiaWF0IjoxNzA5MzcwMDAwLCJleHAiOjE3MDkzNzE4MDB9.signature...
```

---

## 🚀 Despliegue

### 1. Crear Layer con Código Compartido

```bash
# Crear directorio para layer
mkdir -p /tmp/auth-shared-layer/python

# Copiar servicios compartidos
cp -r backend/shared/* /tmp/auth-shared-layer/python/

# Crear ZIP
cd /tmp/auth-shared-layer
zip -r auth-shared-layer.zip python/

# Publicar layer
aws lambda publish-layer-version \
  --layer-name auth-shared-services \
  --description "Servicios compartidos para Auth Lambda" \
  --zip-file fileb://auth-shared-layer.zip \
  --compatible-runtimes python3.12 \
  --region eu-west-1
```

### 2. Empaquetar Lambda

```bash
# Ir al directorio de la lambda
cd backend/lambdas/auth-api

# Instalar dependencias
pip3 install -r requirements.txt -t .

# Crear ZIP
zip -r auth-lambda.zip . -x "*.pyc" -x "__pycache__/*" -x "tests/*"
```

### 3. Crear Lambda

```bash
# Crear función Lambda
aws lambda create-function \
  --function-name auth-api-lmbd \
  --runtime python3.12 \
  --role arn:aws:iam::ACCOUNT_ID:role/lambda-execution-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://auth-lambda.zip \
  --timeout 30 \
  --memory-size 512 \
  --environment Variables="{
    DB_SECRET_NAME=identity-mgmt-dev-db-admin,
    USER_POOL_ID=eu-west-1_XXXXXX,
    USER_POOL_CLIENT_ID=XXXXXXXXXX,
    AWS_REGION=eu-west-1
  }" \
  --layers arn:aws:lambda:eu-west-1:ACCOUNT_ID:layer:auth-shared-services:1 \
  --region eu-west-1
```

### 4. Configurar API Gateway

```bash
# Crear API REST
aws apigateway create-rest-api \
  --name "Auth API" \
  --description "API de autenticación para aplicaciones" \
  --region eu-west-1

# Crear recursos y métodos
# /auth/login (POST)
# /auth/verify (POST)

# Configurar integración con Lambda
# Configurar CORS
# Desplegar API
```

---

## 🧪 Testing

### Test de Login

```bash
curl -X POST https://api.example.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'

# Respuesta esperada:
{
  "success": true,
  "token": "eyJhbGc...",
  "user": {
    "userId": "uuid-123",
    "email": "user@example.com",
    "name": "John Doe",
    "groups": ["developers"]
  },
  "permissions": [...],
  "expiresAt": "2026-03-02T12:00:00Z"
}
```

### Test de Verify

```bash
curl -X POST https://api.example.com/auth/verify \
  -H "Content-Type: application/json" \
  -d '{
    "token": "eyJhbGc..."
  }'

# Respuesta esperada:
{
  "valid": true,
  "user": {
    "userId": "uuid-123",
    "email": "user@example.com",
    "name": "John Doe",
    "groups": ["developers"]
  },
  "permissions": [...],
  "expiresAt": "2026-03-02T12:00:00Z"
}
```

---

## 📊 Configuración de Infraestructura

### Variables de Entorno

```yaml
DB_SECRET_NAME: identity-mgmt-dev-db-admin
USER_POOL_ID: eu-west-1_XXXXXX
USER_POOL_CLIENT_ID: XXXXXXXXXX
AWS_REGION: eu-west-1
JWT_EXPIRATION_MINUTES: 30
```

### Políticas IAM Necesarias

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:eu-west-1:*:secret:identity-mgmt-dev-db-admin-*",
        "arn:aws:secretsmanager:eu-west-1:*:secret:auth-jwt-private-key-*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "cognito-idp:InitiateAuth",
        "cognito-idp:GetUser"
      ],
      "Resource": "arn:aws:cognito-idp:eu-west-1:*:userpool/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

---

## 📝 Uso en Aplicaciones Cliente

### JavaScript/TypeScript

```typescript
// auth-client.ts
class AuthClient {
  private token: string | null = null;
  private permissions: any[] = [];
  
  async login(email: string, password: string) {
    const response = await fetch('https://api.example.com/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    
    const data = await response.json();
    
    if (data.success) {
      this.token = data.token;
      this.permissions = data.permissions;
      localStorage.setItem('auth_token', data.token);
      return data;
    }
    
    throw new Error('Login failed');
  }
  
  async verifyToken(token: string) {
    const response = await fetch('https://api.example.com/auth/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token })
    });
    
    return await response.json();
  }
  
  hasPermission(appId: string, moduleId?: string): boolean {
    if (!this.token) return false;
    
    // Decodificar token localmente
    const payload = this.decodeToken(this.token);
    const permissions = payload.permissions || [];
    
    // Verificar permiso de aplicación
    const appPerm = permissions.find(p => 
      p.type === 'application' && 
      p.id === appId && 
      p.is_active
    );
    
    if (!appPerm) return false;
    
    // Si se especifica módulo, verificar también
    if (moduleId) {
      const modulePerm = permissions.find(p =>
        p.type === 'module' &&
        p.id === moduleId &&
        p.app_id === appId &&
        p.is_active
      );
      return !!modulePerm;
    }
    
    return true;
  }
  
  private decodeToken(token: string): any {
    const parts = token.split('.');
    if (parts.length !== 3) throw new Error('Invalid token');
    
    const payload = parts[1];
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(decoded);
  }
}

// Uso
const auth = new AuthClient();

// Login
await auth.login('user@example.com', 'password');

// Verificar permiso
if (auth.hasPermission('app-1')) {
  // Usuario tiene acceso a la aplicación
}

if (auth.hasPermission('app-1', 'module-1')) {
  // Usuario tiene acceso al módulo específico
}
```

### Python

```python
# auth_client.py
import requests
import jwt
from typing import Dict, Any, Optional

class AuthClient:
    def __init__(self, api_url: str):
        self.api_url = api_url
        self.token: Optional[str] = None
        self.permissions: list = []
    
    def login(self, email: str, password: str) -> Dict[str, Any]:
        """Login y obtener token"""
        response = requests.post(
            f"{self.api_url}/auth/login",
            json={"email": email, "password": password}
        )
        response.raise_for_status()
        
        data = response.json()
        self.token = data['token']
        self.permissions = data['permissions']
        
        return data
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verificar token"""
        response = requests.post(
            f"{self.api_url}/auth/verify",
            json={"token": token}
        )
        response.raise_for_status()
        
        return response.json()
    
    def has_permission(self, app_id: str, module_id: Optional[str] = None) -> bool:
        """Verificar si usuario tiene permiso"""
        if not self.token:
            return False
        
        # Decodificar token (sin verificar firma)
        payload = jwt.decode(self.token, options={"verify_signature": False})
        permissions = payload.get('permissions', [])
        
        # Verificar permiso de aplicación
        app_perm = next(
            (p for p in permissions 
             if p['type'] == 'application' 
             and p['id'] == app_id 
             and p['is_active']),
            None
        )
        
        if not app_perm:
            return False
        
        # Si se especifica módulo, verificar también
        if module_id:
            module_perm = next(
                (p for p in permissions
                 if p['type'] == 'module'
                 and p['id'] == module_id
                 and p['app_id'] == app_id
                 and p['is_active']),
                None
            )
            return module_perm is not None
        
        return True

# Uso
auth = AuthClient('https://api.example.com')

# Login
auth.login('user@example.com', 'password')

# Verificar permiso
if auth.has_permission('app-1'):
    print("Usuario tiene acceso a la aplicación")

if auth.has_permission('app-1', 'module-1'):
    print("Usuario tiene acceso al módulo")
```

---

## 📋 Checklist de Implementación

### Fase 1: Preparación
- [ ] Crear estructura de carpetas `backend/lambdas/auth-api`
- [ ] Crear carpeta `backend/shared` con servicios comunes
- [ ] Mover servicios compartidos a `backend/shared`
- [ ] Generar par de claves RSA
- [ ] Almacenar clave privada en Secrets Manager

### Fase 2: Desarrollo
- [ ] Implementar `lambda_function.py`
- [ ] Implementar `services/auth_service.py`
- [ ] Implementar `utils/token_generator.py`
- [ ] Implementar `utils/token_validator.py`
- [ ] Crear `requirements.txt`
- [ ] Crear tests unitarios

### Fase 3: Infraestructura
- [ ] Crear Layer con código compartido
- [ ] Crear función Lambda
- [ ] Configurar variables de entorno
- [ ] Configurar políticas IAM
- [ ] Crear API Gateway
- [ ] Configurar endpoints
- [ ] Configurar CORS

### Fase 4: Testing
- [ ] Test de login con credenciales válidas
- [ ] Test de login con credenciales inválidas
- [ ] Test de verify con token válido
- [ ] Test de verify con token expirado
- [ ] Test de verify con token inválido
- [ ] Test de permisos en token

### Fase 5: Documentación
- [ ] Documentar API (Swagger/OpenAPI)
- [ ] Crear ejemplos de uso
- [ ] Documentar integración para aplicaciones
- [ ] Crear guía de troubleshooting

### Fase 6: Despliegue
- [ ] Desplegar en dev
- [ ] Pruebas de integración
- [ ] Desplegar en pre
- [ ] Pruebas de carga
- [ ] Desplegar en pro

---

## 🎯 Próximos Pasos

1. **Revisar y aprobar** este diseño
2. **Generar claves RSA** para firma de tokens
3. **Crear estructura** de carpetas
4. **Comenzar implementación** de Auth Lambda
5. **Tests y despliegue** en dev

---

## 📚 Referencias

- [AWS Lambda Python](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html)
- [PyJWT Documentation](https://pyjwt.readthedocs.io/)
- [AWS Cognito Authentication](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-authentication-flow.html)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
