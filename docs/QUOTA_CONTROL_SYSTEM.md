# Sistema de Control de Cuotas Diarias

## Descripción General

Sistema de control de uso que limita el número de peticiones diarias por usuario al proxy de Bedrock, con bloqueo automático al alcanzar el límite y capacidad de desbloqueo administrativo.

## Modelo de Datos

### Extensión del Esquema

El sistema añade dos nuevas tablas al modelo de datos existente:

#### 1. `bedrock-proxy-user-quotas-tbl`

Tabla principal que almacena el estado de cuota de cada usuario.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | UUID | Identificador único |
| `cognito_user_id` | VARCHAR(255) | ID del usuario de Cognito |
| `cognito_email` | VARCHAR(255) | Email del usuario |
| `daily_request_limit` | INTEGER | Límite diario (NULL = usar default de config) |
| `current_date` | DATE | Fecha del día actual |
| `requests_today` | INTEGER | Contador de peticiones del día |
| `is_blocked` | BOOLEAN | Estado de bloqueo |
| `blocked_at` | TIMESTAMP | Momento del bloqueo |
| `administrative_safe` | BOOLEAN | Flag de desbloqueo administrativo |
| `administrative_safe_set_by` | VARCHAR(255) | Admin que desbloqueó |
| `administrative_safe_set_at` | TIMESTAMP | Momento del desbloqueo |
| `administrative_safe_reason` | TEXT | Razón del desbloqueo |
| `last_request_at` | TIMESTAMP | Última petición |
| `created_at` | TIMESTAMP | Fecha de creación |
| `updated_at` | TIMESTAMP | Última actualización |

**Características:**
- Un registro por usuario (UNIQUE en `cognito_user_id`)
- Creación lazy: se crea en la primera petición del usuario
- Persistente: nunca se elimina, solo se resetea diariamente

#### 2. `bedrock-proxy-quota-blocks-history-tbl`

Tabla de auditoría que registra todos los bloqueos y desbloqueos.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | UUID | Identificador único |
| `cognito_user_id` | VARCHAR(255) | ID del usuario |
| `cognito_email` | VARCHAR(255) | Email del usuario |
| `block_date` | DATE | Fecha del bloqueo |
| `blocked_at` | TIMESTAMP | Momento del bloqueo |
| `unblocked_at` | TIMESTAMP | Momento del desbloqueo |
| `unblock_type` | VARCHAR(20) | Tipo: 'automatic' o 'administrative' |
| `requests_count` | INTEGER | Peticiones realizadas |
| `daily_limit` | INTEGER | Límite que se alcanzó |
| `unblocked_by` | VARCHAR(255) | Admin que desbloqueó (si aplica) |
| `unblock_reason` | TEXT | Razón del desbloqueo |
| `created_at` | TIMESTAMP | Fecha de creación |

**Características:**
- Registro histórico completo
- Permite análisis de patrones de uso
- Auditoría de acciones administrativas

### Configuración Global

Se añade un parámetro en `identity-manager-config-tbl`:

```sql
config_key: 'default_daily_request_limit'
config_value: '1000'
description: 'Límite de peticiones diarias por defecto para nuevos usuarios'
```

## Procesos del Sistema

### 1. Validación del Token

**Flujo:**
```
1. Usuario envía petición con JWT
2. Lambda valida el token (proceso existente)
3. Extrae cognito_user_id y cognito_email
4. Procede a verificación de cuota
```

**Sin cambios en el proceso de validación existente.**

### 2. Procesamiento de Nueva Petición

**Función:** `check_and_update_quota(cognito_user_id, cognito_email)`

**Flujo:**

```
┌─────────────────────────────────────┐
│ 1. Obtener/Crear registro usuario  │
│    - Si no existe → crear con       │
│      requests_today = 0             │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 2. Obtener límite diario            │
│    - Si daily_request_limit = NULL  │
│      → usar default de config (1000)│
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 3. Verificar si es nuevo día        │
│    - Si current_date < HOY          │
│      → Ejecutar RESET DIARIO        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 4. Verificar estado de bloqueo      │
│    - Si is_blocked = true Y         │
│      administrative_safe = false    │
│      → RECHAZAR petición (429)      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 5. Verificar límite                 │
│    - Si requests_today >= limit Y   │
│      administrative_safe = false    │
│      → BLOQUEAR usuario             │
│      → Registrar en historial       │
│      → RECHAZAR petición (429)      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 6. Incrementar contador             │
│    - requests_today++               │
│    - last_request_at = NOW()        │
│    - PERMITIR petición (200)        │
└─────────────────────────────────────┘
```

**Respuesta de la función:**
```json
{
  "allowed": true/false,
  "requests_today": 123,
  "daily_limit": 1000,
  "is_blocked": false,
  "block_reason": null/"mensaje de error"
}
```

**Integración en Lambda:**
```python
# Antes de procesar la petición a Bedrock
quota_check = check_and_update_quota(user_id, user_email)

if not quota_check['allowed']:
    return {
        'statusCode': 429,
        'body': {
            'error': 'QuotaExceeded',
            'message': quota_check['block_reason'],
            'requests_today': quota_check['requests_today'],
            'daily_limit': quota_check['daily_limit']
        }
    }

# Continuar con petición a Bedrock...
```

### 3. Reset Diario y Desbloqueo Automático

**Cuándo:** Primera petición del usuario después de medianoche

**Trigger:** La función `check_and_update_quota()` detecta `current_date < CURRENT_DATE`

**Acciones:**
```sql
UPDATE "bedrock-proxy-user-quotas-tbl"
SET 
    current_date = CURRENT_DATE,
    requests_today = 0,              -- Reset contador
    is_blocked = false,              -- Desbloqueo automático
    blocked_at = NULL,
    administrative_safe = false,     -- Reset flag administrativo
    administrative_safe_set_by = NULL,
    administrative_safe_set_at = NULL,
    administrative_safe_reason = NULL,
    updated_at = CURRENT_TIMESTAMP
WHERE cognito_user_id = p_cognito_user_id;
```

**Registro en historial:**
```sql
-- Si el usuario estaba bloqueado
UPDATE "bedrock-proxy-quota-blocks-history-tbl"
SET 
    unblocked_at = CURRENT_TIMESTAMP,
    unblock_type = 'automatic'
WHERE cognito_user_id = p_cognito_user_id
  AND block_date = (fecha anterior)
  AND unblocked_at IS NULL;
```

**Características:**
- Automático y transparente
- No requiere proceso batch
- Se ejecuta en la primera petición del día
- Resetea tanto el contador como el flag administrativo

### 4. Aplicación de Administrative Safe

**Función:** `administrative_unblock_user(cognito_user_id, admin_user_id, reason)`

**Cuándo:** Un administrador necesita desbloquear a un usuario manualmente

**Flujo:**
```
┌─────────────────────────────────────┐
│ 1. Admin identifica usuario         │
│    bloqueado en dashboard            │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 2. Admin ejecuta desbloqueo         │
│    - Proporciona razón               │
│    - Sistema valida permisos         │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 3. Actualizar registro de cuota     │
│    - administrative_safe = true      │
│    - is_blocked = false              │
│    - Registrar admin y razón         │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 4. Actualizar historial              │
│    - unblocked_at = NOW()            │
│    - unblock_type = 'administrative' │
│    - unblocked_by = admin_user_id    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 5. Usuario puede continuar          │
│    - Hasta medianoche                │
│    - Sin límite de peticiones        │
└─────────────────────────────────────┘
```

**Ejemplo de uso:**
```sql
SELECT administrative_unblock_user(
    'us-east-1_abc123',
    'admin@example.com',
    'Usuario necesita completar tarea urgente'
);
```

**Características:**
- El usuario puede hacer peticiones ilimitadas hasta medianoche
- El flag `administrative_safe` se resetea automáticamente al día siguiente
- Queda registrado en historial con trazabilidad completa
- No modifica el contador `requests_today`

### 5. Actualización de Cuota por Administrador

**Función:** `update_user_daily_limit(cognito_user_id, new_limit)`

**Cuándo:** Un administrador necesita cambiar el límite diario de un usuario específico

**Flujo:**
```
┌─────────────────────────────────────┐
│ 1. Admin identifica usuario         │
│    que necesita límite diferente     │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 2. Admin establece nuevo límite     │
│    - Ejemplo: 5000 para usuario VIP │
│    - Sistema valida límite >= 0     │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 3. Actualizar registro              │
│    - daily_request_limit = new_limit│
│    - updated_at = NOW()              │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 4. Límite aplicado inmediatamente   │
│    - Afecta a próximas peticiones    │
│    - Persiste entre días             │
└─────────────────────────────────────┘
```

**Ejemplo de uso:**
```sql
-- Usuario VIP con límite alto
SELECT update_user_daily_limit('us-east-1_vip001', 10000);

-- Usuario de prueba con límite bajo
SELECT update_user_daily_limit('us-east-1_test001', 100);

-- Volver a límite por defecto (usar NULL)
UPDATE "bedrock-proxy-user-quotas-tbl"
SET daily_request_limit = NULL
WHERE cognito_user_id = 'us-east-1_user001';
```

**Características:**
- Límite personalizado por usuario
- Persiste entre días (no se resetea)
- NULL = usar límite por defecto de config
- Cambio inmediato (no requiere reinicio)

## Vistas de Consulta

### `v_quota_status`
Estado actual de todos los usuarios con sus cuotas.

### `v_blocked_users`
Lista de usuarios actualmente bloqueados.

### `v_users_near_limit`
Usuarios que han usado más del 80% de su cuota.

## Ejemplo de Flujo Completo

```
DÍA 1 - 2026-03-02
==================

09:00 - Usuario hace primera petición
        → Crea registro en tabla
        → requests_today = 1
        → Petición PERMITIDA

09:15 - Usuario hace petición 2
        → requests_today = 2
        → Petición PERMITIDA

...

18:30 - Usuario hace petición 1000
        → requests_today = 1000
        → Alcanza límite
        → is_blocked = true
        → Registro en historial
        → Petición RECHAZADA (429)

18:31 - Usuario intenta petición 1001
        → is_blocked = true
        → administrative_safe = false
        → Petición RECHAZADA (429)

19:00 - Admin desbloquea usuario
        → administrative_safe = true
        → is_blocked = false
        → Actualiza historial

19:05 - Usuario hace petición 1001
        → administrative_safe = true
        → Petición PERMITIDA

DÍA 2 - 2026-03-03
==================

08:00 - Usuario hace primera petición del nuevo día
        → Detecta current_date < HOY
        → RESET AUTOMÁTICO:
           * requests_today = 0
           * is_blocked = false
           * administrative_safe = false
        → Petición PERMITIDA (requests_today = 1)

08:15 - Usuario hace petición 2
        → requests_today = 2
        → Petición PERMITIDA

(El ciclo se repite)
```

## Consideraciones de Implementación

### Rendimiento
- Tabla pequeña (un registro por usuario activo)
- Índices optimizados para consultas frecuentes
- Operación atómica con `FOR UPDATE`

### Escalabilidad
- Diseño preparado para millones de usuarios
- Sin procesos batch necesarios
- Reset distribuido (en primera petición de cada usuario)

### Seguridad
- Trazabilidad completa en historial
- Validación de permisos administrativos
- Auditoría de todas las acciones

### Mantenimiento
- Sin limpieza necesaria (registros se reutilizan)
- Historial puede archivarse periódicamente
- Configuración centralizada en tabla config