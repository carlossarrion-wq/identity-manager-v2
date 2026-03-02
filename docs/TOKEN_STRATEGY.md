# Estrategia de Tokens: Permisos en JWT vs Consulta Dinámica

## 🤔 La Pregunta Clave

> "Si el token ya incluye el listado de permisos, ¿para qué necesitamos la función de Consulta de Permisos? ¿No valdría con que la aplicación verifique que el token JWT es válido?"

**Respuesta corta**: Tienes razón. Hay **dos estrategias válidas** y debemos elegir una.

---

## 📊 Estrategia 1: Permisos en el Token JWT (Recomendada ✅)

### Cómo Funciona

```javascript
// Token JWT incluye permisos en los claims
{
  "sub": "user-uuid-123",
  "email": "user@example.com",
  "name": "John Doe",
  "cognito:groups": ["developers"],
  "custom:permissions": {
    "applications": [
      {
        "id": "app-1",
        "name": "Gestión Demanda",
        "permission": "read_write",
        "expires_at": "2026-12-31"
      },
      {
        "id": "app-2",
        "name": "Bedrock Proxy",
        "permission": "read",
        "expires_at": null
      }
    ],
    "modules": [
      {
        "id": "module-1",
        "app_id": "app-1",
        "name": "Solicitudes",
        "permission": "admin"
      }
    ]
  },
  "iat": 1709370000,
  "exp": 1709373600  // 1 hora
}
```

### Flujo Simplificado

```
┌──────────┐         ┌──────────┐         ┌──────────┐
│          │         │          │         │          │
│  App     │────1───▶│  Auth    │────2───▶│ Cognito  │
│  Client  │         │  Lambda  │         │   +      │
│          │         │          │         │   RDS    │
│          │◀───4────│          │◀───3────│          │
└──────────┘         └──────────┘         └──────────┘

1. POST /auth/login { email, password }
2. Auth Lambda:
   - Autentica con Cognito
   - Consulta permisos en RDS
   - Genera token JWT con permisos incluidos
3. Retorna token con permisos
4. App valida token localmente (sin llamadas adicionales)

// Después, la app solo necesita:
- Validar firma del token (usando JWKS público)
- Verificar expiración
- Leer permisos del token
```

### ✅ Ventajas

1. **Performance Óptimo**
   - ❌ NO hay llamadas adicionales para consultar permisos
   - ✅ Validación local del token (sin latencia de red)
   - ✅ Aplicación puede funcionar offline

2. **Simplicidad**
   - ❌ NO necesitas endpoint `/auth/permissions`
   - ❌ NO necesitas endpoint `/auth/check-permission`
   - ✅ Solo necesitas `/auth/login` y validación local

3. **Escalabilidad**
   - ✅ Sin carga en backend para consultas de permisos
   - ✅ Menos requests = menos costos

4. **Experiencia de Usuario**
   - ✅ Respuesta instantánea (sin latencia)
   - ✅ Funciona con conexión intermitente

### ⚠️ Desventajas

1. **Tamaño del Token**
   - ⚠️ Token más grande (puede ser 2-5 KB)
   - ⚠️ Límite de Cognito: 2048 bytes para custom attributes
   - 💡 **Solución**: Usar token propio (no Cognito) o comprimir permisos

2. **Actualización de Permisos**
   - ⚠️ Si cambias permisos, usuario debe hacer re-login
   - ⚠️ O esperar a que expire el token (1 hora típicamente)
   - 💡 **Solución**: TTL corto (15-30 min) o refresh token

3. **Seguridad**
   - ⚠️ Permisos visibles en el token (aunque firmado)
   - ⚠️ Si token se compromete, atacante ve permisos
   - 💡 **Solución**: Tokens de corta duración + HTTPS

---

## 📊 Estrategia 2: Consulta Dinámica de Permisos

### Cómo Funciona

```javascript
// Token JWT solo incluye identidad
{
  "sub": "user-uuid-123",
  "email": "user@example.com",
  "name": "John Doe",
  "cognito:groups": ["developers"],
  "iat": 1709370000,
  "exp": 1709373600
}

// Permisos se consultan en cada request
GET /auth/permissions
Authorization: Bearer <token>

Response:
{
  "applications": [...],
  "modules": [...]
}
```

### Flujo con Consultas

```
┌──────────┐         ┌──────────┐         ┌──────────┐
│          │         │          │         │          │
│  App     │────1───▶│  Auth    │────2───▶│ Cognito  │
│  Client  │         │  Lambda  │         │          │
│          │◀───3────│          │◀────────│          │
└──────────┘         └──────────┘         └──────────┘

1. POST /auth/login { email, password }
2. Auth Lambda autentica con Cognito
3. Retorna token simple (sin permisos)

// Después, cada vez que necesita permisos:
┌──────────┐         ┌──────────┐         ┌──────────┐
│  App     │────1───▶│  Auth    │────2───▶│   RDS    │
│  Client  │         │  Lambda  │         │          │
│          │◀───4────│          │◀───3────│          │
└──────────┘         └──────────┘         └──────────┘

1. GET /auth/permissions (con token)
2. Auth Lambda valida token y extrae userId
3. Consulta permisos en RDS
4. Retorna permisos actualizados
```

### ✅ Ventajas

1. **Permisos Siempre Actualizados**
   - ✅ Cambios de permisos se reflejan inmediatamente
   - ✅ No necesita re-login del usuario
   - ✅ Revocación instantánea

2. **Token Pequeño**
   - ✅ Token ligero (< 500 bytes)
   - ✅ Compatible con Cognito custom attributes

3. **Seguridad**
   - ✅ Permisos no expuestos en el token
   - ✅ Control granular en backend

### ⚠️ Desventajas

1. **Performance**
   - ❌ Llamada adicional en cada request o periódicamente
   - ❌ Latencia de red (50-200ms)
   - ❌ Más carga en backend

2. **Complejidad**
   - ❌ Necesitas endpoint adicional
   - ❌ Gestión de caché en cliente
   - ❌ Manejo de errores de red

3. **Disponibilidad**
   - ❌ Si backend cae, app no puede verificar permisos
   - ❌ Requiere conexión constante

---

## 💡 Estrategia Híbrida (Recomendación Final ✅)

### La Mejor de Ambas Opciones

```javascript
// 1. En el login, incluir permisos en el token
POST /auth/login
Response:
{
  "token": "eyJ...",  // Incluye permisos
  "permissions": {    // También en response para caché local
    "applications": [...],
    "modules": [...]
  }
}

// 2. App valida token localmente (rápido)
// 3. App refresca permisos periódicamente (cada 5-10 min)
GET /auth/permissions  // Opcional, solo si necesita actualización

// 4. Para operaciones críticas, verificar en backend
POST /auth/check-permission  // Solo para operaciones sensibles
{
  "applicationId": "app-1",
  "moduleId": "module-1"
}
```

### Implementación Recomendada

```python
# En Auth Lambda - Login
def handle_login(email, password):
    # 1. Autenticar con Cognito
    cognito_tokens = cognito.authenticate(email, password)
    
    # 2. Obtener permisos de RDS
    permissions = get_user_permissions(user_id)
    
    # 3. Crear token JWT propio con permisos
    custom_token = jwt.encode({
        'sub': user_id,
        'email': email,
        'permissions': permissions,  # ← Permisos incluidos
        'exp': datetime.now() + timedelta(minutes=30)  # TTL corto
    }, SECRET_KEY)
    
    return {
        'token': custom_token,
        'cognito_tokens': cognito_tokens,  # Para refresh
        'permissions': permissions  # Para caché local
    }

# En la Aplicación Cliente
class AuthClient:
    def __init__(self):
        self.token = None
        self.permissions = None
        self.last_refresh = None
    
    def login(self, email, password):
        response = auth_api.login(email, password)
        self.token = response['token']
        self.permissions = response['permissions']
        self.last_refresh = time.time()
    
    def has_permission(self, app_id, module_id=None):
        # 1. Validar token localmente (rápido)
        if not self._is_token_valid():
            return False
        
        # 2. Verificar permisos del token (sin llamada a backend)
        return self._check_local_permissions(app_id, module_id)
    
    def refresh_permissions_if_needed(self):
        # Refrescar cada 5 minutos
        if time.time() - self.last_refresh > 300:
            self.permissions = auth_api.get_permissions(self.token)
            self.last_refresh = time.time()
```

---

## 🎯 Decisión Recomendada

### **Usar Estrategia Híbrida con Énfasis en Token**

#### Endpoints Necesarios:

1. **`POST /auth/login`** (Obligatorio)
   - Retorna token JWT con permisos incluidos
   - App puede funcionar solo con esto

2. **`GET /auth/permissions`** (Opcional)
   - Solo para refrescar permisos sin re-login
   - Llamada periódica (cada 5-10 min) o bajo demanda

3. **`POST /auth/check-permission`** (Opcional)
   - Solo para operaciones críticas que requieren verificación en tiempo real
   - Ejemplo: antes de ejecutar una operación destructiva

#### Configuración Recomendada:

```yaml
Token Configuration:
  - Type: JWT propio (no Cognito custom attributes)
  - TTL: 30 minutos
  - Include: user_id, email, groups, permissions
  - Size: ~2-4 KB (aceptable)

Permissions Refresh:
  - Strategy: Lazy refresh
  - Interval: 5 minutos
  - Trigger: Automático en background

Critical Operations:
  - Strategy: Backend verification
  - Endpoint: /auth/check-permission
  - Use cases: Delete, Admin actions
```

---

## 📋 Comparativa Final

| Aspecto | Solo Token | Solo Consulta | Híbrido ✅ |
|---------|-----------|---------------|-----------|
| **Performance** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| **Actualización** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Simplicidad** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Seguridad** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Escalabilidad** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| **Offline** | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐ |

---

## 🚀 Implementación Simplificada

### Si Eliges Solo Token (Más Simple):

```python
# Auth Lambda - Solo necesitas esto
@app.route('/auth/login', methods=['POST'])
def login():
    email = request.json['email']
    password = request.json['password']
    
    # 1. Autenticar
    user = cognito.authenticate(email, password)
    
    # 2. Obtener permisos
    permissions = db.get_user_permissions(user['user_id'])
    
    # 3. Crear token con permisos
    token = jwt.encode({
        'sub': user['user_id'],
        'email': email,
        'permissions': permissions,
        'exp': datetime.now() + timedelta(minutes=30)
    }, SECRET_KEY)
    
    return {'token': token}

# En la App - Validación local
def has_permission(token, app_id):
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=['RS256'])
        permissions = payload['permissions']
        
        for perm in permissions['applications']:
            if perm['id'] == app_id and perm['is_active']:
                return True
        return False
    except:
        return False
```

---

## 💭 Conclusión

**Tu intuición es correcta**: Si incluyes permisos en el token, **NO necesitas** endpoint de consulta de permisos para el 95% de los casos.

**Recomendación**:
1. **Empezar simple**: Solo `/auth/login` con permisos en token
2. **Añadir después si necesario**: `/auth/permissions` para refresh
3. **Solo si crítico**: `/auth/check-permission` para verificación backend

Esto reduce complejidad, mejora performance y es más fácil de mantener.
