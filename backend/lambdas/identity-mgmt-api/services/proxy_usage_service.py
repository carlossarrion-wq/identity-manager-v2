"""
Proxy Usage Service
===================
Servicio para consultar y agregar datos de uso del proxy Bedrock.

Este servicio proporciona métodos para obtener estadísticas y métricas
de uso del proxy Bedrock desde la tabla bedrock-proxy-usage-tracking-tbl.
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
        logger.info("ProxyUsageService inicializado")
    
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
        logger.info(f"Obteniendo resumen de uso: {start_date} a {end_date}")
        
        # Calcular período anterior para comparación
        period_duration = end_date - start_date
        prev_start = start_date - period_duration
        prev_end = start_date
        
        # Obtener estadísticas del período actual
        current_stats = self._get_period_stats(start_date, end_date, user_id)
        
        # Obtener estadísticas del período anterior
        previous_stats = self._get_period_stats(prev_start, prev_end, user_id)
        
        # Calcular cambios porcentuales
        result = {
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
        
        logger.info(f"Resumen calculado: {result['total_requests']} requests, ${result['total_cost']:.2f}")
        return result
    
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
        logger.info(f"Obteniendo uso por hora: {start_date} a {end_date}")
        
        query = """
            SELECT 
                EXTRACT(HOUR FROM request_timestamp) as hour,
                COUNT(*) as requests
            FROM "bedrock-proxy-usage-tracking-tbl"
            WHERE request_timestamp >= %s
                AND request_timestamp <= %s
                AND response_status = 'success'
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
        
        logger.info(f"Hora pico: {peak_hour['hour']} con {peak_hour['requests']} requests")
        
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
        Obtener distribución de uso por equipo (agrupado por team)
        
        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            
        Returns:
            Diccionario con datos por equipo
        """
        logger.info(f"Obteniendo uso por equipo: {start_date} a {end_date}")
        
        query = """
            SELECT 
                COALESCE(team, 'N/A') as team,
                COUNT(*) as requests
            FROM "bedrock-proxy-usage-tracking-tbl"
            WHERE request_timestamp >= %s
                AND request_timestamp <= %s
                AND response_status = 'success'
            GROUP BY team
            ORDER BY requests DESC
            LIMIT 10
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
        
        logger.info(f"Equipo top: {top_team['name'] if top_team else 'N/A'}")
        
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
        logger.info(f"Obteniendo uso por día: {start_date} a {end_date}")
        
        query = """
            SELECT 
                DATE(request_timestamp) as date,
                COUNT(*) as requests
            FROM "bedrock-proxy-usage-tracking-tbl"
            WHERE request_timestamp >= %s
                AND request_timestamp <= %s
                AND response_status = 'success'
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
        
        logger.info(f"Día pico: {peak_day['date']} con {peak_day['requests']} requests")
        
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
        logger.info(f"Obteniendo estados de respuesta: {start_date} a {end_date}")
        
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
        
        logger.info(f"Tasa de éxito: {success_rate['percentage']}%")
        
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
        Obtener tendencia de uso por usuario a lo largo del tiempo
        
        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            
        Returns:
            Diccionario con series de tiempo por usuario (top 5)
        """
        logger.info(f"Obteniendo tendencia de uso: {start_date} a {end_date}")
        
        query = """
            SELECT 
                DATE(request_timestamp) as date,
                cognito_email as team,
                COUNT(*) as requests
            FROM "bedrock-proxy-usage-tracking-tbl"
            WHERE request_timestamp >= %s
                AND request_timestamp <= %s
                AND response_status = 'success'
            GROUP BY DATE(request_timestamp), cognito_email
            ORDER BY date, requests DESC
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
        
        logger.info(f"Tendencia calculada para {len(datasets)} equipos")
        
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
        logger.info(f"Obteniendo uso por usuario: página {page}, tamaño {page_size}")
        
        offset = (page - 1) * page_size
        
        # Query para obtener datos - solo peticiones exitosas, incluyendo team y person
        query = """
            SELECT 
                cognito_email as email,
                cognito_user_id,
                MAX(person) as person,
                MAX(team) as team,
                COUNT(*) as requests,
                SUM(tokens_input + tokens_output) as tokens,
                SUM(cost_usd) as cost
            FROM "bedrock-proxy-usage-tracking-tbl"
            WHERE request_timestamp >= %s
                AND request_timestamp <= %s
                AND response_status = 'success'
            GROUP BY cognito_email, cognito_user_id
            ORDER BY cost DESC
            LIMIT %s OFFSET %s
        """
        
        # Query para contar total - solo peticiones exitosas
        count_query = """
            SELECT COUNT(DISTINCT cognito_email) as total
            FROM "bedrock-proxy-usage-tracking-tbl"
            WHERE request_timestamp >= %s
                AND request_timestamp <= %s
                AND response_status = 'success'
        """
        
        results = self.db.execute_query(query, (start_date, end_date, page_size, offset))
        count_result = self.db.execute_query(count_query, (start_date, end_date))
        
        total_records = count_result[0]['total'] if count_result else 0
        total_pages = (total_records + page_size - 1) // page_size
        
        users = []
        for row in results:
            users.append({
                'email': row['email'],
                'person': row['person'] if row['person'] else row['email'],  # Usar person de BD, fallback a email
                'team': row['team'] if row['team'] else 'N/A',  # Team de la BD
                'requests': row['requests'],
                'tokens': int(row['tokens']) if row['tokens'] else 0,
                'cost': float(row['cost']) if row['cost'] else 0.0
            })
        
        logger.info(f"Retornando {len(users)} usuarios de {total_records} totales")
        
        return {
            'users': users,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_records': total_records,
                'total_pages': total_pages
            }
        }
    
    # ========================================================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ========================================================================
    
    def _get_period_stats(
        self,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtener estadísticas para un período
        
        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            user_id: ID de usuario opcional
            
        Returns:
            Diccionario con estadísticas del período
        """
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
                AND response_status = 'success'
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