# User Quotas Dashboard

## Descripción

Nueva vista en el dashboard de Identity Manager que muestra el estado de cuotas de usuarios en tiempo real, incluyendo uso diario, límites establecidos y estado de bloqueo.

## Características

### Vista Principal

La vista de User Quotas muestra:

1. **Tarjetas de Resumen (KPIs)**
   - Active Users Today: Usuarios con uso en el día actual
   - Blocked Users: Usuarios bloqueados por exceder cuota
   - Admin Safe Users: Usuarios protegidos de bloqueo automático
   - Avg Usage: Promedio de peticiones por usuario

2. **Tabla de Cuotas**
   - User ID
   - Email
   - Person (nombre completo)
   - Team (equipo)
   - Requests Today (peticiones del día)
   - Daily Limit (límite diario establecido)
   - Usage % (porcentaje de consumo con barra visual)
   - Status (ACTIVE, BLOCKED, ADMIN_SAFE)
   - Blocked Until (fecha/hora de desbloqueo si aplica)

### Funcionalidades

- **Búsqueda**: Filtrado en tiempo real por user ID, email, person, team o status
- **Paginación**: 10 registros por página
- **Exportación**: Descarga de datos en formato CSV
- **Actualización**: Botón de refresh para recargar datos
- **Indicadores Visuales**: Barras de progreso con código de colores según porcentaje de uso

### Código de Colores

- **Verde** (0-49%): Uso normal
- **Amarillo** (50-74%): Uso moderado
- **Naranja** (75-89%): Uso alto
- **Rojo** (90-100%): Uso crítico
- **Morado**: Admin Safe (protegido)

## Endpoint API Requerido

### GET /proxy/quotas/today

Endpoint necesario en el backend para obtener las cuotas de usuarios del día actual.

#### Request

```http
GET /proxy/quotas/today HTTP/1.1
Host: api.identity-manager.com
Authorization: Bearer <JWT_TOKEN>
```

#### Response

```json
{
  "success": true,
  "data": [
    {
      "cognito_user_id": "us-east-1:12345678-1234-1234-1234-123456789012",
      "cognito_email": "user@example.com",
      "person": "John Doe",
      "team": "Engineering",
      "requests_today": 450,
      "daily_limit": 1000,
      "is_blocked": false,
      "administrative_safe": false,
      "blocked_until": null,
      "status": "ACTIVE"
    },
    {
      "cognito_user_id": "us-east-1:87654321-4321-4321-4321-210987654321",
      "cognito_email": "admin@example.com",
      "person": "Jane Smith",
      "team": "DevOps",
      "requests_today": 1200,
      "daily_limit": 1000,
      "is_blocked": false,
      "administrative_safe": true,
      "blocked_until": null,
      "status": "ADMIN_SAFE"
    },
    {
      "cognito_user_id": "us-east-1:11111111-2222-3333-4444-555555555555",
      "cognito_email": "blocked@example.com",
      "person": "Bob Johnson",
      "team": "QA",
      "requests_today": 1050,
      "daily_limit": 1000,
      "is_blocked": true,
      "administrative_safe": false,
      "blocked_until": "2026-03-06T00:00:00Z",
      "status": "BLOCKED"
    }
  ],
  "message": "User quotas retrieved successfully"
}
```

#### Campos de Respuesta

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `cognito_user_id` | string | ID único del usuario en Cognito |
| `cognito_email` | string | Email del usuario |
| `person` | string | Nombre completo del usuario |
| `team` | string | Equipo al que pertenece |
| `requests_today` | integer | Número de peticiones realizadas hoy |
| `daily_limit` | integer | Límite diario de peticiones |
| `is_blocked` | boolean | Si el usuario está bloqueado |
| `administrative_safe` | boolean | Si tiene protección administrativa |
| `blocked_until` | string\|null | Fecha/hora hasta la que está bloqueado (ISO 8601) |
| `status` | string | Estado calculado: ACTIVE, BLOCKED, ADMIN_SAFE |

#### Lógica de Status

El campo `status` se calcula según:

```python
if administrative_safe == True:
    status = "ADMIN_SAFE"
elif is_blocked == True:
    status = "BLOCKED"
else:
    status = "ACTIVE"
```

#### Query SQL Sugerida

```sql
SELECT 
    cognito_user_id,
    cognito_email,
    person,
    team,
    requests_today,
    COALESCE(daily_request_limit, 1000) as daily_limit,
    is_blocked,
    administrative_safe,
    blocked_until,
    CASE 
        WHEN administrative_safe = true THEN 'ADMIN_SAFE'
        WHEN is_blocked = true THEN 'BLOCKED'
        ELSE 'ACTIVE'
    END as status
FROM "bedrock-proxy-user-quotas-tbl"
WHERE quota_date = CURRENT_DATE
    AND requests_today > 0
ORDER BY requests_today DESC;
```

#### Códigos de Error

| Código | Descripción |
|--------|-------------|
| 200 | Éxito |
| 401 | No autorizado (token inválido) |
| 403 | Permisos insuficientes |
| 500 | Error interno del servidor |

## Implementación Backend

### Ubicación del Endpoint

El endpoint debe implementarse en:
```
backend/lambdas/identity-mgmt-api/lambda_function.py
```

### Ejemplo de Implementación

```python
@app.route('/proxy/quotas/today', methods=['GET'])
@require_auth
def get_user_quotas_today():
    """
    Get user quotas for today
    """
    try:
        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Query user quotas for today
        query = """
            SELECT 
                cognito_user_id,
                cognito_email,
                person,
                team,
                requests_today,
                COALESCE(daily_request_limit, 1000) as daily_limit,
                is_blocked,
                administrative_safe,
                blocked_until,
                CASE 
                    WHEN administrative_safe = true THEN 'ADMIN_SAFE'
                    WHEN is_blocked = true THEN 'BLOCKED'
                    ELSE 'ACTIVE'
                END as status
            FROM "bedrock-proxy-user-quotas-tbl"
            WHERE quota_date = CURRENT_DATE
                AND requests_today > 0
            ORDER BY requests_today DESC;
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Format results
        quotas = []
        for row in rows:
            quotas.append({
                'cognito_user_id': row[0],
                'cognito_email': row[1],
                'person': row[2],
                'team': row[3],
                'requests_today': row[4],
                'daily_limit': row[5],
                'is_blocked': row[6],
                'administrative_safe': row[7],
                'blocked_until': row[8].isoformat() if row[8] else None,
                'status': row[9]
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': quotas,
            'message': 'User quotas retrieved successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting user quotas: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error retrieving user quotas: {str(e)}'
        }), 500
```

## Archivos Modificados/Creados

### Nuevos Archivos

1. **frontend/dashboard/js/user-quotas.js**
   - Lógica JavaScript para la vista de cuotas
   - Funciones de carga, filtrado, paginación y exportación

2. **docs/09-USER-QUOTAS-DASHBOARD.md**
   - Documentación completa de la feature

### Archivos Modificados

1. **frontend/dashboard/index.html**
   - Añadido botón de navegación "User Quotas"
   - Añadida sección HTML completa para la vista
   - Referencia al nuevo archivo JS

2. **frontend/dashboard/css/dashboard.css**
   - Estilos para badges ADMIN_SAFE y ACTIVE
   - Estilos para barras de progreso de uso

## Testing

### Pruebas Manuales

1. **Verificar Carga de Datos**
   ```bash
   curl -X GET https://api.identity-manager.com/proxy/quotas/today \
     -H "Authorization: Bearer <TOKEN>"
   ```

2. **Verificar Búsqueda**
   - Buscar por email
   - Buscar por team
   - Buscar por status

3. **Verificar Exportación**
   - Exportar datos a CSV
   - Verificar formato del archivo

4. **Verificar Paginación**
   - Navegar entre páginas
   - Verificar contadores

### Casos de Prueba

| Caso | Entrada | Resultado Esperado |
|------|---------|-------------------|
| Usuario activo normal | requests_today: 500, limit: 1000 | Status: ACTIVE, barra verde |
| Usuario cerca del límite | requests_today: 950, limit: 1000 | Status: ACTIVE, barra roja |
| Usuario bloqueado | is_blocked: true | Status: BLOCKED, badge rojo |
| Usuario admin safe | administrative_safe: true | Status: ADMIN_SAFE, badge morado |
| Sin uso hoy | requests_today: 0 | No aparece en la lista |

## Mantenimiento

### Actualización de Datos

Los datos se actualizan:
- Automáticamente al cargar la vista
- Manualmente con el botón "Refresh"
- Los datos provienen de la tabla `bedrock-proxy-user-quotas-tbl`

### Monitoreo

Verificar regularmente:
- Tiempo de respuesta del endpoint
- Precisión de los contadores
- Funcionamiento de los filtros
- Exportación de CSV

## Próximas Mejoras

1. **Filtros Avanzados**
   - Filtro por rango de uso (0-25%, 25-50%, etc.)
   - Filtro por team
   - Filtro por status

2. **Gráficos**
   - Distribución de uso por equipos
   - Tendencia de uso diario
   - Top usuarios por consumo

3. **Acciones**
   - Botón para desbloquear usuario
   - Botón para activar/desactivar admin safe
   - Botón para ajustar límite diario

4. **Notificaciones**
   - Alertas cuando usuarios se acercan al límite
   - Notificaciones de bloqueos
   - Resumen diario por email

## Soporte

Para problemas o preguntas sobre esta feature:
- Revisar logs del backend en CloudWatch
- Verificar permisos del usuario en la base de datos
- Comprobar que el endpoint está desplegado correctamente