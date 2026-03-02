# Arquitectura de Autenticación para Aplicaciones
## Propuesta de Integración del Sistema de Permisos

---

## 📋 Análisis de Requisitos

### Necesidades Identificadas:
1. **Autenticación de usuarios** mediante Cognito en cada aplicación
2. **Obtención de token JWT** con atributos del usuario
3. **Consulta de permisos** del usuario autenticado
4. **Validación de permisos** a nivel de aplicación y módulo

---

## 🏗️ Arquitectura Propuesta

### **Opción Recomendada: Lambda Dedicada para Autenticación (Auth Lambda)**

#### ✅ **Ventajas de Lambda Separada:**

1. **Separación de Responsabilidades**
   - Lambda actual (`identity-mgmt-api`): Gestión administrativa (CRUD usuarios, permisos, tokens)
   - Nueva Lambda (`auth-api`): Autenticación y autorización en tiempo real

2. **Escalabilidad Independiente**
   - Auth Lambda tendrá mucho más tráfico (cada request de aplicación)
   - Puede escalar independientemente sin afectar operaciones administrativas

3. **Seguridad**
   - Diferentes niveles de acceso y políticas IAM
   - Auth Lambda: acceso público con rate limiting
   - Admin Lambda: acceso restringido a administradores

4. **Performance**
   - Auth Lambda optimizada para baja latencia
   - Caché de permisos en memoria (warm containers)
   - Sin operaciones pesadas de escritura

5. **Mantenimiento**
   - Despliegues independientes
   - Menor riesgo de afectar servicios críticos

---

## 🔧 Arquitectura Detallada

### **Componente 1: Auth Lambda (Nueva)**

```
┌─────────────────────────────────────────────────────────────┐
│                      AUTH LAMBDA                             │
│                   (auth-api-lmbd)                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Endpoints:                                                  │
│  ├─ POST /auth/login                                        │
│  │   └─ Autentica usuario con Cognito                      │
│  │   └─ Retorna: ID Token + Access Token + Refresh Token   │
│  │                                                           │
│  ├─ POST /auth/verify                                       │
│  │   └─ Valida token JWT de Cognito                        │
│  │   └─ Retorna: Claims del usuario                        │
│  │                                                           │
│  ├─ GET /auth/permissions                                   │
│  │   └─ Consulta permisos del usuario autenticado          │
│  │   └─ Retorna: Lista de permisos (apps + módulos)        │
│  │                                                           │
│  └─ POST /auth/check-permission                             │
│      └─ Verifica si usuario tiene permiso específico        │
│      └─ Retorna: boolean + detalles del permiso            │
│                                                              │
│  Servicios Reutilizados:                                    │
│  ├─ CognitoService (autenticación)                         │
│  ├─ DatabaseService (consulta permisos)                    │
│  └─ PermissionsService (lógica de permisos)                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### **Componente 2: Identity Management Lambda (Existente)**

```
┌─────────────────────────────────────────────────────────────┐
│              IDENTITY MANAGEMENT LAMBDA                      │
│                (identity-mgmt-api-lmbd)                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Endpoints Administrativos:                                  │
│  ├─ Gestión de Usuarios (CRUD)                             │
│  ├─ Gestión de Tokens JWT (crear, revocar, restaurar)      │
│  ├─ Gestión de Permisos (asignar, revocar, restaurar)      │
│  ├─ Consulta de Auditoría                                   │
│  └─ Configuración del Sistema                               │
│                                                              │
│  Uso: Dashboard administrativo                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Flujo de Autenticación Propuesto

### **Flujo 1: Login de Usuario**

```
┌──────────┐         ┌──────────┐         ┌──────────┐         ┌──────────┐
│          │         │          │         │          │         │          │
│  App     │────1───▶│  Auth    │────2───▶│ Cognito  │────3───▶│   RDS    │
│  Client  │         │  Lambda  │         │          │         │ Postgres │
│          │◀───6────│          │◀───5────│          │◀───4────│          │
└──────────┘         └──────────┘         └──────────┘         └──────────┘

1. POST /auth/login { email, password }
2. Auth Lambda → Cognito: InitiateAuth
3. Cognito valida credenciales
4. Auth Lambda consulta permisos en RDS
5. Cognito retorna tokens (ID, Access, Refresh)
6. Auth Lambda retorna:
   {
     "tokens": {
       "idToken": "eyJ...",      // Token de identidad (claims del usuario)
       "accessToken": "eyJ...",  // Token de acceso (para APIs de AWS)
       "refreshToken": "eyJ..."  // Token para renovar sesión
     },
     "user": {
       "userId": "uuid",
       "email": "user@example.com",
       "name": "John Doe",
       "groups": ["developers"]
     },
     "permissions": {
       "applications": [...],
       "modules": [...]
     }
   }
```

### **Flujo 2: Verificación de Token**

```
┌──────────┐         ┌──────────┐         ┌──────────┐
│          │         │          │         │          │
│  App     │────1───▶│  Auth    │────2───▶│ Cognito  │
│  Client  │         │  Lambda  │         │          │
│          │◀───4────│          │◀───3────│          │
└──────────┘         └──────────┘         └──────────┘

1. POST /auth/verify { idToken }
2. Auth Lambda valida token con Cognito
3. Cognito retorna claims si válido
4. Auth Lambda retorna claims del usuario
```

### **Flujo 3: Consulta de Permisos**

```
┌──────────┐         ┌──────────┐         ┌──────────┐
│          │         │          │         │          │
│  App     │────1───▶│  Auth    │────2───▶│   RDS    │
│  Client  │         │  Lambda  │         │ Postgres │
│          │◀───4────│          │◀───3────│          │
└──────────┘         └──────────┘         └──────────┘

1. GET /auth/permissions
   Headers: { Authorization: "Bearer <idToken>" }
2. Auth Lambda valida token y extrae userId
3. Consulta permisos en RDS (tabla permissions)
4. Retorna permisos filtrados y activos
```

### **Flujo 4: Verificación de Permiso Específico**

```
┌──────────┐         ┌──────────┐         ┌──────────┐
│          │         │          │         │          │
│  App     │────1───▶│  Auth    │────2───▶│   RDS    │
│  Client  │         │  Lambda  │         │ Postgres │
│          │◀───4────│          │◀───3────│          │
└──────────┘         └──────────┘         └──────────┘

1. POST /auth/check-permission
   {
     "applicationId": "app-123",
     "moduleId": "module-456" (opcional)
   }
2. Auth Lambda valida token y extrae userId
3. Consulta permiso específico en RDS
4. Retorna:
   {
     "hasPermission": true,
     "permissionType": "read_write",
     "expiresAt": "2026-06-01T00:00:00Z"
   }
```

---

## 📦 Servicios Reutilizables

### **Servicios a Compartir entre Lambdas:**

```python
# Estructura de carpetas compartidas
backend/
├── shared/                          # Código compartido
│   ├── services/
│   │   ├── cognito_service.py      # ✅ Reutilizar
│   │   ├── database_service.py     # ✅ Reutilizar
│   │   └── permissions_service.py  # ✅ Reutilizar
│   └── utils/
│       ├── validators.py            # ✅ Reutilizar
│       └── response_builder.py     # ✅ Reutilizar
│
├── lambdas/
│   ├── identity-mgmt-api/          # Lambda administrativa
│   │   └── lambda_function.py
│   │
│   └── auth-api/                    # Nueva Lambda de autenticación
│       ├── lambda_function.py
│       └── services/
│           └── auth_service.py     # Nuevo servicio específico
```

### **Servicios a Crear para Auth Lambda:**

1. **`auth_service.py`** - Nuevo
   - `authenticate_user(email, password)` → Tokens de Cognito
   - `verify_token(id_token)` → Claims del usuario
   - `refresh_session(refresh_token)` → Nuevos tokens
   - `logout(access_token)` → Invalidar sesión

2. **`permission_checker.py`** - Nuevo
   - `check_app_permission(user_id, app_id)` → boolean
   - `check_module_permission(user_id, module_id)` → boolean
   - `get_user_permissions_cached(user_id)` → Permisos con caché

---

## 🔐 Seguridad y Mejores Prácticas

### **1. Autenticación con Cognito**

```python
# Usar Cognito User Pools para autenticación
# NO crear tokens JWT propios para autenticación
# SÍ usar tokens de Cognito (más seguros y estándar)

# Flujo recomendado:
1. Usuario → email/password → Auth Lambda
2. Auth Lambda → Cognito InitiateAuth
3. Cognito → ID Token (JWT con claims del usuario)
4. App usa ID Token para llamadas subsiguientes
```

### **2. Validación de Tokens**

```python
# Validar tokens de Cognito usando:
- Verificación de firma (JWKS de Cognito)
- Verificación de expiración
- Verificación de audience
- Verificación de issuer

# NO confiar en tokens sin validar
```

### **3. Caché de Permisos**

```python
# Implementar caché en memoria para permisos
# Reducir consultas a RDS en cada request

class PermissionCache:
    def __init__(self):
        self.cache = {}
        self.ttl = 300  # 5 minutos
    
    def get_permissions(self, user_id):
        if user_id in self.cache:
            if not self._is_expired(user_id):
                return self.cache[user_id]
        
        # Consultar RDS
        permissions = self._fetch_from_db(user_id)
        self.cache[user_id] = {
            'data': permissions,
            'timestamp': time.time()
        }
        return permissions
```

### **4. Rate Limiting**

```python
# Implementar rate limiting en API Gateway
# Proteger contra ataques de fuerza bruta

# Configuración recomendada:
- 10 requests/segundo por IP para /auth/login
- 100 requests/segundo por usuario para /auth/permissions
- 1000 requests/segundo global para /auth/verify
```

---

## 🚀 Plan de Implementación

### **Fase 1: Preparación (1-2 días)**
- [ ] Crear estructura de carpeta `shared/` con servicios comunes
- [ ] Refactorizar servicios existentes para ser reutilizables
- [ ] Documentar interfaces de servicios compartidos

### **Fase 2: Desarrollo Auth Lambda (3-4 días)**
- [ ] Crear nueva Lambda `auth-api`
- [ ] Implementar endpoint `/auth/login`
- [ ] Implementar endpoint `/auth/verify`
- [ ] Implementar endpoint `/auth/permissions`
- [ ] Implementar endpoint `/auth/check-permission`
- [ ] Añadir caché de permisos
- [ ] Tests unitarios e integración

### **Fase 3: Infraestructura (2-3 días)**
- [ ] Configurar API Gateway para Auth Lambda
- [ ] Configurar rate limiting
- [ ] Configurar CORS para aplicaciones
- [ ] Configurar CloudWatch logs y métricas
- [ ] Configurar alarmas

### **Fase 4: Integración (2-3 días)**
- [ ] Crear SDK/librería cliente para aplicaciones
- [ ] Documentar API de autenticación
- [ ] Ejemplos de integración
- [ ] Guía de migración para aplicaciones existentes

### **Fase 5: Testing y Despliegue (2-3 días)**
- [ ] Tests de carga
- [ ] Tests de seguridad
- [ ] Despliegue en dev
- [ ] Despliegue en pre
- [ ] Despliegue en pro

---

## 📊 Comparativa: Lambda Única vs Lambda Separada

| Aspecto | Lambda Única | Lambda Separada (✅ Recomendado) |
|---------|--------------|----------------------------------|
| **Escalabilidad** | ❌ Limitada | ✅ Independiente |
| **Performance** | ❌ Compartida | ✅ Optimizada |
| **Seguridad** | ⚠️ Mismo nivel acceso | ✅ Niveles diferentes |
| **Mantenimiento** | ❌ Acoplado | ✅ Desacoplado |
| **Despliegues** | ❌ Riesgo alto | ✅ Riesgo bajo |
| **Costos** | ✅ Menor | ⚠️ Ligeramente mayor |
| **Complejidad** | ✅ Menor | ⚠️ Mayor inicial |

---

## 💡 Recomendación Final

### **✅ Crear Lambda Separada para Autenticación**

**Razones principales:**
1. **Tráfico diferente**: Auth tendrá 100x más requests que Admin
2. **Latencia crítica**: Auth necesita responder en <100ms
3. **Seguridad**: Diferentes niveles de acceso y exposición
4. **Escalabilidad**: Pueden escalar independientemente
5. **Mantenimiento**: Cambios en Admin no afectan Auth

**Servicios a reutilizar:**
- ✅ `CognitoService` - Autenticación con Cognito
- ✅ `DatabaseService` - Conexión a RDS
- ✅ `PermissionsService` - Lógica de permisos
- ✅ Utilidades comunes

**Servicios nuevos a crear:**
- 🆕 `AuthService` - Flujos de autenticación
- 🆕 `PermissionChecker` - Validación rápida de permisos
- 🆕 `TokenValidator` - Validación de tokens de Cognito

---

## 📝 Próximos Pasos

1. **Revisar y aprobar** esta arquitectura
2. **Definir prioridades** de endpoints a implementar
3. **Crear estructura** de carpetas compartidas
4. **Comenzar desarrollo** de Auth Lambda
5. **Documentar APIs** para consumo de aplicaciones

---

## 🔗 Referencias

- [AWS Cognito Authentication Flow](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-authentication-flow.html)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [API Gateway Rate Limiting](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-request-throttling.html)
