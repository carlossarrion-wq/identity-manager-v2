# Sistema de Login con Herramientas

Sistema de autenticación centralizado usando AWS Cognito y gestión de permisos con PostgreSQL.

## 📋 Descripción

Lambda de autenticación que proporciona:
- **Login**: Autenticación con Cognito + Permisos en token JWT
- **Verify**: Validación de token JWT

## 🏗️ Arquitectura

```
┌─────────────┐         ┌──────────────┐         ┌──────────┐         ┌──────────┐
│   Cliente   │────────▶│  Auth Lambda │────────▶│ Cognito  │         │   RDS    │
│ (Frontend)  │         │              │         │          │         │PostgreSQL│
│             │◀────────│              │◀────────│          │◀────────│          │
└─────────────┘         └──────────────┘         └──────────┘         └──────────┘
```

## 📁 Estructura del Proyecto

```
SistemaLoginHerramientas/
├── backend/
│   ├── shared/                      # Servicios compartidos
│   │   ├── services/
│   │   │   ├── cognito_service.py   # Autenticación con Cognito
│   │   │   ├── database_service.py  # Conexión a PostgreSQL
│   │   │   ├── permissions_service.py # Consulta de permisos
│   │   │   └── jwt_service.py       # Generación/validación JWT
│   │   └── utils/
│   │       ├── response_builder.py  # Respuestas HTTP
│   │       └── validators.py        # Validaciones
│   │
│   └── auth-lambda/                 # Lambda de autenticación
│       ├── lambda_function.py       # Handler principal
│       ├── auth_service.py          # Lógica de autenticación
│       ├── config.py                # Configuración
│       └── README.md
│
├── local_server.py                  # Servidor Flask para testing local
├── requirements-local.txt           # Dependencias para testing local
└── README.md                        # Este archivo
```

## 🚀 Instalación y Configuración

### 1. Instalar Dependencias

```bash
pip install -r requirements-local.txt
```

### 2. Configurar Variables de Entorno (Opcional)

Las credenciales de AWS se toman automáticamente de tu configuración local (`~/.aws/credentials`).

Si quieres sobrescribir la configuración por defecto:

```bash
# Windows (PowerShell)
$env:COGNITO_USER_POOL_ID="eu-west-1_UaMIbG9pD"
$env:COGNITO_CLIENT_ID="15b1ub3navqgh0ushcqo2ngfsk"
$env:AWS_REGION="eu-west-1"
$env:DB_SECRET_NAME="identity-mgmt-dev-db-admin"
$env:JWT_SECRET_NAME="identity-mgmt-dev-jwt-secret"
$env:JWT_EXPIRATION_HOURS="1"

# Linux/Mac
export COGNITO_USER_POOL_ID="eu-west-1_UaMIbG9pD"
export COGNITO_CLIENT_ID="15b1ub3navqgh0ushcqo2ngfsk"
export AWS_REGION="eu-west-1"
export DB_SECRET_NAME="identity-mgmt-dev-db-admin"
export JWT_SECRET_NAME="identity-mgmt-dev-jwt-secret"
export JWT_EXPIRATION_HOURS="1"
```

### 3. Iniciar Servidor Local

```bash
python local_server.py
```

El servidor estará disponible en: `http://localhost:5000`

## 📡 Endpoints

### POST /auth/login

Autenticar usuario con Cognito y obtener token JWT con permisos.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response (Success):**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "userId": "uuid-123",
    "email": "user@example.com",
    "name": "John Doe",
    "groups": ["developers"]
  },
  "permissions": [
    {
      "scope": "application",
      "resource_id": "uuid-app-1",
      "resource_name": "Gestión Demanda",
      "permission_type": "read_write",
      "permission_level": 50,
      "is_active": true,
      "status": "active",
      "granted_at": "2026-01-01T00:00:00Z",
      "expires_at": null
    }
  ],
  "expiresAt": "2026-03-02T18:00:00Z"
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "INVALID_CREDENTIALS",
  "message": "Email o contraseña incorrectos"
}
```

### POST /auth/verify

Verificar y decodificar token JWT.

**Request:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (Valid):**
```json
{
  "valid": true,
  "user": {
    "userId": "uuid-123",
    "email": "user@example.com",
    "name": "John Doe",
    "groups": ["developers"]
  },
  "permissions": [...],
  "expiresAt": "2026-03-02T18:00:00Z"
}
```

**Response (Invalid):**
```json
{
  "valid": false,
  "error": "Token expirado"
}
```

## 🧪 Testing

### Con curl

**Login:**
```bash
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'
```

**Verify:**
```bash
curl -X POST http://localhost:5000/auth/verify \
  -H "Content-Type: application/json" \
  -d '{"token":"eyJhbGc..."}'
```

### Con Python

```python
import requests

# Login
response = requests.post('http://localhost:5000/auth/login', json={
    'email': 'user@example.com',
    'password': 'password123'
})
data = response.json()
token = data['token']

# Verify
response = requests.post('http://localhost:5000/auth/verify', json={
    'token': token
})
print(response.json())
```

## 🔐 Configuración de Cognito

### User Pool
- **ID**: `eu-west-1_UaMIbG9pD`
- **Nombre**: `identity-manager-dev-pool`
- **Región**: `eu-west-1`

### App Client
- **ID**: `15b1ub3navqgh0ushcqo2ngfsk`
- **Nombre**: `auth-login-client`
- **Flujos habilitados**:
  - ✅ ALLOW_USER_AUTH
  - ✅ ALLOW_USER_PASSWORD_AUTH
  - ✅ ALLOW_USER_SRP_AUTH
  - ✅ ALLOW_REFRESH_TOKEN_AUTH

## 🗄️ Base de Datos

### Secreto
- **Nombre**: `identity-mgmt-dev-db-admin`
- **Contiene**: host, port, dbname, username, password

### Tablas Principales
- `identity-manager-app-permissions-tbl`: Permisos de aplicaciones
- `identity-manager-module-permissions-tbl`: Permisos de módulos
- `identity-manager-applications-tbl`: Catálogo de aplicaciones
- `identity-manager-modules-tbl`: Catálogo de módulos

## 🔑 JWT Token

### Estructura del Token

```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "name": "John Doe",
  "groups": ["developers"],
  "permissions": [...],
  "iss": "auth-lambda",
  "aud": ["auth-login"],
  "iat": 1709370000,
  "exp": 1709373600
}
```

### Características
- **Algoritmo**: HMAC (HS256)
- **Validez**: 1 hora
- **Incluye**: Permisos completos del usuario

## 📦 Despliegue en AWS Lambda

### 1. Crear requirements.txt para Lambda

```txt
boto3==1.42.59
botocore==1.42.59
PyJWT==2.11.0
cryptography==42.0.5
psycopg2-binary==2.9.9
python-dateutil==2.9.0
```

### 2. Empaquetar Lambda

```bash
cd backend/auth-lambda
pip install -r requirements.txt -t .
zip -r auth-lambda.zip . -x "*.pyc" -x "__pycache__/*"
```

### 3. Crear Lambda en AWS

```bash
aws lambda create-function \
  --function-name auth-api-lambda \
  --runtime python3.12 \
  --role arn:aws:iam::ACCOUNT_ID:role/lambda-execution-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://auth-lambda.zip \
  --timeout 30 \
  --memory-size 512 \
  --environment Variables="{
    COGNITO_USER_POOL_ID=eu-west-1_UaMIbG9pD,
    COGNITO_CLIENT_ID=15b1ub3navqgh0ushcqo2ngfsk,
    AWS_REGION=eu-west-1,
    DB_SECRET_NAME=identity-mgmt-dev-db-admin,
    JWT_SECRET_NAME=identity-mgmt-dev-jwt-secret,
    JWT_EXPIRATION_HOURS=1
  }" \
  --region eu-west-1
```

### 4. Configurar API Gateway

Crear API REST con endpoints:
- `POST /auth/login`
- `POST /auth/verify`

## 🛠️ Troubleshooting

### Error: "Email o contraseña incorrectos"
- Verifica que el usuario existe en Cognito
- Verifica que la contraseña es correcta
- Verifica que el usuario está confirmado

### Error: "No se pudo cargar la clave privada"
- Verifica que el secreto `identity-mgmt-dev-jwt-secret` existe
- Verifica que tienes permisos para acceder al secreto

### Error: "Error conectando a PostgreSQL"
- Verifica que el secreto `identity-mgmt-dev-db-admin` existe
- Verifica la conectividad a la base de datos
- Verifica que estás en la VPC correcta (si aplica)

## 📚 Referencias

- [AWS Cognito Documentation](https://docs.aws.amazon.com/cognito/)
- [PyJWT Documentation](https://pyjwt.readthedocs.io/)
- [Flask Documentation](https://flask.palletsprojects.com/)

## 👥 Autor

Sistema desarrollado para gestión centralizada de autenticación y permisos.

## 📄 Licencia

Uso interno.