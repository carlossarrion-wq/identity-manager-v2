# Sistema de Permisos

## 📋 Visión General

El sistema de permisos de Identity Manager v2 proporciona control granular de acceso a aplicaciones y módulos mediante una jerarquía de tres niveles.

## 🎯 Niveles de Permisos

### Tipos de Permisos

| Tipo | Nivel | Descripción |
|------|-------|-------------|
| **Read-only** | 10 | Solo lectura, sin modificaciones |
| **Write** | 50 | Lectura y escritura |
| **Admin** | 100 | Control total, gestión de permisos |

## 🏗️ Jerarquía de Permisos

```
Aplicación (ej: cline)
    ↓
Módulo (ej: chat)
    ↓
Operación (read/write/admin)
```

### Herencia
- Permiso de **aplicación** se hereda a todos sus módulos
- Permiso de **módulo** es específico y no afecta otros módulos
- Permiso de **nivel superior** prevalece sobre nivel inferior

## 📊 Estructura en Base de Datos

### Tablas Principales

**identity-manager-permission-types-tbl**
- Define tipos de permisos disponibles
- Incluye nivel jerárquico

**identity-manager-app-permissions-tbl**
- Permisos sobre aplicaciones completas
- Un usuario puede tener un permiso por aplicación

**identity-manager-module-permissions-tbl**
- Permisos sobre módulos específicos
- Un usuario puede tener un permiso por módulo

## 🔐 Validación de Permisos

### Flujo de Validación

1. **Verificar permiso de aplicación**
   - Si existe y está activo → permitir
   - Si no existe → continuar

2. **Verificar permiso de módulo**
   - Si existe y está activo → permitir
   - Si no existe → denegar

3. **Verificar nivel de permiso**
   - Comparar nivel requerido vs nivel otorgado
   - Permitir si nivel otorgado >= nivel requerido

### Ejemplo

```
Usuario: john@example.com
Aplicación: cline
Módulo: chat
Operación: write (nivel 50)

Verificación:
1. ¿Tiene permiso en "cline"? → Sí, Admin (100) → ✅ PERMITIR
2. No es necesario verificar módulo (herencia)
```

## 🎫 Asignación de Permisos

### Permiso de Aplicación

```json
{
  "operation": "assign_app_permission",
  "data": {
    "user_id": "cognito_user_id",
    "user_email": "user@example.com",
    "application_id": "app_uuid",
    "permission_type_id": "permission_uuid",
    "duration_days": 90
  }
}
```

### Permiso de Módulo

```json
{
  "operation": "assign_module_permission",
  "data": {
    "user_id": "cognito_user_id",
    "user_email": "user@example.com",
    "module_id": "module_uuid",
    "permission_type_id": "permission_uuid",
    "duration_days": 90
  }
}
```

## ⏰ Expiración de Permisos

- Los permisos pueden tener fecha de expiración opcional
- Campo `expires_at` en tablas de permisos
- Verificación automática en validación
- Permisos expirados se consideran inactivos

## 🔄 Revocación y Restauración

### Revocación
- Marca permiso como inactivo (`is_active = false`)
- No elimina el registro (auditoría)
- Efecto inmediato

### Restauración
- Reactiva permiso revocado
- Verifica que no haya expirado
- Registra en auditoría

## 📝 Mejores Prácticas

1. **Principio de Mínimo Privilegio**
   - Asignar solo permisos necesarios
   - Preferir permisos de módulo sobre aplicación

2. **Revisión Periódica**
   - Auditar permisos regularmente
   - Revocar permisos no utilizados

3. **Duración Limitada**
   - Usar `duration_days` para permisos temporales
   - Renovar solo si es necesario

4. **Documentación**
   - Documentar razón de asignación
   - Mantener registro de cambios

## 🔍 Consulta de Permisos

### Ver Permisos de Usuario

```json
{
  "operation": "get_user_permissions",
  "user_id": "cognito_user_id"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user_id": "cognito_user_id",
    "email": "user@example.com",
    "permissions": [
      {
        "scope": "application",
        "resource_name": "cline",
        "permission_type": "Admin",
        "permission_level": 100,
        "is_active": true,
        "granted_at": "2026-01-01T00:00:00Z",
        "expires_at": null
      },
      {
        "scope": "module",
        "resource_name": "chat",
        "permission_type": "Write",
        "permission_level": 50,
        "is_active": true,
        "granted_at": "2026-01-01T00:00:00Z",
        "expires_at": "2026-04-01T00:00:00Z"
      }
    ]
  }
}
```

## 🔗 Referencias

- [API Reference](./04-API-REFERENCE.md)
- [Arquitectura del Sistema](./02-ARCHITECTURE.md)
- [Base de Datos](./07-DATABASE.md)