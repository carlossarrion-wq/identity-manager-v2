# 🔐 Flujo de Autorización - Identity Manager

## 📋 Resumen

Este documento explica **cómo se verifica que un usuario tiene autorización** para acceder a la aplicación Identity Manager y al proxy de Bedrock.

---

## 🎯 Niveles de Autorización

La aplicación tiene **3 niveles de autorización**:

### **Nivel 1: Frontend (Dashboard)**
- Verifica que el usuario tenga un token válido
- Controla acceso a las páginas del dashboard

### **Nivel 2: Backend (Auth Lambda)**
- Valida credenciales con Cognito
- Verifica permisos de aplicación en base de datos
- Genera token JWT con información del usuario

### **Nivel 3: Proxy Bedrock**
- Valida token JWT
- Verifica cuotas diarias
- Controla acceso a modelos de AWS Bedrock

---

## 🔄 Flujo Completo de Autorización

```
┌─────────────┐
│   Usuario   │
└──────┬──────┘
       │
       │ 1. Accede a login.html
       ▼
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (login.html)                     │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ 1. Usuario ingresa email y password                │    │
│  │ 2. Se envía POST a /auth/login con:                │    │
│  │    - email                                          │    │
│  │    - password                                       │    │
│  │    - app_id: "e61e1af9-8992-4bdf-be65-9cad86f34da0"│    │
│  └────────────────────────────────────────────────────┘    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ 2. POST /auth/login
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              BACKEND (Auth Lambda - auth_service.py)         │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ PASO 1: Autenticación con Cognito                  │    │
│  │ ────────────────────────────────────────────────   │    │
│  │ • Llama a cognito-idp:InitiateAuth                 │    │
│  │ • Valida email y password                          │    │
│  │ • Obtiene user_id, email, grupos                   │    │
│  │                                                     │    │
│  │ ✅ Si es válido → Continúa                         │    │
│  │ ❌ Si es inválido → Error 401                      │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ PASO 2: Obtener permisos de base de datos          │    │
│  │ ────────────────────────────────────────────────   │    │
│  │ • Consulta PostgreSQL:                             │    │
│  │   SELECT * FROM user_permissions                   │    │
│  │   WHERE user_id = ? AND status = 'active'          │    │
│  │                                                     │    │
│  │ • Obtiene lista de permisos del usuario            │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ PASO 3: Validar permiso de aplicación              │    │
│  │ ────────────────────────────────────────────────   │    │
│  │ • Busca en permisos:                               │    │
│  │   - scope = 'application'                          │    │
│  │   - resource_id = app_id recibido                  │    │
│  │   - status = 'active'                              │    │
│  │   - is_active = true                               │    │
│  │                                                     │    │
│  │ ✅ Si tiene permiso → Continúa                     │    │
│  │ ❌ Si NO tiene permiso → Error 403                 │    │
│  │    "Access denied. You do not have permissions"    │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ PASO 4: Generar token JWT                          │    │
│  │ ────────────────────────────────────────────────   │    │
│  │ • Crea JWT con:                                    │    │
│  │   - sub: user_id                                   │    │
│  │   - email: email                                   │    │
│  │   - groups: grupos de Cognito                      │    │
│  │   - exp: 1 hora                                    │    │
│  │                                                     │    │
│  │ • Firma con JWT_SECRET_KEY                         │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ RESPUESTA:                                          │    │
│  │ {                                                   │    │
│  │   "success": true,                                  │    │
│  │   "token": "eyJhbGc...",                            │    │
│  │   "user": { userId, email, name, groups },          │    │
│  │   "permissions": [...],                             │    │
│  │   "expiresAt": "2026-03-09T11:00:00Z"              │    │
│  │ }                                                   │    │
│  └────────────────────────────────────────────────────┘    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ 3. Respuesta con token
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (login.html)                     │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ 1. Guarda en localStorage:                          │    │
│  │    - auth_token                                     │    │
│  │    - user_data                                      │    │
│  │    - token_expires_at                               │    │
│  │                                                     │    │
│  │ 2. Redirige a /dashboard/index.html                │    │
│  └────────────────────────────────────────────────────┘    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ 4. Accede al dashboard
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              FRONTEND (Dashboard - auth-guard.js)            │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ VERIFICACIÓN AUTOMÁTICA (cada página):              │    │
│  │                                                     │    │
│  │ 1. Lee localStorage:                                │    │
│  │    - auth_token                                     │    │
│  │    - token_expires_at                               │    │
│  │                                                     │    │
│  │ 2. Verifica:                                        │    │
│  │    ✅ Token existe                                  │    │
│  │    ✅ Token no ha expirado                          │    │
│  │                                                     │    │
│  │ 3. Si falla → Redirige a login.html                │    │
│  │                                                     │    │
│  │ 4. Verificación periódica cada 30 segundos         │    │
│  └────────────────────────────────────────────────────┘    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ 5. Usuario usa API de Bedrock
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              PROXY BEDROCK (middleware.go)                   │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ PASO 1: Extraer token                              │    │
│  │ ────────────────────────────────────────────────   │    │
│  │ • Lee header Authorization: Bearer <token>          │    │
│  │ • O header x-api-key: <token>                      │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ PASO 2: Rate Limiting                              │    │
│  │ ────────────────────────────────────────────────   │    │
│  │ • Verifica intentos por IP                         │    │
│  │ • Verifica intentos por token                      │    │
│  │                                                     │    │
│  │ ❌ Si excede límite → Error 401 + Retry-After      │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ PASO 3: Validar token en base de datos             │    │
│  │ ────────────────────────────────────────────────   │    │
│  │ • Calcula hash del token                           │    │
│  │ • Consulta PostgreSQL:                             │    │
│  │   SELECT * FROM api_keys                           │    │
│  │   WHERE token_hash = ? AND is_revoked = false      │    │
│  │                                                     │    │
│  │ ✅ Si existe y no está revocado → Continúa         │    │
│  │ ❌ Si no existe o está revocado → Error 401        │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ PASO 4: Validar firma JWT                          │    │
│  │ ────────────────────────────────────────────────   │    │
│  │ • Decodifica JWT                                   │    │
│  │ • Verifica firma con JWT_SECRET_KEY                │    │
│  │ • Verifica expiración                              │    │
│  │                                                     │    │
│  │ ✅ Si es válido → Continúa                         │    │
│  │ ❌ Si expiró → Intenta auto-regeneración           │    │
│  │ ❌ Si firma inválida → Error 401                   │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ PASO 5: Verificar cuota diaria                     │    │
│  │ ────────────────────────────────────────────────   │    │
│  │ • Consulta PostgreSQL:                             │    │
│  │   - Obtiene daily_limit del usuario                │    │
│  │   - Cuenta requests_today                          │    │
│  │   - Verifica si está bloqueado                     │    │
│  │                                                     │    │
│  │ • Actualiza contador de requests                   │    │
│  │                                                     │    │
│  │ ✅ Si dentro de cuota → Continúa                   │    │
│  │ ❌ Si excede cuota → Error 401                     │    │
│  │    + Headers: X-RateLimit-*                        │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ PASO 6: Crear contexto de usuario                  │    │
│  │ ────────────────────────────────────────────────   │    │
│  │ • Extrae del JWT:                                  │    │
│  │   - UserID, Email, Team, Person                    │    │
│  │   - IAMUsername, IAMGroups                         │    │
│  │   - DefaultInferenceProfile                        │    │
│  │                                                     │    │
│  │ • Añade al contexto de la request                  │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ ✅ AUTORIZACIÓN EXITOSA                            │    │
│  │                                                     │    │
│  │ • Request continúa a AWS Bedrock                   │    │
│  │ • Se registra uso en base de datos                 │    │
│  │ • Se calculan costos                               │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔑 Mecanismos de Autorización Detallados

### **1. Frontend: auth-guard.js**

**Ubicación**: `frontend/dashboard/js/auth-guard.js`

**Función**: Proteger páginas del dashboard

**Verificaciones**:
```javascript
// 1. Verificar que existe token
const token = localStorage.getItem('auth_token');
if (!token) {
    redirectToLogin();
}

// 2. Verificar que no ha expirado
const expiresAt = localStorage.getItem('token_expires_at');
if (new Date() >= new Date(expiresAt)) {
    clearAuth();
    redirectToLogin();
}

// 3. Verificación periódica cada 30 segundos
setInterval(checkAuth, 30000);
```

**Resultado**:
- ✅ **Autorizado**: Usuario puede ver la página
- ❌ **No autorizado**: Redirige a `/frontend/login.html`

---

### **2. Backend: Auth Lambda**

**Ubicación**: `backend/lambdas/auth-lambda/auth_service.py`

**Función**: Validar credenciales y permisos de aplicación

#### **2.1. Autenticación con Cognito**

```python
# Método: _authenticate_with_cognito()

# 1. Llamar a Cognito InitiateAuth
response = client.initiate_auth(
    ClientId=COGNITO_CLIENT_ID,
    AuthFlow='USER_PASSWORD_AUTH',
    AuthParameters={
        'USERNAME': email,
        'PASSWORD': password
    }
)

# 2. Obtener información del usuario
user_response = client.get_user(AccessToken=access_token)

# 3. Obtener grupos del usuario
groups_response = client.admin_list_groups_for_user(
    UserPoolId=COGNITO_USER_POOL_ID,
    Username=username
)
```

**Resultado**:
- ✅ **Válido**: Retorna `user_id`, `email`, `groups`
- ❌ **Inválido**: Lanza `ValueError('Email o contraseña incorrectos')`

#### **2.2. Obtener Permisos de Base de Datos**

```python
# Método: permissions_service.get_user_permissions()

# Consulta SQL
SELECT 
    up.permission_id,
    up.user_id,
    up.scope,
    up.resource_id,
    up.permission_type,
    up.permission_level,
    up.status,
    up.is_active,
    up.granted_at,
    up.expires_at,
    a.name as application_name
FROM user_permissions up
LEFT JOIN applications a ON up.resource_id = a.application_id
WHERE up.user_id = %s
  AND up.status = 'active'
  AND up.is_active = true
```

**Resultado**:
- Lista de permisos del usuario
- Incluye: `scope`, `resource_id`, `permission_type`, `permission_level`

#### **2.3. Validar Permiso de Aplicación**

```python
# Método: _validate_app_permission()

# Buscar permiso específico
app_permissions = [
    perm for perm in permissions
    if perm.get('scope') == 'application'
    and perm.get('resource_id') == required_app_id
    and perm.get('status') == 'active'
    and perm.get('is_active') is True
]

if not app_permissions:
    raise ValueError(f'INSUFFICIENT_PERMISSIONS:{required_app_id}')
```

**Resultado**:
- ✅ **Tiene permiso**: Continúa con generación de token
- ❌ **No tiene permiso**: Error 403
  ```json
  {
    "error": "Access denied. You do not have the necessary permissions to access this application"
  }
  ```

#### **2.4. Generar Token JWT**

```python
# Método: _generate_custom_token()

# Payload del token
payload = {
    'sub': user_id,
    'email': email,
    'name': name,
    'groups': groups,
    'iat': datetime.utcnow(),
    'exp': datetime.utcnow() + timedelta(hours=1),
    'iss': 'auth-lambda',
    'aud': ['auth-login']
}

# Firmar con secret key
token = jwt.encode(payload, secret_key, algorithm='HS256')
```

**Resultado**:
- Token JWT válido por 1 hora
- Incluye información del usuario y grupos
- **NO incluye permisos completos** (solo se validan en login)

---

### **3. Proxy Bedrock: middleware.go**

**Ubicación**: `proxy-bedrock/pkg/auth/middleware.go`

**Función**: Validar token JWT y controlar acceso a Bedrock

#### **3.1. Extraer Token**

```go
// Opción 1: Header Authorization
authHeader := r.Header.Get("Authorization")
tokenString, err := ExtractBearerToken(authHeader)

// Opción 2: Header x-api-key
apiKey := r.Header.Get("x-api-key")
tokenString = apiKey
```

#### **3.2. Rate Limiting**

```go
// Por IP
allowed, retryAfter := am.rateLimiter.CheckIP(clientIP)
if !allowed {
    return Error401("too many attempts from IP")
}

// Por Token
tokenHash := HashToken(tokenString)
allowed, retryAfter = am.rateLimiter.CheckToken(tokenHash)
if !allowed {
    return Error401("too many attempts with this token")
}
```

#### **3.3. Validar Token en Base de Datos**

```go
// Consulta SQL
SELECT 
    user_id,
    inference_profile,
    is_revoked,
    created_at,
    expires_at
FROM api_keys
WHERE token_hash = $1
  AND is_revoked = false
```

**Verificaciones**:
- ✅ Token existe en BD
- ✅ No está revocado (`is_revoked = false`)
- ✅ `user_id` coincide con el del JWT

#### **3.4. Validar Firma JWT**

```go
// Decodificar y validar
claims, err := ValidateToken(tokenString, jwtConfig.SecretKey)

// Verificaciones:
// - Firma válida
// - No expirado
// - Issuer correcto
// - Audience correcto
```

**Si expira**:
- Intenta auto-regeneración (si está habilitada)
- Llama a Lambda API para generar nuevo token
- Envía email al usuario con nuevo token

#### **3.5. Verificar Cuota Diaria**

```go
// Método: db.CheckAndUpdateQuota()

// 1. Obtener límite diario del usuario
SELECT daily_limit, is_blocked, block_reason
FROM user_quotas
WHERE user_id = $1

// 2. Contar requests de hoy
SELECT COUNT(*) 
FROM usage_tracking
WHERE user_id = $1
  AND DATE(created_at) = CURRENT_DATE

// 3. Verificar si excede
if requests_today >= daily_limit {
    return QuotaExceeded
}

// 4. Actualizar contador
UPDATE user_quotas
SET requests_today = requests_today + 1
WHERE user_id = $1
```

**Resultado**:
- ✅ **Dentro de cuota**: Continúa
- ❌ **Cuota excedida**: Error 401
  ```json
  {
    "error": {
      "type": "quota_exceeded",
      "message": "Daily quota limit exceeded",
      "retry_after": "43200"
    }
  }
  ```

**Headers de respuesta**:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 245
X-RateLimit-Reset: 1709942400
```

---

## 📊 Tabla Resumen de Verificaciones

| Nivel | Componente | Qué Verifica | Dónde | Resultado |
|-------|-----------|--------------|-------|-----------|
| **1** | Frontend | Token existe y no expiró | localStorage | Redirige a login si falla |
| **2** | Auth Lambda | Credenciales Cognito | AWS Cognito | Error 401 si inválido |
| **2** | Auth Lambda | Permisos de aplicación | PostgreSQL | Error 403 si no tiene permiso |
| **2** | Auth Lambda | Genera JWT | Secrets Manager | Token válido 1 hora |
| **3** | Proxy | Token existe en BD | PostgreSQL | Error 401 si no existe |
| **3** | Proxy | Firma JWT válida | JWT Secret | Error 401 si inválida |
| **3** | Proxy | Token no expirado | JWT exp claim | Auto-regenera o error 401 |
| **3** | Proxy | Cuota diaria | PostgreSQL | Error 401 si excede |
| **3** | Proxy | Rate limiting | En memoria | Error 401 si excede |

---

## 🔐 Información Almacenada en JWT

```json
{
  "sub": "62d5f404-90d1-70cc-e0d6-a8cb2d156cbc",
  "email": "carlos.sarrion@es.ibm.com",
  "name": "Carlos Sarrion",
  "groups": ["admin"],
  "iat": 1709899200,
  "exp": 1709902800,
  "iss": "auth-lambda",
  "aud": ["auth-login"]
}
```

**Nota importante**: 
- ✅ El JWT **NO incluye la lista completa de permisos**
- ✅ Los permisos se validan **solo en el login** contra la base de datos
- ✅ El JWT solo contiene información básica del usuario

---

## 🎯 Puntos Clave de Autorización

### **1. Validación de Permisos de Aplicación**

**Cuándo**: Durante el login en Auth Lambda

**Cómo**:
```python
# Se verifica que el usuario tenga un permiso activo para la aplicación
required_app_id = "e61e1af9-8992-4bdf-be65-9cad86f34da0"  # identity-mgmt

# Busca en base de datos:
# - scope = 'application'
# - resource_id = required_app_id
# - status = 'active'
# - is_active = true
```

**Resultado**:
- ✅ **Tiene permiso**: Genera token y permite acceso
- ❌ **No tiene permiso**: Error 403 - "Access denied"

### **2. Control de Cuotas**

**Cuándo**: En cada request al proxy de Bedrock

**Cómo**:
```sql
-- Obtener límite diario
SELECT daily_limit FROM user_quotas WHERE user_id = ?

-- Contar requests de hoy
SELECT COUNT(*) FROM usage_tracking 
WHERE user_id = ? AND DATE(created_at) = CURRENT_DATE

-- Verificar
IF requests_today >= daily_limit THEN
    RETURN 'quota_exceeded'
END IF
```

**Resultado**:
- ✅ **Dentro de cuota**: Permite request
- ❌ **Cuota excedida**: Error 401 con headers de rate limit

### **3. Rate Limiting**

**Niveles**:
1. **Por IP**: Máximo de intentos de autenticación por IP
2. **Por Token**: Máximo de intentos con un token específico

**Implementación**: En memoria (no persistente)

---

## 🚨 Casos de Error Comunes

### **Error 401: Unauthorized**

**Causas posibles**:
1. Token no proporcionado
2. Token expirado
3. Token revocado
4. Firma JWT inválida
5. Cuota diaria excedida
6. Rate limit excedido

### **Error 403: Forbidden**

**Causa**:
- Usuario no tiene permiso para acceder a la aplicación
- Se verifica en login contra base de datos

### **Error 429: Too Many Requests**

**Causa**:
- Demasiados intentos de autenticación
- Rate limiting activado

---

## 📝 Resumen Ejecutivo

**¿Cómo se verifica la autorización?**

1. **Login**: 
   - Cognito valida credenciales
   - Base de datos valida permisos de aplicación
   - Se genera JWT si todo es válido

2. **Dashboard**:
   - JavaScript verifica token en localStorage
   - Redirige a login si no existe o expiró

3. **Proxy Bedrock**:
   - Valida token en base de datos
   - Verifica firma JWT
   - Controla cuotas diarias
   - Aplica rate limiting

**Puntos clave**:
- ✅ Permisos se validan **solo en login** contra BD
- ✅ JWT **no contiene permisos completos**
- ✅ Cuotas se verifican **en cada request** al proxy
- ✅ Rate limiting protege contra ataques
- ✅ Auto-regeneración de tokens expirados (opcional)