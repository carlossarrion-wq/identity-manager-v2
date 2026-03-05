# API Reference

## 📋 Información General

**Base URL:** `https://api.identity-manager.com/v1`  
**Método:** POST  
**Content-Type:** application/json  
**Autenticación:** AWS Cognito Session (admin) o JWT (proxy)

## 🔐 Estructura de Request

```json
{
  "operation": "operation_name",
  "data": {},
  "filters": {},
  "pagination": {}
}
```

## 👥 Operaciones de Usuarios

### list_users
Lista usuarios de Cognito con filtros opcionales.

**Request:**
```json
{
  "operation": "list_users",
  "filters": {
    "group": "developers-group",
    "status": "CONFIRMED"
  },
  "pagination": {
    "limit": 60,
    "pagination_token": "token"
  }
}
```

### create_user
Crea un nuevo usuario en Cognito.

**Request:**
```json
{
  "operation": "create_user",
  "data": {
    "email": "user@example.com",
    "person": "John Doe",
    "group": "developers-group",
    "temporary_password": "TempPass123!",
    "send_email": true,
    "auto_regenerate_tokens": true
  }
}
```

### delete_user
Elimina usuario y todos sus datos relacionados.

**Request:**
```json
{
  "operation": "delete_user",
  "user_id": "cognito_user_id"
}
```

## 🎫 Operaciones de Tokens

### list_tokens
Lista tokens JWT con filtros.

**Request:**
```json
{
  "operation": "list_tokens",
  "filters": {
    "user_id": "cognito_user_id",
    "status": "active",
    "profile_id": "profile_uuid"
  },
  "pagination": {
    "limit": 50,
    "offset": 0
  }
}
```

### create_token
Genera un nuevo token JWT.

**Request:**
```json
{
  "operation": "create_token",
  "data": {
    "user_id": "cognito_user_id",
    "application_profile_id": "profile_uuid",
    "validity_period": "90_days",
    "send_email": false
  }
}
```

**Períodos de validez:**
- `1_day`: 24 horas
- `7_days`: 7 días
- `30_days`: 30 días
- `60_days`: 60 días
- `90_days`: 90 días (default)

### validate_token
Valida un token JWT.

**Request:**
```json
{
  "operation": "validate_token",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### revoke_token
Revoca un token JWT.

**Request:**
```json
{
  "operation": "revoke_token",
  "token_id": "token_uuid",
  "reason": "User changed role"
}
```

### restore_token
Restaura un token revocado.

**Request:**
```json
{
  "operation": "restore_token",
  "token_id": "token_uuid"
}
```

### delete_token
Elimina permanentemente un token.

**Request:**
```json
{
  "operation": "delete_token",
  "token_id": "token_uuid"
}
```

### regenerate_token
Regenera automáticamente un token expirado.

**Request:**
```json
{
  "operation": "regenerate_token",
  "data": {
    "expired_token_jti": "old_jti",
    "user_id": "cognito_user_id",
    "client_ip": "192.168.1.1",
    "user_agent": "Mozilla/5.0..."
  }
}
```

## 🔑 Operaciones de Permisos

### assign_app_permission
Asigna permiso de aplicación a usuario.

**Request:**
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

### assign_module_permission
Asigna permiso de módulo a usuario.

**Request:**
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

### revoke_app_permission
Revoca permiso de aplicación.

**Request:**
```json
{
  "operation": "revoke_app_permission",
  "user_id": "cognito_user_id",
  "application_id": "app_uuid"
}
```

### revoke_module_permission
Revoca permiso de módulo.

**Request:**
```json
{
  "operation": "revoke_module_permission",
  "user_id": "cognito_user_id",
  "module_id": "module_uuid"
}
```

### get_user_permissions
Obtiene todos los permisos de un usuario.

**Request:**
```json
{
  "operation": "get_user_permissions",
  "user_id": "cognito_user_id"
}
```

### list_all_permissions
Lista todos los permisos del sistema.

**Request:**
```json
{
  "operation": "list_all_permissions"
}
```

### list_permission_types
Lista tipos de permisos disponibles.

**Request:**
```json
{
  "operation": "list_permission_types"
}
```

### list_applications
Lista aplicaciones del sistema.

**Request:**
```json
{
  "operation": "list_applications"
}
```

### list_modules
Lista módulos de una aplicación.

**Request:**
```json
{
  "operation": "list_modules",
  "application_id": "app_uuid"
}
```

## 📊 Operaciones de Uso del Proxy

### get_proxy_usage_summary
Obtiene resumen de métricas (KPIs).

**Request:**
```json
{
  "operation": "get_proxy_usage_summary",
  "filters": {
    "start_date": "2026-03-01T00:00:00Z",
    "end_date": "2026-03-07T23:59:59Z",
    "user_id": "optional_user_id"
  }
}
```

### get_proxy_usage_by_hour
Obtiene distribución por hora del día.

**Request:**
```json
{
  "operation": "get_proxy_usage_by_hour",
  "filters": {
    "start_date": "2026-03-01T00:00:00Z",
    "end_date": "2026-03-07T23:59:59Z"
  }
}
```

### get_proxy_usage_by_team
Obtiene distribución por equipo.

**Request:**
```json
{
  "operation": "get_proxy_usage_by_team",
  "filters": {
    "start_date": "2026-03-01T00:00:00Z",
    "end_date": "2026-03-07T23:59:59Z"
  }
}
```

### get_proxy_usage_by_day
Obtiene distribución por día.

**Request:**
```json
{
  "operation": "get_proxy_usage_by_day",
  "filters": {
    "start_date": "2026-03-01T00:00:00Z",
    "end_date": "2026-03-07T23:59:59Z"
  }
}
```

### get_proxy_usage_response_status
Obtiene distribución de estados de respuesta.

**Request:**
```json
{
  "operation": "get_proxy_usage_response_status",
  "filters": {
    "start_date": "2026-03-01T00:00:00Z",
    "end_date": "2026-03-07T23:59:59Z"
  }
}
```

### get_proxy_usage_trend
Obtiene tendencia de uso por equipo.

**Request:**
```json
{
  "operation": "get_proxy_usage_trend",
  "filters": {
    "start_date": "2026-03-01T00:00:00Z",
    "end_date": "2026-03-07T23:59:59Z"
  }
}
```

### get_proxy_usage_by_user
Obtiene uso por usuario con paginación.

**Request:**
```json
{
  "operation": "get_proxy_usage_by_user",
  "filters": {
    "start_date": "2026-03-01T00:00:00Z",
    "end_date": "2026-03-07T23:59:59Z"
  },
  "pagination": {
    "page": 1,
    "page_size": 10
  }
}
```

## 🎯 Otras Operaciones

### list_profiles
Lista perfiles de inferencia.

**Request:**
```json
{
  "operation": "list_profiles",
  "filters": {
    "application_id": "app_uuid",
    "is_active": true
  }
}
```

### list_groups
Lista grupos de Cognito.

**Request:**
```json
{
  "operation": "list_groups"
}
```

### get_config
Obtiene configuración del sistema.

**Request:**
```json
{
  "operation": "get_config"
}
```

## 📝 Estructura de Response

### Success Response
```json
{
  "success": true,
  "data": {},
  "message": "Operation completed successfully",
  "timestamp": "2026-03-05T09:45:00Z"
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Error description",
    "details": {}
  },
  "timestamp": "2026-03-05T09:45:00Z"
}
```

## ⚠️ Códigos de Error

| Código | Descripción |
|--------|-------------|
| `INVALID_OPERATION` | Operación no reconocida |
| `MISSING_PARAMETERS` | Faltan parámetros requeridos |
| `USER_NOT_FOUND` | Usuario no existe |
| `TOKEN_LIMIT_EXCEEDED` | Límite de tokens alcanzado |
| `PROFILE_NOT_FOUND` | Perfil no existe |
| `PROFILE_INACTIVE` | Perfil inactivo |
| `DATABASE_ERROR` | Error en BD |
| `COGNITO_ERROR` | Error en Cognito |
| `UNAUTHORIZED` | No autorizado |
| `VALIDATION_ERROR` | Error de validación |

## 🔗 Referencias

- [Arquitectura del Sistema](./02-ARCHITECTURE.md)
- [Guía de Instalación](./03-INSTALLATION.md)
- [Sistema de Permisos](./05-PERMISSIONS.md)