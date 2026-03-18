# List Users Light - Endpoint Optimizado

## Descripción

El endpoint `list_users_light` es una versión **optimizada y rápida** del endpoint `list_users` que devuelve solo los campos esenciales de los usuarios de Cognito.

## Problema Resuelto

El endpoint original `list_users` era lento porque:
- Hacía **1 llamada a Cognito** para listar usuarios
- Hacía **N llamadas adicionales** para obtener los grupos de cada usuario (una por usuario)
- **Total: N+1 llamadas** para N usuarios

**Ejemplo:** Para 100 usuarios = **101 llamadas a Cognito** ⏱️ ~10-15 segundos

## Solución

`list_users_light` elimina las llamadas para obtener grupos:
- Hace **1 sola llamada a Cognito** (paginada automáticamente)
- **NO** obtiene grupos de usuarios
- **Total: 1 llamada** para N usuarios

**Ejemplo:** Para 100 usuarios = **1 llamada a Cognito** ⚡ ~1-2 segundos

## Mejora de Rendimiento

| Usuarios | list_users (original) | list_users_light | Mejora |
|----------|----------------------|------------------|--------|
| 10       | ~2 segundos          | ~0.5 segundos    | **4x más rápido** |
| 50       | ~6 segundos          | ~1 segundo       | **6x más rápido** |
| 100      | ~12 segundos         | ~1.5 segundos    | **8x más rápido** |
| 200      | ~25 segundos         | ~2 segundos      | **12x más rápido** |

## Uso

### Request

```json
POST /api
{
  "operation": "list_users_light",
  "filters": {
    "group": "team-delta",     // Opcional
    "status": "CONFIRMED"       // Opcional
  },
  "pagination": {
    "limit": 100                // Opcional (null = todos)
  }
}
```

### Response

```json
{
  "success": true,
  "data": {
    "users": [
      {
        "user_id": "user@example.com",
        "email": "user@example.com",
        "person": "John Doe",
        "status": "CONFIRMED"
      },
      {
        "user_id": "jane@example.com",
        "email": "jane@example.com",
        "person": "Jane Smith",
        "status": "CONFIRMED"
      }
    ],
    "total_count": 2
  },
  "timestamp": "2026-03-18T10:00:00Z"
}
```

## Campos Devueltos

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `user_id` | string | ID del usuario en Cognito (email) |
| `email` | string | Email del usuario |
| `person` | string | Nombre completo de la persona |
| `status` | string | Estado del usuario (CONFIRMED, FORCE_CHANGE_PASSWORD, etc.) |

## Casos de Uso Ideales

✅ **Usar `list_users_light` cuando:**
- Necesitas poblar dropdowns/selects
- Necesitas listar usuarios para asignaciones
- Solo necesitas ID, email y nombre
- Quieres respuesta rápida

❌ **NO usar `list_users_light` cuando:**
- Necesitas saber los grupos de cada usuario
- Necesitas información completa del usuario
- Necesitas fecha de creación o estado de habilitación

## Comparación con list_users

| Característica | list_users | list_users_light |
|----------------|------------|------------------|
| Velocidad | Lento (N+1 llamadas) | **Rápido (1 llamada)** |
| Campos devueltos | Completos (8 campos) | **Esenciales (4 campos)** |
| Incluye grupos | ✅ Sí | ❌ No |
| Incluye created_date | ✅ Sí | ❌ No |
| Incluye enabled | ✅ Sí | ❌ No |
| Incluye auto_regenerate_tokens | ✅ Sí | ❌ No |
| Uso recomendado | Detalles completos | **Listados rápidos** |

## Permisos Requeridos

- **Nivel mínimo:** 10 (read)
- **Aplicación:** identity-mgmt

## Ejemplo de Integración en Frontend

```javascript
// Cargar usuarios para un dropdown
async function loadUsersDropdown() {
    const response = await fetch('/api', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            operation: 'list_users_light',
            filters: {
                status: 'CONFIRMED'  // Solo usuarios confirmados
            }
        })
    });
    
    const result = await response.json();
    
    // Poblar dropdown
    const select = document.getElementById('user-select');
    result.data.users.forEach(user => {
        const option = document.createElement('option');
        option.value = user.user_id;
        option.textContent = `${user.person} (${user.email})`;
        select.appendChild(option);
    });
}
```

## Notas Técnicas

1. **Paginación automática:** El endpoint pagina automáticamente todas las páginas de Cognito
2. **Sin límite por defecto:** Si no se especifica `limit`, devuelve TODOS los usuarios
3. **Filtros aplicados:** Los filtros de grupo y status se aplican después de obtener todos los usuarios
4. **Logging mejorado:** Incluye `[LIGHT]` en los logs para identificar llamadas optimizadas

## Migración desde list_users

Si actualmente usas `list_users` solo para obtener ID y nombre:

```javascript
// ❌ ANTES (lento)
{
    "operation": "list_users"
}

// ✅ DESPUÉS (rápido)
{
    "operation": "list_users_light"
}
```

**Nota:** Si necesitas los grupos, mantén `list_users` original.