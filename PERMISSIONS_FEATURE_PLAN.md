# Plan de Implementación: Gestión de Permisos de Acceso

## 📋 Resumen Ejecutivo

Implementar una interfaz completa en el dashboard para gestionar permisos de acceso a aplicaciones y módulos para usuarios, aprovechando el esquema de base de datos ya existente.

## 🎯 Objetivos

1. Permitir asignar/revocar permisos de aplicaciones a usuarios
2. Permitir asignar/revocar permisos de módulos específicos a usuarios
3. Visualizar permisos actuales de cada usuario
4. Auditar cambios en permisos

## 📊 Análisis del Estado Actual

### ✅ Base de Datos (Ya Implementado)

El esquema actual ya incluye:

```sql
-- Tipos de permisos (Read-only, Write, Admin, etc.)
identity-manager-permission-types-tbl

-- Permisos a nivel de aplicación
identity-manager-app-permissions-tbl
  - cognito_user_id
  - application_id
  - permission_type_id
  - expires_at
  - is_active

-- Permisos a nivel de módulo
identity-manager-module-permissions-tbl
  - cognito_user_id
  - application_module_id
  - permission_type_id
  - expires_at
  - is_active

-- Vista consolidada
v_user_permissions
```

### 🔴 Pendiente de Implementar

1. **Backend (Lambda API)**
   - Endpoints para gestión de permisos
   - Servicio de permisos

2. **Frontend (Dashboard)**
   - Nueva pestaña "Permissions"
   - Interfaz de asignación de permisos (versión simple)
   - Visualización de permisos por usuario

## 🏗️ Arquitectura de la Solución

### 1. Backend - Nuevos Endpoints API

```python
# Operaciones de Permisos
POST   /permissions/assign-app          # Asignar permiso de aplicación
POST   /permissions/assign-module       # Asignar permiso de módulo
DELETE /permissions/revoke-app          # Revocar permiso de aplicación
DELETE /permissions/revoke-module       # Revocar permiso de módulo
GET    /permissions/user/{user_id}      # Obtener todos los permisos de un usuario
                                        # (incluye validación implícita)

# Operaciones de Catálogo
GET    /permission-types                # Listar tipos de permisos
GET    /applications                    # Listar aplicaciones (ya existe)
GET    /modules                         # Listar módulos por aplicación
```

**Nota:** El endpoint `/permissions/check` se elimina por redundancia. La validación de permisos se puede hacer desde el frontend consultando `/permissions/user/{user_id}` y verificando localmente.

### 2. Backend - Nuevo Servicio

**`backend/lambdas/identity-mgmt-api/services/permissions_service.py`**

```python
class PermissionsService:
    
    # Asignación de permisos
    def assign_app_permission(user_id, app_id, permission_type_id, expires_at=None)
    def assign_module_permission(user_id, module_id, permission_type_id, expires_at=None)
    
    # Revocación de permisos
    def revoke_app_permission(user_id, app_id)
    def revoke_module_permission(user_id, module_id)
    
    # Consulta de permisos
    def get_user_permissions(user_id)
    def check_user_has_permission(user_id, resource_type, resource_id, min_level=1)
    
    # Validación
    def validate_permission_for_token(user_id, profile_id)
    
    # Catálogos
    def list_permission_types()
    def list_applications()
    def list_modules(app_id=None)
```

### 3. Frontend - Nueva Pestaña "Permissions" (Versión Simple)

**Estructura de la UI (sin filtros ni paginación):**

```
┌─────────────────────────────────────────────────────────┐
│ PERMISSIONS MANAGEMENT                                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ [+ Assign Permission]                                   │
│                                                          │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ User Permissions                                     │ │
│ ├──────────┬──────────────┬──────────┬────────────────┤ │
│ │ User     │ Resource     │ Type     │ Actions        │ │
│ ├──────────┼──────────────┼──────────┼────────────────┤ │
│ │ john@... │ Cline        │ Admin    │ [Revoke]       │ │
│ │ john@... │ Cline > RAG  │ Write    │ [Revoke]       │ │
│ │ jane@... │ KB-Agent     │ Read     │ [Revoke]       │ │
│ └──────────┴──────────────┴──────────┴────────────────┘ │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Nota:** En esta versión inicial se omiten filtros y paginación para simplificar. Se añadirán en futuras iteraciones.

### 4. Flujo de Asignación de Permisos

```
1. Admin selecciona usuario
   ↓
2. Admin selecciona aplicación o módulo
   ↓
3. Admin selecciona tipo de permiso (Read/Write/Admin)
   ↓
4. (Opcional) Admin selecciona duración del permiso:
   - 1 día
   - 7 días
   - 30 días
   - 60 días
   - 90 días
   - Indefinido (sin expiración)
   ↓
5. Sistema valida:
   - Usuario existe en Cognito
   - Aplicación/módulo existe
   - No hay conflictos de permisos
   ↓
6. Sistema calcula fecha de expiración (si aplica)
   ↓
7. Sistema registra en BD
   ↓
8. Sistema registra en auditoría
   ↓
9. Dashboard actualiza vista
```


## 📝 Plan de Implementación Detallado

### Fase 1: Backend - Servicio de Permisos (2-3 horas)

**Archivos a crear/modificar:**

1. ✅ `backend/lambdas/identity-mgmt-api/services/permissions_service.py`
   - Implementar todas las operaciones CRUD de permisos
   - Incluir validaciones de negocio
   - Registrar en auditoría

2. ✅ `backend/lambdas/identity-mgmt-api/lambda_function.py`
   - Añadir nuevos endpoints
   - Integrar con permissions_service

3. ✅ `backend/lambdas/identity-mgmt-api/utils/validators.py`
   - Añadir validadores para permisos

### Fase 2: Frontend - API Client (1 hora)

**Archivos a modificar:**

1. ✅ `frontend/dashboard/js/api.js`
   - Añadir métodos para gestión de permisos:
     ```javascript
     // Permissions API
     async assignAppPermission(userId, appId, permissionTypeId, expiresAt)
     async assignModulePermission(userId, moduleId, permissionTypeId, expiresAt)
     async revokeAppPermission(userId, appId)
     async revokeModulePermission(userId, moduleId)
     async getUserPermissions(userId)
     async listPermissionTypes()
     async listModules(appId)
     ```

### Fase 4: Frontend - UI de Permisos (3-4 horas)

**Archivos a crear/modificar:**

1. ✅ `frontend/dashboard/index.html`
   - Añadir nueva pestaña "Permissions"
   - Añadir modal para asignar permisos
   - Añadir tabla de permisos

2. ✅ `frontend/dashboard/js/dashboard.js`
   - Implementar lógica de la pestaña Permissions
   - Funciones para cargar/mostrar permisos
   - Funciones para asignar/revocar permisos

3. ✅ `frontend/dashboard/css/dashboard.css`
   - Estilos para la nueva pestaña
   - Estilos para badges de permisos

### Fase 5: Testing y Documentación (1-2 horas)

1. ✅ Tests unitarios para permissions_service
2. ✅ Tests de integración para endpoints
3. ✅ Actualizar README con nueva funcionalidad
4. ✅ Documentar API de permisos

## 🎨 Diseño de UI Propuesto

### Pestaña "Permissions" (Versión Simple)

```html
<!-- Botones de acción -->
<div class="actions-section">
  <button class="action-button create" onclick="showAssignPermissionModal()">
    + Assign Permission
  </button>
  <button class="action-button refresh" onclick="refreshPermissions()">
    🔄 Refresh
  </button>
</div>

<!-- Tabla de Permisos (sin filtros ni paginación) -->
<table id="permissions-table">
  <thead>
    <tr>
      <th>User</th>
      <th>Email</th>
      <th>Scope</th>
      <th>Resource</th>
      <th>Permission</th>
      <th>Granted</th>
      <th>Expires</th>
      <th>Status</th>
      <th>Actions</th>
    </tr>
  </thead>
  <tbody>
    <!-- Permisos dinámicos - Se cargan todos sin paginación -->
  </tbody>
</table>
```

**Nota:** Filtros y paginación se añadirán en una versión futura cuando sea necesario.

### Modal de Asignación

```html
<div id="assign-permission-modal" class="modal">
  <div class="modal-content">
    <div class="modal-header">
      <h2>Assign Permission</h2>
      <button class="modal-close" onclick="closeAssignPermissionModal()">×</button>
    </div>
    <div class="modal-body">
      <form id="assign-permission-form">
        <div class="form-group">
          <label>User *</label>
          <select id="perm-user" required>
            <!-- Usuarios -->
          </select>
        </div>
        
        <div class="form-group">
          <label>Scope *</label>
          <select id="perm-scope" onchange="updateResourceOptions()" required>
            <option value="">Select scope...</option>
            <option value="application">Application</option>
            <option value="module">Module</option>
          </select>
        </div>
        
        <div class="form-group">
          <label>Application *</label>
          <select id="perm-application" onchange="loadModules()" required>
            <!-- Aplicaciones -->
          </select>
        </div>
        
        <div class="form-group" id="module-group" style="display:none;">
          <label>Module</label>
          <select id="perm-module">
            <!-- Módulos -->
          </select>
        </div>
        
        <div class="form-group">
          <label>Permission Type *</label>
          <select id="perm-type" required>
            <option value="">Select permission...</option>
            <!-- Read-only, Write, Admin, etc. -->
          </select>
        </div>
        
        <div class="form-group">
          <label>Duration</label>
          <select id="perm-duration">
            <option value="indefinite">Indefinite</option>
            <option value="1">1 Day</option>
            <option value="7">7 Days</option>
            <option value="30">30 Days</option>
            <option value="60">60 Days</option>
            <option value="90">90 Days</option>
          </select>
        </div>
        
        <div class="form-actions">
          <button type="button" class="btn-secondary" onclick="closeAssignPermissionModal()">
            Cancel
          </button>
          <button type="submit" class="btn-primary">
            Assign Permission
          </button>
        </div>
      </form>
    </div>
  </div>
</div>
```

## 🔒 Consideraciones de Seguridad

1. **Validación de Permisos**
   - Solo usuarios con rol Admin pueden gestionar permisos
   - Validar que el usuario que asigna tiene permisos suficientes

2. **Auditoría**
   - Registrar todas las operaciones de permisos en `identity-manager-audit-tbl`
   - Incluir: quién, qué, cuándo, desde dónde

3. **Expiración**
   - Implementar job para desactivar permisos expirados
   - Notificar antes de expiración

4. **Validación en Tokens**
   - Verificar permisos activos antes de generar tokens
   - Incluir permisos en el payload del JWT

## 📊 Modelo de Datos - Jerarquía de Permisos

```
Permission Types (Niveles):
├─ 1: Read-only (Nivel 10)
├─ 2: Write (Nivel 50)
└─ 3: Admin (Nivel 100)

Scope:
├─ Application Level
│  └─ Aplica a toda la aplicación y sus módulos
└─ Module Level
   └─ Aplica solo a un módulo específico
```

**Reglas de Herencia:**
- Permiso de aplicación se hereda a todos sus módulos
- Permiso de módulo NO se hereda a la aplicación
- Nivel mayor prevalece sobre nivel menor

## 🚀 Orden de Implementación Recomendado

### Sprint 1: Backend Core (1 día)
1. ✅ Crear `permissions_service.py`
2. ✅ Añadir endpoints en `lambda_function.py`
3. ✅ Añadir validadores
4. ✅ Tests unitarios

### Sprint 2: Frontend (1.5 días)
1. ✅ Actualizar `api.js`
2. ✅ Crear UI de permisos en `index.html`
3. ✅ Implementar lógica en `dashboard.js`
4. ✅ Añadir estilos en `dashboard.css`

### Sprint 3: Testing y Documentación (0.5 días)
1. ✅ Testing end-to-end
2. ✅ Documentación
3. ✅ Deploy

**Total estimado: 2.5-3 días de desarrollo**

## 📚 Documentación Adicional Necesaria

1. **API Documentation**
   - Swagger/OpenAPI para nuevos endpoints
   - Ejemplos de uso

2. **User Guide**
   - Cómo asignar permisos
   - Mejores prácticas
   - Troubleshooting

3. **Admin Guide**
   - Gestión de tipos de permisos
   - Auditoría de permisos
   - Limpieza de permisos expirados

## ✅ Checklist de Implementación

### Backend
- [ ] Crear `permissions_service.py`
- [ ] Implementar CRUD de permisos de aplicaciones
- [ ] Implementar CRUD de permisos de módulos
- [ ] Añadir endpoints en Lambda
- [ ] Añadir validadores para permisos
- [ ] Añadir tests unitarios
- [ ] Añadir tests de integración

### Frontend
- [ ] Actualizar `api.js` con métodos de permisos
- [ ] Añadir pestaña "Permissions" en HTML (versión simple)
- [ ] Crear modal de asignación con duraciones predefinidas
- [ ] Implementar tabla de permisos (sin filtros ni paginación)
- [ ] Añadir lógica en `dashboard.js`
- [ ] Añadir estilos en CSS
- [ ] Testing manual

### Documentación
- [ ] Actualizar README
- [ ] Documentar API de permisos
- [ ] Crear guía de usuario
- [ ] Actualizar diagramas de arquitectura

### Deployment
- [ ] Actualizar Lambda
- [ ] Verificar permisos IAM
- [ ] Testing en DEV
- [ ] Testing en PRE
- [ ] Deploy a PRO

## 🎯 Resultado Esperado

Al finalizar la implementación, los administradores podrán:

1. ✅ Ver todos los permisos asignados en el sistema
2. ✅ Asignar permisos de aplicaciones a usuarios
3. ✅ Asignar permisos de módulos específicos a usuarios
4. ✅ Revocar permisos existentes
5. ✅ Establecer fechas de expiración para permisos
6. ✅ Filtrar y buscar permisos
7. ✅ Ver historial de cambios en auditoría

Y el sistema automáticamente:

1. ✅ Registrará todos los cambios en auditoría
2. ✅ Respetará la jerarquía de permisos
3. ✅ Manejará expiración de permisos

---

**Documento creado:** 2026-02-28
**Versión:** 1.0
**Autor:** Identity Manager Team
