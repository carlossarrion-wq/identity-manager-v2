# Propuesta de Integración: Dashboard de Uso del Proxy con Base de Datos

## 📋 Resumen Ejecutivo

Este documento describe la propuesta de solución para conectar el dashboard de uso del proxy Bedrock con los datos reales almacenados en la tabla `bedrock-proxy-usage-tracking-tbl`.

## 🎯 Objetivos

1. Crear endpoints API en el backend para consultar datos de uso
2. Implementar servicios de agregación y análisis de datos
3. Conectar el frontend con las APIs reales
4. Mantener el rendimiento con consultas optimizadas
5. Implementar caché para mejorar tiempos de respuesta

## 🏗️ Arquitectura de la Solución

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Dashboard                        │
│  (frontend/dashboard/js/proxy-usage.js)                     │
└────────────────┬────────────────────────────────────────────┘
                 │ HTTP/HTTPS
                 ↓
┌─────────────────────────────────────────────────────────────┐
│              API Gateway + Lambda                            │
│  (backend/lambdas/identity-mgmt-api/lambda_function.py)     │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────┐
│           Proxy Usage Service (NUEVO)                        │
│  (backend/lambdas/identity-mgmt-api/services/              │
│   proxy_usage_service.py)                                   │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────┐
│                  PostgreSQL RDS                              │
│  - bedrock-proxy-usage-tracking-tbl                         │
│  - Vistas agregadas (v_usage_*)                             │
│  - Funciones SQL (get_usage_stats, etc.)                    │
└─────────────────────────────────────────────────────────────┘
```

## 📊 Endpoints API Propuestos

### 1. **GET /proxy-usage/summary**
Obtiene resumen de métricas (KPIs) para el período especificado.

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
      "start": "2026-03-01T00:00:00Z",
      "end": "2026-03-07T23:59:59Z"
    }
  }
}
```

### 2. **GET /proxy-usage/by-hour**
Obtiene distribución de uso por hora del día.

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

### 3. **GET /proxy-usage/by-team**
Obtiene distribución de uso por equipo (grupo de Cognito).

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

### 4. **GET /proxy-usage/by-day**
Obtiene distribución de uso por día.

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

### 5. **GET /proxy-usage/response-status**
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

### 6. **GET /proxy-usage/trend**
Obtiene tendencia de uso por equipo a lo largo del tiempo.

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

### 7. **GET /proxy-usage/by-user**
Obtiene uso detallado por usuario con paginación.

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

## 🔧 Implementación Backend

### 1. Crear Servicio de Uso del Proxy

**Archivo:** `backend/lambdas/identity-mgmt-api/services/proxy_usage_service.py`

```python
"""
Proxy Usage Service
===================
Servicio para consultar y agregar datos de uso del proxy Bedrock.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal

logger = logging.getLogger()


class ProxyUsageService:
    """Servicio para gestionar datos de uso del proxy"""
    
    def __init__(self, db_service):
        """
        Inicializar servicio
        
        Args:
            db_service: Instancia de DatabaseService
        """
        self.db = db_service
    
    def get_summary(
        self,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtener resumen de métricas (KPIs)
        
        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            user_id: ID de usuario opcional para filtrar
            
        Returns:
            Diccionario con métricas agregadas
        """
        # Calcular período anterior para comparación
        period_duration = end_date - start_date
        prev_start = start_date - period_duration
        prev_end = start_date
        
        # Obtener estadísticas del período actual
        current_stats = self._get_period_stats(start_date, end_date, user_id)
        
        # Obtener estadísticas del período anterior
        previous_stats = self._get_period_stats(prev_start, prev_end, user_id)
        
        # Calcular cambios porcentuales
        return {
            'total_requests': current_stats['total_requests'],
            'requests_change': self._calculate_change(
                current_stats['total_requests'],
                previous_stats['total_requests']
            ),
            'total_tokens': current_stats['total_tokens'],
            'tokens_change': self._calculate_change(
                current_stats['total_tokens'],
                previous_stats['total_tokens']
            ),
            'total_cost': float(current_stats['total_cost']),
            'cost_change': self._calculate_change(
                current_stats['total_cost'],
                previous_stats['total_cost']
            ),
            'avg_response_time': current_stats['avg_response_time'],
            'response_time_change': self._calculate_change(
                current_stats['avg_response_time'],
                previous_stats['avg_response_time'],
                inverse=True  # Menor es mejor
            ),
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }
    
    def get_usage_by_hour(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Obtener distribución de uso por hora del día
        
        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            
        Returns:
            Diccionario con datos por hora
        """
        query = """
            SELECT 
                EXTRACT(HOUR FROM request_timestamp) as hour,
                COUNT(*) as requests
            FROM "bedrock-proxy-usage-tracking-tbl"
            WHERE request_timestamp >= %s
                AND request_timestamp <= %s
            GROUP BY EXTRACT(HOUR FROM request_timestamp)
            ORDER BY hour
        """
        
        results = self.db.execute_query(query, (start_date, end_date))
        
        # Crear array de 24 horas (0-23)
        hours_data = [0] * 24
        peak_hour = {'hour': '00:00', 'requests': 0}
        
        for row in results:
            hour = int(row['hour'])
            requests = row['requests']
            hours_data[hour] = requests
            
            if requests > peak_hour['requests']:
                peak_hour = {
                    'hour': f"{hour:02d}:00",
                    'requests': requests
                }
        
        return {
            'labels': [f"{h:02d}h" for h in range(24)],
            'values': hours_data,
            'peak_hour': peak_hour
        }
    
    def get_usage_by_team(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Obtener distribución de uso por equipo (grupo Cognito)
        
        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            
        Returns:
            Diccionario con datos por equipo
        """
        query = """
            SELECT 
                COALESCE(cg.group_name, 'Sin Grupo') as team,
                COUNT(*) as requests
            FROM "bedrock-proxy-usage-tracking-tbl" u
            LEFT JOIN "identity-manager-users-tbl" usr 
                ON u.cognito_user_id = usr.cognito_user_id
            LEFT JOIN "identity-manager-cognito-groups-tbl" cg 
                ON usr.cognito_group_id = cg.id
            WHERE u.request_timestamp >= %s
                AND u.request_timestamp <= %s
            GROUP BY cg.group_name
            ORDER BY requests DESC
        """
        
        results = self.db.execute_query(query, (start_date, end_date))
        
        labels = []
        values = []
        total_requests = sum(row['requests'] for row in results)
        top_team = None
        
        for row in results:
            labels.append(row['team'])
            values.append(row['requests'])
            
            if not top_team:
                top_team = {
                    'name': row['team'],
                    'requests': row['requests'],
                    'percentage': round((row['requests'] / total_requests * 100), 1) if total_requests > 0 else 0
                }
        
        return {
            'labels': labels,
            'values': values,
            'top_team': top_team or {'name': 'N/A', 'requests': 0, 'percentage': 0}
        }
    
    def get_usage_by_day(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Obtener distribución de uso por día
        
        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            
        Returns:
            Diccionario con datos por día
        """
        query = """
            SELECT 
                DATE(request_timestamp) as date,
                COUNT(*) as requests
            FROM "bedrock-proxy-usage-tracking-tbl"
            WHERE request_timestamp >= %s
                AND request_timestamp <= %s
            GROUP BY DATE(request_timestamp)
            ORDER BY date
        """
        
        results = self.db.execute_query(query, (start_date, end_date))
        
        labels = []
        values = []
        peak_day = {'date': '', 'requests': 0}
        
        for row in results:
            date_str = row['date'].strftime('%Y-%m-%d')
            labels.append(date_str)
            values.append(row['requests'])
            
            if row['requests'] > peak_day['requests']:
                peak_day = {
                    'date': date_str,
                    'requests': row['requests']
                }
        
        return {
            'labels': labels,
            'values': values,
            'peak_day': peak_day
        }
    
    def get_response_status(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Obtener distribución de estados de respuesta
        
        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            
        Returns:
            Diccionario con datos de estados
        """
        query = """
            SELECT 
                response_status,
                COUNT(*) as count
            FROM "bedrock-proxy-usage-tracking-tbl"
            WHERE request_timestamp >= %s
                AND request_timestamp <= %s
            GROUP BY response_status
            ORDER BY count DESC
        """
        
        results = self.db.execute_query(query, (start_date, end_date))
        
        # Mapeo de estados a etiquetas legibles
        status_labels = {
            'success': 'Success (200)',
            'rate_limited': 'Rate Limited (429)',
            'auth_error': 'Auth Error (401)',
            'server_error': 'Server Error (500)',
            'timeout': 'Timeout',
            'error': 'Other Errors'
        }
        
        labels = []
        values = []
        total_requests = sum(row['count'] for row in results)
        successful_requests = 0
        
        for row in results:
            status = row['response_status']
            count = row['count']
            
            label = status_labels.get(status, f"{status.title()}")
            labels.append(label)
            values.append(count)
            
            if status == 'success':
                successful_requests = count
        
        success_rate = {
            'percentage': round((successful_requests / total_requests * 100), 1) if total_requests > 0 else 0,
            'successful_requests': successful_requests,
            'total_requests': total_requests
        }
        
        return {
            'labels': labels,
            'values': values,
            'success_rate': success_rate
        }
    
    def get_usage_trend(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Obtener tendencia de uso por equipo a lo largo del tiempo
        
        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            
        Returns:
            Diccionario con series de tiempo por equipo
        """
        query = """
            SELECT 
                DATE(u.request_timestamp) as date,
                COALESCE(cg.group_name, 'Sin Grupo') as team,
                COUNT(*) as requests
            FROM "bedrock-proxy-usage-tracking-tbl" u
            LEFT JOIN "identity-manager-users-tbl" usr 
                ON u.cognito_user_id = usr.cognito_user_id
            LEFT JOIN "identity-manager-cognito-groups-tbl" cg 
                ON usr.cognito_group_id = cg.id
            WHERE u.request_timestamp >= %s
                AND u.request_timestamp <= %s
            GROUP BY DATE(u.request_timestamp), cg.group_name
            ORDER BY date, team
        """
        
        results = self.db.execute_query(query, (start_date, end_date))
        
        # Organizar datos por equipo
        teams_data = {}
        all_dates = set()
        
        for row in results:
            date_str = row['date'].strftime('%Y-%m-%d')
            team = row['team']
            requests = row['requests']
            
            all_dates.add(date_str)
            
            if team not in teams_data:
                teams_data[team] = {}
            
            teams_data[team][date_str] = requests
        
        # Crear labels (fechas ordenadas)
        labels = sorted(list(all_dates))
        
        # Crear datasets
        datasets = []
        for team, data in teams_data.items():
            dataset = {
                'label': team,
                'data': [data.get(date, 0) for date in labels]
            }
            datasets.append(dataset)
        
        return {
            'labels': labels,
            'datasets': datasets
        }
    
    def get_usage_by_user(
        self,
        start_date: datetime,
        end_date: datetime,
        page: int = 1,
        page_size: int = 10
    ) -> Dict[str, Any]:
        """
        Obtener uso detallado por usuario con paginación
        
        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            page: Número de página
            page_size: Tamaño de página
            
        Returns:
            Diccionario con datos de usuarios y paginación
        """
        offset = (page - 1) * page_size
        
        # Query para obtener datos
        query = """
            SELECT 
                u.cognito_email as email,
                usr.person_name as person,
                COALESCE(cg.group_name, 'Sin Grupo') as team,
                COUNT(*) as requests,
                SUM(u.tokens_input + u.tokens_output) as tokens,
                SUM(u.cost_usd) as cost
            FROM "bedrock-proxy-usage-tracking-tbl" u
            LEFT JOIN "identity-manager-users-tbl" usr 
                ON u.cognito_user_id = usr.cognito_user_id
            LEFT JOIN "identity-manager-cognito-groups-tbl" cg 
                ON usr.cognito_group_id = cg.id
            WHERE u.request_timestamp >= %s
                AND u.request_timestamp <= %s
            GROUP BY u.cognito_email, usr.person_name, cg.group_name
            ORDER BY cost DESC
            LIMIT %s OFFSET %s
        """
        
        # Query para contar total
        count_query = """
            SELECT COUNT(DISTINCT cognito_email) as total
            FROM "bedrock-proxy-usage-tracking-tbl"
            WHERE request_timestamp >= %s
                AND request_timestamp <= %s
        """
        
        results = self.db.execute_query(query, (start_date, end_date, page_size, offset))
        count_result = self.db.execute_query(count_query, (start_date, end_date))
        
        total_records = count_result[0]['total'] if count_result else 0
        total_pages = (total_records + page_size - 1) // page_size
        
        users = []
        for row in results:
            users.append({
                'email': row['email'],
                'person': row['person'] or row['email'],
                'team': row['team'],
                'requests': row['requests'],
                'tokens': int(row['tokens']) if row['tokens'] else 0,
                'cost': float(row['cost']) if row['cost'] else 0.0
            })
        
        return {
            'users': users,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_records': total_records,
                'total_pages': total_pages
            }
        }
    
    # Métodos auxiliares privados
    
    def _get_period_stats(
        self,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Obtener estadísticas para un período"""
        user_filter = "AND cognito_user_id = %s" if user_id else ""
        params = [start_date, end_date]
        if user_id:
            params.append(user_id)
        
        query = f"""
            SELECT 
                COUNT(*) as total_requests,
                SUM(tokens_input + tokens_output) as total_tokens,
                SUM(cost_usd) as total_cost,
                AVG(processing_time_ms) as avg_response_time
            FROM "bedrock-proxy-usage-tracking-tbl"
            WHERE request_timestamp >= %s
                AND request_timestamp <= %s
                {user_filter}
        """
        
        result = self.db.execute_query(query, tuple(params))
        
        if result:
            row = result[0]
            return {
                'total_requests': row['total_requests'] or 0,
                'total_tokens': int(row['total_tokens']) if row['total_tokens'] else 0,
                'total_cost': Decimal(str(row['total_cost'])) if row['total_cost'] else Decimal('0'),
                'avg_response_time': int(row['avg_response_time']) if row['avg_response_time'] else 0
            }
        
        return {
            'total_requests': 0,
            'total_tokens': 0,
            'total_cost': Decimal('0'),
            'avg_response_time': 0
        }
    
    def _calculate_change(
        self,
        current: Any,
        previous: Any,
        inverse: bool = False
    ) -> str:
        """
        Calcular cambio porcentual
        
        Args:
            current: Valor actual
            previous: Valor anterior
            inverse: Si True, invertir el signo (para métricas donde menor es mejor)
            
        Returns:
            String con el cambio porcentual (ej: "+15.2%")
        """
        if not previous or previous == 0:
            return "+100.0%" if current > 0 else "0.0%"
        
        # Convertir a float para el cálculo
        current_val = float(current)
        previous_val = float(previous)
        
        change = ((current_val - previous_val) / previous_val) * 100
        
        if inverse:
            change = -change
        
        sign = "+" if change >= 0 else ""
        return f"{sign}{change:.1f}%"
```

### 2. Actualizar Lambda Handler

**Archivo:** `backend/lambdas/identity-mgmt-api/lambda_function.py`

Agregar las siguientes operaciones al routing:

```python
# Importar el nuevo servicio
from services.proxy_usage_service import ProxyUsageService

# Inicializar servicio
proxy_usage_service = None

def initialize_services():
    """Inicializar servicios en el primer invocación (lazy loading)"""
    global cognito_service, database_service, jwt_service, email_service, permissions_service, proxy_usage_service
    
    # ... código existente ...
    
    if proxy_usage_service is None:
        proxy_usage_service = ProxyUsageService(database_service)

# Agregar al routing de operaciones
def route_operation(operation: str, body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
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
    
    # ... resto del código ...

# Handlers para las nuevas operaciones
def handle_get_proxy_usage_summary(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Obtener resumen de uso del proxy"""
    logger.info(f"[{request_id}] Obteniendo resumen de uso del proxy")
    
    filters = body.get('filters', {})
    start_date = datetime.fromisoformat(filters['start_date'].replace('Z', '+00:00'))
    end_date = datetime.fromisoformat(filters['end_date'].replace('Z', '+00:00'))
    user_id = filters.get('user_id')
    
    result = proxy_usage_service.get_summary(start_date, end_date, user_id)
    
    return {'success': True, 'data': result}

def handle_get_proxy_usage_by_hour(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Obtener uso del proxy por hora"""
    logger.info(f"[{request_id}] Obteniendo uso por hora")
    
    filters = body.get('filters', {})
    start_date = datetime.fromisoformat(filters['start_date'].replace('Z', '+00:00'))
    end_date = datetime.fromisoformat(filters['end_date'].replace('Z', '+00:00'))
    
    result = proxy_usage_service.get_usage_by_hour(start_date, end_date)
    
    return {'success': True, 'data': result}

def handle_get_proxy_usage_by_team(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Obtener uso del proxy por equipo"""
    logger.info(f"[{request_id}] Obteniendo uso por equipo")
    
    filters = body.get('filters', {})
    start_date = datetime.fromisoformat(filters['start_date'].replace('Z', '+00:00'))
    end_date = datetime.fromisoformat(filters['end_date'].replace('Z', '+00:00'))
    
    result = proxy_usage_service.get_usage_by_team(start_date, end_date)
    
    return {'success': True, 'data': result}

def handle_get_proxy_usage_by_day(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Obtener uso del proxy por día"""
    logger.info(f"[{request_id}] Obteniendo uso por día")
    
    filters = body.get('filters', {})
    start_date = datetime.fromisoformat(filters['start_date'].replace('Z', '+00:00'))
    end_date = datetime.fromisoformat(filters['end_date'].replace('Z', '+00:00'))
    
    result = proxy_usage_service.get_usage_by_day(start_date, end_date)
    
    return {'success': True, 'data': result}

def handle_get_proxy_usage_response_status(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Obtener distribución de estados de respuesta"""
    logger.info(f"[{request_id}] Obteniendo estados de respuesta")
    
    filters = body.get('filters', {})
    start_date = datetime.fromisoformat(filters['start_date'].replace('Z', '+00:00'))
    end_date = datetime.fromisoformat(filters['end_date'].replace('Z', '+00:00'))
    
    result = proxy_usage_service.get_response_status(start_date, end_date)
    
    return {'success': True, 'data': result}

def handle_get_proxy_usage_trend(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Obtener tendencia de uso por equipo"""
    logger.info(f"[{request_id}] Obteniendo tendencia de uso")
    
    filters = body.get('filters', {})
    start_date = datetime.fromisoformat(filters['start_date'].replace('Z', '+00:00'))
    end_date = datetime.fromisoformat(filters['end_date'].replace('Z', '+00:00'))
    
    result = proxy_usage_service.get_usage_trend(start_date, end_date)
    
    return {'success': True, 'data': result}

def handle_get_proxy_usage_by_user(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Obtener uso por usuario con paginación"""
    logger.info(f"[{request_id}] Obteniendo uso por usuario")
    
    filters = body.get('filters', {})
    pagination = body.get('pagination', {})
    
    start_date = datetime.fromisoformat(filters['start_date'].replace('Z', '+00:00'))
    end_date = datetime.fromisoformat(filters['end_date'].replace('Z', '+00:00'))
    page = pagination.get('page', 1)
    page_size = pagination.get('page_size', 10)
    
    result = proxy_usage_service.get_usage_by_user(start_date, end_date, page, page_size)
    
    return {'success': True, 'data': result}
```

## 🎨 Actualización Frontend

### Modificar `frontend/dashboard/js/proxy-usage.js`

Reemplazar la función `loadUsageData()` para usar las APIs reales:

```javascript
/**
 * Load usage data from API
 */
async function loadUsageData() {
    try {
        console.log('Loading usage data...', dateRange);
        
        const filters = {
            start_date: dateRange.start.toISOString(),
            end_date: dateRange.end.toISOString()
        };
        
        // Cargar todas las métricas en paralelo
        const [
            summaryData,
            byHourData,
            byTeamData,
            byDayData,
            responseStatusData,
            trendData,
            usersData
        ] = await Promise.all([
            apiCall('', 'POST', { operation: 'get_proxy_usage_summary', filters }),
            apiCall('', 'POST', { operation: 'get_proxy_usage_by_hour', filters }),
            apiCall('', 'POST', { operation: 'get_proxy_usage_by_team', filters }),
            apiCall('', 'POST', { operation: 'get_proxy_usage_by_day', filters }),
            apiCall('', 'POST', { operation: 'get_proxy_usage_response_status', filters }),
            apiCall('', 'POST', { operation: 'get_proxy_usage_trend', filters }),
            apiCall('', 'POST', { 
                operation: 'get_proxy_usage_by_user', 
                filters,
                pagination: { page: currentPage, page_size: pageSize }
            })
        ]);
        
        // Actualizar KPIs
        if (summaryData.success) {
            updateKPIs(summaryData.data);
        }
        
        // Actualizar gráficas
        const chartsData = {
            byHour: byHourData.success ? byHourData.data : null,
            byTeam: byTeamData.success ? byTeamData.data : null,
            byDay: byDayData.success ? byDayData.data : null,
            responseStatus: responseStatusData.success ? responseStatusData.data : null,
            trend: trendData.success ? trendData.data : null
        };
        
        updateCharts(chartsData);
        
        // Actualizar tabla
        if (usersData.success) {
            usageData = usersData.data.users;
            totalUsers = usersData.data.pagination.total_records;
            updateTable();
        }
        
    } catch (error) {
        console.error('Error loading usage data:', error);
        showError('Failed to load usage data: ' + error.message);
    }
}
```

Actualizar la función `updateCharts()`:

```javascript
/**
 * Update all charts
 */
function updateCharts(chartsData) {
    // Destroy existing charts
    Object.values(charts).forEach(chart => chart && chart.destroy());
    charts = {};
    
    // Verificar que tenemos datos
    if (!chartsData.byHour || !chartsData.byTeam || !chartsData.byDay || 
        !chartsData.responseStatus || !chartsData.trend) {
        console.error('Missing chart data');
        return;
    }
    
    // Create charts
    charts.byHour = createBarChart('chart-by-hour', chartsData.byHour.labels, chartsData.byHour.values);
    charts.byTeam = createHorizontalBarChart('chart-by-team', chartsData.byTeam.labels, chartsData.byTeam.values);
    charts.byDay = createBarChart('chart-by-day', chartsData.byDay.labels, chartsData.byDay.values, true);
    charts.responseStatus = createPieChart('chart-response-status', chartsData.responseStatus.labels, chartsData.responseStatus.values);
    charts.trend = createLineChart('chart-trend', chartsData.trend.labels, chartsData.trend.datasets);
    
    // Update footers
    document.getElementById('peak-hour').textContent = 
        `${chartsData.byHour.peak_hour.hour} (${chartsData.byHour.peak_hour.requests.toLocaleString()} requests)`;
    document.getElementById('top-team').textContent = 
        `${chartsData.byTeam.top_team.name} (${chartsData.byTeam.top_team.percentage}%)`;
    document.getElementById('peak-day').textContent = 
        `${chartsData.byDay.peak_day.date} (${chartsData.byDay.peak_day.requests.toLocaleString()} requests)`;
    document.getElementById('success-rate').textContent = 
        `${chartsData.responseStatus.success_rate.percentage}% (${chartsData.responseStatus.success_rate.successful_requests.toLocaleString()} successful requests)`;
}
```

## 📋 Plan de Implementación

### Fase 1: Backend (Estimado: 2-3 días)

1. **Día 1: Crear servicio y queries**
   - [ ] Crear `proxy_usage_service.py`
   - [ ] Implementar todos los métodos del servicio
   - [ ] Probar queries SQL individualmente
   - [ ] Optimizar índices si es necesario

2. **Día 2: Integrar con Lambda**
   - [ ] Actualizar `lambda_function.py`
   - [ ] Agregar handlers para cada operación
   - [ ] Implementar validación de parámetros
   - [ ] Agregar logging apropiado

3. **Día 3: Testing y optimización**
   - [ ] Crear tests unitarios
   - [ ] Probar con datos reales
   - [ ] Optimizar rendimiento de queries
   - [ ] Documentar endpoints

### Fase 2: Frontend (Estimado: 1-2 días)

1. **Día 1: Conectar con APIs**
   - [ ] Actualizar `proxy-usage.js`
   - [ ] Reemplazar datos mock con llamadas API
   - [ ] Implementar manejo de errores
   - [ ] Agregar indicadores de carga

2. **Día 2: Testing y refinamiento**
   - [ ] Probar todas las funcionalidades
   - [ ] Verificar rendimiento
   - [ ] Ajustar UI según feedback
   - [ ] Documentar uso

### Fase 3: Deployment (Estimado: 1 día)

1. **Deployment**
   - [ ] Desplegar Lambda actualizada
   - [ ] Verificar permisos de BD
   - [ ] Probar en ambiente de desarrollo
   - [ ] Desplegar frontend
   - [ ] Verificar en producción

## ⚡ Optimizaciones Recomendadas

### 1. Caché de Resultados

Implementar caché para consultas frecuentes:

```python
from functools import lru_cache
from datetime import datetime, timedelta

class ProxyUsageService:
    def __init__(self, db_service):
        self.db = db_service
        self.cache_ttl = 300  # 5 minutos
        self.cache = {}
    
    def _get_cache_key(self, operation, start_date, end_date):
        return f"{operation}:{start_date.isoformat()}:{end_date.isoformat()}"
    
    def _get_cached_result(self, cache_key):
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if (datetime.now() - timestamp).seconds < self.cache_ttl:
                return cached_data
        return None
    
    def _set_cache(self, cache_key, data):
        self.cache[cache_key] = (data, datetime.now())
```

### 2. Vistas Materializadas

Crear vistas materializadas para agregaciones comunes:

```sql
-- Vista materializada para uso diario
CREATE MATERIALIZED VIEW mv_daily_usage AS
SELECT 
    DATE(request_timestamp) as usage_date,
    cognito_user_id,
    cognito_email,
    COUNT(*) as total_requests,
    SUM(tokens_input + tokens_output) as total_tokens,
    SUM(cost_usd) as total_cost,
    AVG(processing_time_ms) as avg_response_time
FROM "bedrock-proxy-usage-tracking-tbl"
GROUP BY DATE(request_timestamp), cognito_user_id, cognito_email;

-- Índice en la vista
CREATE INDEX idx_mv_daily_usage_date ON mv_daily_usage(usage_date DESC);

-- Refrescar periódicamente (cron job)
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_usage;
```

### 3. Paginación Eficiente

Usar cursor-based pagination para grandes volúmenes:

```python
def get_usage_by_user_cursor(
    self,
    start_date: datetime,
    end_date: datetime,
    cursor: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """Paginación basada en cursor para mejor rendimiento"""
    # Implementación con cursor
    pass
```

### 4. Agregación Asíncrona

Para períodos largos, usar procesamiento asíncrono:

```python
import asyncio

async def get_all_metrics_async(self, start_date, end_date):
    """Obtener todas las métricas en paralelo"""
    tasks = [
        self.get_summary_async(start_date, end_date),
        self.get_usage_by_hour_async(start_date, end_date),
        # ... más tareas
    ]
    results = await asyncio.gather(*tasks)
    return results
```

## 🔒 Consideraciones de Seguridad

1. **Autenticación**: Verificar token JWT en cada request
2. **Autorización**: Validar permisos del usuario
3. **Rate Limiting**: Limitar requests por usuario
4. **SQL Injection**: Usar parámetros preparados (ya implementado)
5. **Datos Sensibles**: No exponer información de otros usuarios

## 📊 Monitoreo y Alertas

### Métricas a Monitorear

1. **Rendimiento de Queries**
   - Tiempo de ejecución
   - Queries lentas (> 1s)
   - Uso de índices

2. **Uso de API**
   - Requests por minuto
   - Errores 4xx/5xx
   - Latencia promedio

3. **Tamaño de Datos**
   - Crecimiento de tabla
   - Uso de disco
   - Necesidad de archivado

### CloudWatch Alarms

```python
# Ejemplo de métricas custom
cloudwatch.put_metric_data(
    Namespace='ProxyUsage',
    MetricData=[
        {
            'MetricName': 'QueryExecutionTime',
            'Value': execution_time_ms,
            'Unit': 'Milliseconds'
        }
    ]
)
```

## 📝 Checklist de Implementación

### Backend
- [ ] Crear `proxy_usage_service.py`
- [ ] Implementar todos los métodos
- [ ] Actualizar `lambda_function.py`
- [ ] Agregar handlers
- [ ] Crear tests unitarios
- [ ] Optimizar queries
- [ ] Documentar código

### Frontend
- [ ] Actualizar `proxy-usage.js`
- [ ] Reemplazar datos mock
- [ ] Implementar manejo de errores
- [ ] Agregar loading states
- [ ] Probar todas las funcionalidades
- [ ] Optimizar rendimiento

### Database
- [ ] Verificar índices existentes
- [ ] Crear vistas materializadas (opcional)
- [ ] Configurar refresh automático
- [ ] Implementar política de retención

### Deployment
- [ ] Actualizar requirements.txt
- [ ] Desplegar Lambda
- [ ] Verificar permisos RDS
- [ ] Desplegar frontend
- [ ] Configurar CloudWatch
- [ ] Documentar proceso

### Testing
- [ ] Tests unitarios backend
- [ ] Tests de integración
- [ ] Tests de rendimiento
- [ ] Tests de UI
- [ ] Tests de carga

## 🎯 Próximos Pasos

1. **Revisar y aprobar** esta propuesta
2. **Estimar esfuerzo** detallado por tarea
3. **Asignar recursos** al proyecto
4. **Comenzar implementación** por fases
5. **Iterar y mejorar** basado en feedback

## 📚 Referencias

- [Documentación de Usage Tracking](./USAGE_TRACKING.md)
- [Esquema de Base de Datos](../database/schema/identity_manager_schema_v3_uuid.sql)
- [API Lambda Actual](../backend/lambdas/identity-mgmt-api/lambda_function.py)
- [Dashboard Frontend](../frontend/dashboard/js/proxy-usage.js)
