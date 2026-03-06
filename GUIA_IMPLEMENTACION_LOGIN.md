# 🚀 Guía de Implementación - Sistema de Login con Validación de Permisos

## 📋 Resumen

Esta guía explica cómo implementar el sistema de login con validación de permisos en **cualquier herramienta nueva**. El sistema utiliza una Lambda genérica que valida permisos específicos por aplicación.

---

## 🎯 Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────┐
│  Frontend de la Herramienta (login.html)               │
│  - Especifica UUID de la aplicación                     │
│  - Envía credenciales + app_id a la Lambda             │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│  Lambda de Autenticación (GENÉRICA)                     │
│  - Autentica con Cognito                                │
│  - Valida permisos en BBDD para el app_id recibido     │
│  - Genera token JWT                                     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│  Base de Datos PostgreSQL                               │
│  - identity-manager-applications-tbl                    │
│  - identity-manager-app-permissions-tbl                 │
└─────────────────────────────────────────────────────────┘
```

---

## 📝 Paso 1: Registrar la Nueva Aplicación en la Base de Datos

### 1.1. Conectarse a la Base de Datos

```bash
# Conectar a RDS PostgreSQL
psql -h identity-manager-dev-rds.czuimyk2qu10.eu-west-1.rds.amazonaws.com \
     -U admin_user \
     -d identity_manager_db
```

### 1.2. Insertar la Nueva Aplicación

```sql
-- Insertar nueva aplicación
INSERT INTO "identity-manager-applications-tbl" 
(id, name, description, is_active, display_order)
VALUES 
(
    gen_random_uuid(),  -- Genera UUID automáticamente
    'Mi Nueva Herramienta',  -- Nombre de la aplicación
    'Descripción de la herramienta',  -- Descripción
    TRUE,  -- Activa
    10  -- Orden de visualización
)
RETURNING id, name;

-- Ejemplo de salida:
--                   id                  |        name
-- --------------------------------------+---------------------
--  a1b2c3d4-5678-90ab-cdef-1234567890ab | Mi Nueva Herramienta
```

**⚠️ IMPORTANTE:** Guarda el UUID generado, lo necesitarás en el frontend.

### 1.3. Verificar que se Creó Correctamente

```sql
-- Verificar la aplicación
SELECT id, name, description, is_active
FROM "identity-manager-applications-tbl"
WHERE name = 'Mi Nueva Herramienta';
```

---

## 📁 Paso 2: Copiar y Configurar el Frontend

### 2.1. Copiar el Template de Login

```bash
# Copiar el archivo de login de identity-mgmt
cp frontend/login.html frontend/login-mi-herramienta.html
```

### 2.2. Actualizar el UUID de la Aplicación

Editar `frontend/login-mi-herramienta.html` y cambiar el `APP_ID`:

```javascript
// Buscar esta línea (aproximadamente línea 663)
const APP_ID = 'e61e1af9-8992-4bdf-be65-9cad86f34da0'; // identity-mgmt

// Cambiar por el UUID de tu nueva aplicación
const APP_ID = 'a1b2c3d4-5678-90ab-cdef-1234567890ab'; // ⬅️ UUID de tu app
```

### 2.3. Personalizar el Título y Descripción (Opcional)

```html
<!-- Buscar estas líneas (aproximadamente línea 380-382) -->
<div class="login-header">
    <h1>Mi Nueva Herramienta</h1>  <!-- ⬅️ Cambiar título -->
    <p>Descripción de mi herramienta</p>  <!-- ⬅️ Cambiar descripción -->
</div>
```

---

## 👥 Paso 3: Asignar Permisos a Usuarios

### 3.1. Obtener el ID del Tipo de Permiso

```sql
-- Ver tipos de permisos disponibles
SELECT id, name, description, level
FROM "identity-manager-permission-types-tbl"
ORDER BY level;

-- Ejemplo de salida:
--                   id                  |    name    | level
-- --------------------------------------+------------+-------
--  perm-read-uuid                       | read       |   1
--  perm-write-uuid                      | write      |   2
--  perm-admin-uuid                      | admin      |   3
```

### 3.2. Asignar Permiso a un Usuario

```sql
-- Asignar permiso de admin a un usuario
INSERT INTO "identity-manager-app-permissions-tbl" 
(cognito_user_id, cognito_email, application_id, permission_type_id, is_active)
VALUES 
(
    'f2a56474-9031-7054-1518-5ba5b06aac5d',  -- UUID del usuario en Cognito
    'usuario@example.com',  -- Email del usuario
    'a1b2c3d4-5678-90ab-cdef-1234567890ab',  -- UUID de tu aplicación
    'perm-admin-uuid',  -- UUID del tipo de permiso (admin, read, write)
    TRUE  -- Permiso activo
);
```

### 3.3. Verificar el Permiso Asignado

```sql
-- Verificar permisos del usuario
SELECT 
    u.cognito_email,
    a.name as application_name,
    pt.name as permission_type,
    p.is_active,
    p.granted_at,
    p.expires_at
FROM "identity-manager-app-permissions-tbl" p
JOIN "identity-manager-applications-tbl" a ON p.application_id = a.id
JOIN "identity-manager-permission-types-tbl" pt ON p.permission_type_id = pt.id
WHERE p.cognito_email = 'usuario@example.com'
AND a.name = 'Mi Nueva Herramienta';
```

---

## 🧪 Paso 4: Probar el Login Localmente

### 4.1. Iniciar el Servidor Local

```bash
# Desde la raíz del proyecto
python local_server.py
```

Deberías ver:
```
🚀 Auth Lambda - Servidor Local
📍 Endpoints disponibles:
   • POST http://localhost:5000/auth/login
   • POST http://localhost:5000/auth/verify
   • GET  http://localhost:5000/health
⚙️  Iniciando servidor en http://localhost:5000
```

### 4.2. Abrir el Frontend

```bash
# Abrir en el navegador
start frontend/login-mi-herramienta.html
```

### 4.3. Probar el Login

**Caso 1: Usuario CON Permisos**
```
Email: usuario@example.com
Password: su-contraseña

Resultado esperado: ✅ Login exitoso
```

**Caso 2: Usuario SIN Permisos**
```
Email: otro-usuario@example.com
Password: su-contraseña

Resultado esperado: ❌ Error 403 "No tienes permisos para acceder a esta aplicación"
```

**Caso 3: Usuario con Contraseña Temporal**
```
Email: nuevo-usuario@example.com
Password: contraseña-temporal

Resultado esperado: 
1. Muestra formulario de cambio de contraseña
2. Usuario cambia contraseña
3. Vuelve al login
4. Valida permisos en el siguiente login
```

---

## 🔐 Paso 5: Gestión de Permisos (Operaciones Comunes)

### 5.1. Revocar Permiso (Sin Eliminar)

```sql
-- Desactivar permiso (mantiene historial)
UPDATE "identity-manager-app-permissions-tbl"
SET is_active = FALSE
WHERE cognito_email = 'usuario@example.com'
AND application_id = 'a1b2c3d4-5678-90ab-cdef-1234567890ab';
```

### 5.2. Restaurar Permiso Revocado

```sql
-- Reactivar permiso
UPDATE "identity-manager-app-permissions-tbl"
SET is_active = TRUE
WHERE cognito_email = 'usuario@example.com'
AND application_id = 'a1b2c3d4-5678-90ab-cdef-1234567890ab';
```

### 5.3. Asignar Permiso con Fecha de Expiración

```sql
-- Permiso temporal (expira en 30 días)
INSERT INTO "identity-manager-app-permissions-tbl" 
(cognito_user_id, cognito_email, application_id, permission_type_id, is_active, expires_at)
VALUES 
(
    'user-uuid',
    'usuario@example.com',
    'a1b2c3d4-5678-90ab-cdef-1234567890ab',
    'perm-read-uuid',
    TRUE,
    CURRENT_TIMESTAMP + INTERVAL '30 days'  -- ⬅️ Expira en 30 días
);
```

### 5.4. Cambiar Tipo de Permiso

```sql
-- Cambiar de 'read' a 'admin'
UPDATE "identity-manager-app-permissions-tbl"
SET permission_type_id = 'perm-admin-uuid'
WHERE cognito_email = 'usuario@example.com'
AND application_id = 'a1b2c3d4-5678-90ab-cdef-1234567890ab';
```

### 5.5. Listar Todos los Usuarios con Acceso

```sql
-- Ver todos los usuarios con permiso a la aplicación
SELECT 
    p.cognito_email,
    pt.name as permission_type,
    p.is_active,
    p.granted_at,
    p.expires_at,
    CASE 
        WHEN NOT p.is_active THEN 'Revocado'
        WHEN p.expires_at IS NOT NULL AND p.expires_at < CURRENT_TIMESTAMP THEN 'Expirado'
        ELSE 'Activo'
    END as status
FROM "identity-manager-app-permissions-tbl" p
JOIN "identity-manager-permission-types-tbl" pt ON p.permission_type_id = pt.id
WHERE p.application_id = 'a1b2c3d4-5678-90ab-cdef-1234567890ab'
ORDER BY p.cognito_email;
```

---

## 🚀 Paso 6: Desplegar a Producción (Cuando Esté Listo)

### 6.1. Verificar Configuración

```bash
# Verificar que el APP_ID está correcto en el frontend
grep "const APP_ID" frontend/login-mi-herramienta.html
```

### 6.2. Actualizar URL del API

```javascript
// En frontend/login-mi-herramienta.html
// Cambiar de localhost a la URL de producción
const API_URL = 'https://api.tu-dominio.com';  // ⬅️ URL de producción
```

### 6.3. Subir Frontend a S3 o Hosting

```bash
# Ejemplo con S3
aws s3 cp frontend/login-mi-herramienta.html s3://tu-bucket/login.html
```

---

## 📊 Estructura de Respuestas del API

### Login Exitoso (200)

```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "userId": "f2a56474-9031-7054-1518-5ba5b06aac5d",
    "email": "usuario@example.com",
    "name": "Usuario Ejemplo",
    "groups": []
  },
  "permissions": [
    {
      "permission_id": "perm-uuid",
      "scope": "application",
      "resource_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
      "resource_name": "Mi Nueva Herramienta",
      "permission_type": "admin",
      "permission_level": 3,
      "is_active": true,
      "granted_at": "2026-03-03T17:00:00Z",
      "expires_at": null,
      "status": "active"
    }
  ],
  "expiresAt": "2026-03-03T19:00:00Z"
}
```

### Sin Permisos (403)

```json
{
  "success": false,
  "error": "INSUFFICIENT_PERMISSIONS",
  "message": "No tienes permisos para acceder a esta aplicación (ID: a1b2c3d4-5678-90ab-cdef-1234567890ab)",
  "statusCode": 403
}
```

### Credenciales Incorrectas (400)

```json
{
  "success": false,
  "error": "VALIDATION_ERROR",
  "message": "Email o contraseña incorrectos",
  "statusCode": 400
}
```

### Cambio de Contraseña Requerido (200)

```json
{
  "success": false,
  "requiresPasswordChange": true,
  "message": "Se requiere cambio de contraseña temporal"
}
```

---

## 🔍 Troubleshooting

### Problema 1: Error 403 - Usuario sin Permisos

**Síntoma:** Usuario puede autenticarse en Cognito pero recibe error 403.

**Solución:**
```sql
-- Verificar si el usuario tiene permiso
SELECT * FROM "identity-manager-app-permissions-tbl"
WHERE cognito_email = 'usuario@example.com'
AND application_id = 'tu-app-uuid';

-- Si no existe, asignarlo
INSERT INTO "identity-manager-app-permissions-tbl" 
(cognito_user_id, cognito_email, application_id, permission_type_id, is_active)
VALUES ('user-uuid', 'usuario@example.com', 'tu-app-uuid', 'perm-type-uuid', TRUE);
```

### Problema 2: Error 500 - Error Interno

**Síntoma:** Error 500 al hacer login.

**Solución:**
1. Revisar logs del servidor local
2. Verificar que el UUID de la aplicación existe en la BBDD
3. Verificar conexión a la base de datos

```sql
-- Verificar que la aplicación existe
SELECT * FROM "identity-manager-applications-tbl"
WHERE id = 'tu-app-uuid';
```

### Problema 3: Permiso Expirado

**Síntoma:** Usuario tenía acceso pero ahora recibe error 403.

**Solución:**
```sql
-- Verificar si el permiso expiró
SELECT 
    cognito_email,
    expires_at,
    CASE 
        WHEN expires_at < CURRENT_TIMESTAMP THEN 'EXPIRADO'
        ELSE 'VIGENTE'
    END as status
FROM "identity-manager-app-permissions-tbl"
WHERE cognito_email = 'usuario@example.com'
AND application_id = 'tu-app-uuid';

-- Extender la fecha de expiración
UPDATE "identity-manager-app-permissions-tbl"
SET expires_at = CURRENT_TIMESTAMP + INTERVAL '90 days'
WHERE cognito_email = 'usuario@example.com'
AND application_id = 'tu-app-uuid';
```

### Problema 4: UUID Incorrecto en el Frontend

**Síntoma:** Todos los usuarios reciben error 403.

**Solución:**
```javascript
// Verificar que el APP_ID en el frontend coincide con la BBDD
const APP_ID = 'a1b2c3d4-5678-90ab-cdef-1234567890ab'; // ⬅️ Verificar este UUID
```

```sql
-- Verificar UUID en la BBDD
SELECT id, name FROM "identity-manager-applications-tbl"
WHERE name = 'Mi Nueva Herramienta';
```

---

## 📚 Consultas SQL Útiles

### Ver Todas las Aplicaciones

```sql
SELECT id, name, description, is_active
FROM "identity-manager-applications-tbl"
ORDER BY display_order, name;
```

### Ver Todos los Tipos de Permisos

```sql
SELECT id, name, description, level
FROM "identity-manager-permission-types-tbl"
ORDER BY level;
```

### Ver Permisos de un Usuario Específico

```sql
SELECT 
    a.name as application,
    pt.name as permission_type,
    p.is_active,
    p.granted_at,
    p.expires_at
FROM "identity-manager-app-permissions-tbl" p
JOIN "identity-manager-applications-tbl" a ON p.application_id = a.id
JOIN "identity-manager-permission-types-tbl" pt ON p.permission_type_id = pt.id
WHERE p.cognito_email = 'usuario@example.com';
```

### Ver Usuarios con Acceso a una Aplicación

```sql
SELECT 
    p.cognito_email,
    pt.name as permission_type,
    p.is_active,
    p.granted_at
FROM "identity-manager-app-permissions-tbl" p
JOIN "identity-manager-permission-types-tbl" pt ON p.permission_type_id = pt.id
WHERE p.application_id = 'tu-app-uuid'
AND p.is_active = TRUE
ORDER BY p.cognito_email;
```

---

## ✅ Checklist de Implementación

### Fase 1: Configuración en Base de Datos
- [ ] Conectar a la base de datos PostgreSQL
- [ ] Insertar nueva aplicación en `identity-manager-applications-tbl`
- [ ] Guardar el UUID generado
- [ ] Verificar que la aplicación se creó correctamente

### Fase 2: Configuración del Frontend
- [ ] Copiar `frontend/login.html` con nuevo nombre
- [ ] Actualizar `APP_ID` con el UUID de la nueva aplicación
- [ ] Personalizar título y descripción (opcional)
- [ ] Verificar que el UUID está correcto

### Fase 3: Asignación de Permisos
- [ ] Identificar usuarios que necesitan acceso
- [ ] Obtener UUIDs de usuarios en Cognito
- [ ] Asignar permisos en `identity-manager-app-permissions-tbl`
- [ ] Verificar permisos asignados

### Fase 4: Testing Local
- [ ] Iniciar servidor local (`python local_server.py`)
- [ ] Abrir frontend en navegador
- [ ] Probar login con usuario CON permisos → Debe funcionar ✅
- [ ] Probar login con usuario SIN permisos → Debe dar error 403 ❌
- [ ] Probar cambio de contraseña temporal (si aplica)

### Fase 5: Despliegue (Opcional)
- [ ] Actualizar URL del API a producción
- [ ] Subir frontend a hosting/S3
- [ ] Probar en producción
- [ ] Documentar URL de acceso

---

## 🎯 Resumen Rápido

1. **Registrar app en BBDD** → Obtener UUID
2. **Copiar frontend** → Cambiar `APP_ID` al nuevo UUID
3. **Asignar permisos** a usuarios en BBDD
4. **Probar localmente** → Verificar que funciona
5. **Desplegar** cuando esté listo

---

## 📞 Soporte

Si encuentras problemas:
1. Revisar logs del servidor local
2. Verificar UUIDs en BBDD y frontend
3. Consultar sección de Troubleshooting
4. Revisar permisos del usuario en BBDD

---

## 🔗 Referencias

- **Archivo de configuración:** `backend/auth-lambda/config.py`
- **Servicio de autenticación:** `backend/auth-lambda/auth_service.py`
- **Servicio de permisos:** `backend/shared/services/permissions_service.py`
- **Frontend template:** `frontend/login.html`
- **Servidor local:** `local_server.py`

---

**Última actualización:** 3 de Marzo de 2026  
**Versión:** 1.0.0