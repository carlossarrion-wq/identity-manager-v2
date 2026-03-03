# Implementación Backend - Dashboard de Uso del Proxy

## ✅ Resumen de Implementación

Se ha completado la implementación del backend para el dashboard de uso del proxy Bedrock. Esta implementación proporciona 7 endpoints API para consultar y agregar datos de uso almacenados en la tabla `bedrock-proxy-usage-tracking-tbl`.

## 📁 Archivos Creados/Modificados

### 1. **Nuevo Servicio: `proxy_usage_service.py`**
**Ubicación:** `backend/lambdas/identity-mgmt-api/services/proxy_usage_service.py`

**Descripción:** Servicio completo para gestionar consultas de uso del proxy.

**Características:**
- ✅ 7 métodos públicos para diferentes agregaciones
- ✅ Queries SQL optimizadas con índices existentes
- ✅ Cálculo automático de cambios porcentuales
- ✅ Manejo robusto de casos edge (sin datos, divisiones por cero)
- ✅ Logging detallado para debugging
- ✅ Documentación completa con docstrings

**Métodos Implementados:**

| Método | Descripción | Retorna |
|--------|-------------|---------|
| `get_summary()` | KPIs y métricas agregadas con comparación vs período anterior | Total requests, tokens, cost, avg response time + cambios % |
| `get_usage_by_hour()` | Distribución de uso por hora del día (0-23h) | Array de 24 valores + hora pico |
| `get_usage_by_team()` | Uso agregado por equipo/grupo Cognito | Labels, values, equipo top |
| `get_usage_by_day()` | Tendencia diaria de uso | Labels por fecha, values, día pico |
| `get_response_status()` | Distribución de estados de respuesta | Labels de estados, counts, tasa de éxito |
| `get_usage_trend()` | Series temporales por equipo | Datasets multi-serie para gráfica de líneas |
| `get_usage_by_user()` | Detalle por usuario con paginación | Lista de usuarios + metadata de paginación |

### 2. **Lambda Function Actualizada: `lambda_function.py`**
**Ubicación:** `backend/lambdas/identity-mgmt-api/lambda_function.py`

**Cambios Realizados:**

#### a) Importación del Servicio
```python
from services.proxy_usage_service import ProxyUsageService
```

#### b) Inicialización Global
```python
proxy_usage_service = None

def initialize_services():
    # ...
    if proxy_usage_service is None:
        proxy_usage_service = ProxyUsageService(database_service)
```

#### c) Routing de Operaciones
Agregadas 7 nuevas operaciones al diccionario de routing:
```python
operations = {
    # ... operaciones existentes ...
    
    # Operaciones de uso del proxy
    'get_proxy_usage_summary': handle_get_proxy_usage_summary,
    'get_proxy_usage_by_hour': handle_get_proxy_usage_by_hour,
    'get_proxy_usage_by_team': handle_get_proxy_usage_by_team,
    'get_proxy_usage_by_day': handle_get_proxy_usage_by_day,
    'get_proxy_usage_response_status': handle_get_proxy_usage_response_status,
    'get_proxy_usage_trend': handle_get_proxy_usage_trend,
    'get_proxy_usage_by_user': handle_get_proxy_usage_by_user,
}
```

#### d) Handlers Implementados
7 nuevos handlers con:
- ✅ Parsing de fechas ISO 8601
- ✅ Extracción de filtros y paginación
- ✅ Llamadas al servicio
- ✅ Formato de respuesta consistente
- ✅ Logging apropiado

## 🔌 Endpoints API Disponibles

### 1. GET /proxy-usage/summary
**Operación:** `get_proxy_usage_summary`

**Request:**
```json
{
  "operation": "get_proxy_usage_summary",
  "filters": {
    "start_date": "2026-03-01T00:00:00Z",
    "end_date": "2026-03-07T23:59:59Z",
    "user_id": "optional-user-id"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "total_requests": 12458,
    "requests_change": "+15.2%",
    "total_tokens": 2400000,
    "tokens_change": "+12.3%",
    "total_cost": 124.50,
    "cost_change": "+18.1%",
    "avg_response_time": 1234,
    "response_time_change": "-5.2%",
    "period": {
      "start": "2026-03-01T00:00:00+00:00",
      "end": "2026-03-07T23:59:59+00:00"
    }
  }
}
```

### 2. GET /proxy-usage/by-hour
**Operación:** `get_proxy_usage_by_hour`

**Response:**
```json
{
  "success": true,
  "data": {
    "labels": ["00h", "01h", ..., "23h"],
    "values": [45, 23, ..., 89],
    "peak_hour": {
      "hour": "14:00",
      "requests": 1234
    }
  }
}
```

### 3. GET /proxy-usage/by-team
**Operación:** `get_proxy_usage_by_team`

**Response:**
```json
{
  "success": true,
  "data": {
    "labels": ["Team Alpha", "Team Beta", "Team Gamma"],
    "values": [5678, 3456, 2345],
    "top_team": {
      "name": "Team Alpha",
      "requests": 5678,
      "percentage": 45.6
    }
  }
}
```

### 4. GET /proxy-usage/by-day
**Operación:** `get_proxy_usage_by_day`

**Response:**
```json
{
  "success": true,
  "data": {
    "labels": ["2026-03-01", "2026-03-02", ...],
    "values": [2345, 2678, 3567, ...],
    "peak_day": {
      "date": "2026-03-03",
      "requests": 3567
    }
  }
}
```

### 5. GET /proxy-usage/response-status
**Operación:** `get_proxy_usage_response_status`

**Response:**
```json
{
  "success": true,
  "data": {
    "labels": ["Success (200)", "Rate Limited (429)", ...],
    "values": [12271, 98, 45, 23, 15, 6],
    "success_rate": {
      "percentage": 98.5,
      "successful_requests": 12271,
      "total_requests": 12458
    }
  }
}
```

### 6. GET /proxy-usage/trend
**Operación:** `get_proxy_usage_trend`

**Response:**
```json
{
  "success": true,
  "data": {
    "labels": ["2026-03-01", "2026-03-02", ...],
    "datasets": [
      {
        "label": "Team Alpha",
        "data": [1200, 1350, 1500, ...]
      },
      {
        "label": "Team Beta",
        "data": [800, 900, 1100, ...]
      }
    ]
  }
}
```

### 7. GET /proxy-usage/by-user
**Operación:** `get_proxy_usage_by_user`

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

**Response:**
```json
{
  "success": true,
  "data": {
    "users": [
      {
        "email": "john.doe@example.com",
        "person": "John Doe",
        "team": "Team Alpha",
        "requests": 1234,
        "tokens": 245600,
        "cost": 12.28
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 10,
      "total_records": 45,
      "total_pages": 5
    }
  }
}
```

## 🗄️ Queries SQL Utilizadas

### Tablas Consultadas
- ✅ `bedrock-proxy-usage-tracking-tbl` (principal)
- ✅ `identity-manager-users-tbl` (para nombres de usuario)
- ✅ `identity-manager-cognito-groups-tbl` (para equipos)

### Índices Utilizados
Las queries aprovechan los índices existentes:
- `idx_usage_cognito_user` - Búsquedas por usuario
- `idx_usage_request_timestamp` - Filtros por fecha
- `idx_usage_user_timestamp` - Agregaciones por usuario y fecha
- `idx_usage_model_timestamp` - Agregaciones por modelo y fecha

### Optimizaciones Aplicadas
1. **LEFT JOIN** para incluir usuarios sin grupo
2. **COALESCE** para valores por defecto
3. **Agregaciones eficientes** con GROUP BY
4. **Paginación** con LIMIT/OFFSET
5. **Ordenamiento** optimizado

## 📊 Características Implementadas

### 1. Cálculo de Cambios Porcentuales
```python
def _calculate_change(current, previous, inverse=False):
    """
    Calcula cambio % entre dos períodos
    - Maneja divisiones por cero
    - Soporta métricas inversas (menor es mejor)
    - Formato: "+15.2%" o "-5.1%"
    """
```

### 2. Comparación con Período Anterior
```python
# Automáticamente calcula período anterior
period_duration = end_date - start_date
prev_start = start_date - period_duration
prev_end = start_date
```

### 3. Manejo de Datos Faltantes
- Arrays pre-inicializados (24 horas)
- Valores por defecto (0, 'Sin Grupo')
- Validación de resultados vacíos

### 4. Logging Detallado
```python
logger.info(f"Obteniendo resumen de uso: {start_date} a {end_date}")
logger.info(f"Resumen calculado: {total_requests} requests, ${total_cost:.2f}")
logger.info(f"Hora pico: {peak_hour} con {requests} requests")
```

## 🔧 Próximos Pasos

### Fase 2: Frontend (Pendiente)
- [ ] Actualizar `proxy-usage.js`
- [ ] Reemplazar datos mock con llamadas API
- [ ] Implementar manejo de errores
- [ ] Agregar loading states
- [ ] Probar integración completa

### Fase 3: Testing (Pendiente)
- [ ] Tests unitarios del servicio
- [ ] Tests de integración
- [ ] Tests con datos reales
- [ ] Validación de rendimiento

### Fase 4: Deployment (Pendiente)
- [ ] Empaquetar Lambda
- [ ] Desplegar a AWS
- [ ] Verificar permisos RDS
- [ ] Probar en ambiente real

## 📝 Notas Técnicas

### Dependencias
No se requieren nuevas dependencias. El servicio utiliza:
- `datetime` (stdlib)
- `typing` (stdlib)
- `decimal` (stdlib)
- `logging` (stdlib)
- `database_service` (existente)

### Compatibilidad
- ✅ Python 3.12
- ✅ PostgreSQL 13+
- ✅ Compatible con estructura actual de BD
- ✅ No requiere migraciones

### Rendimiento
- Queries optimizadas con índices
- Agregaciones en BD (no en memoria)
- Paginación para grandes volúmenes
- Logging eficiente

## 🎯 Estado Actual

### ✅ Completado
- [x] Servicio `ProxyUsageService` completo
- [x] 7 métodos de agregación implementados
- [x] Lambda function actualizada
- [x] 7 handlers implementados
- [x] Routing configurado
- [x] Documentación del código
- [x] Logging implementado

### ⏳ Pendiente
- [ ] Actualización del frontend
- [ ] Tests unitarios
- [ ] Tests de integración
- [ ] Deployment a AWS
- [ ] Validación con datos reales

## 📚 Referencias

- [Propuesta de Integración](./PROXY_USAGE_API_INTEGRATION.md)
- [Documentación de Usage Tracking](./USAGE_TRACKING.md)
- [Esquema de Base de Datos](../database/schema/identity_manager_schema_v3_uuid.sql)
- [Servicio Implementado](../backend/lambdas/identity-mgmt-api/services/proxy_usage_service.py)
- [Lambda Function](../backend/lambdas/identity-mgmt-api/lambda_function.py)