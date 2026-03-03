"""
Test Script for Proxy Usage Service (Standalone)
=================================================
Script standalone para probar la lógica del servicio sin dependencias.

Uso:
    python test_proxy_usage_standalone.py
"""

import json
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional


# Copiar la clase ProxyUsageService aquí para evitar imports
class ProxyUsageService:
    """Servicio para gestionar datos de uso del proxy"""
    
    def __init__(self, db_service):
        self.db = db_service
    
    def get_summary(self, start_date: datetime, end_date: datetime, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Obtener resumen de métricas (KPIs)"""
        period_duration = end_date - start_date
        prev_start = start_date - period_duration
        prev_end = start_date
        
        current_stats = self._get_period_stats(start_date, end_date, user_id)
        previous_stats = self._get_period_stats(prev_start, prev_end, user_id)
        
        return {
            'total_requests': current_stats['total_requests'],
            'requests_change': self._calculate_change(current_stats['total_requests'], previous_stats['total_requests']),
            'total_tokens': current_stats['total_tokens'],
            'tokens_change': self._calculate_change(current_stats['total_tokens'], previous_stats['total_tokens']),
            'total_cost': float(current_stats['total_cost']),
            'cost_change': self._calculate_change(current_stats['total_cost'], previous_stats['total_cost']),
            'avg_response_time': current_stats['avg_response_time'],
            'response_time_change': self._calculate_change(current_stats['avg_response_time'], previous_stats['avg_response_time'], inverse=True),
            'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()}
        }
    
    def get_usage_by_hour(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Obtener distribución de uso por hora del día"""
        query = """SELECT EXTRACT(HOUR FROM request_timestamp) as hour, COUNT(*) as requests"""
        results = self.db.execute_query(query, (start_date, end_date))
        
        hours_data = [0] * 24
        peak_hour = {'hour': '00:00', 'requests': 0}
        
        for row in results:
            hour = int(row['hour'])
            requests = row['requests']
            hours_data[hour] = requests
            if requests > peak_hour['requests']:
                peak_hour = {'hour': f"{hour:02d}:00", 'requests': requests}
        
        return {'labels': [f"{h:02d}h" for h in range(24)], 'values': hours_data, 'peak_hour': peak_hour}
    
    def get_usage_by_team(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Obtener distribución de uso por equipo"""
        query = """SELECT COALESCE(cg.group_name, 'Sin Grupo') as team, COUNT(*) as requests"""
        results = self.db.execute_query(query, (start_date, end_date))
        
        labels, values = [], []
        total_requests = sum(row['requests'] for row in results)
        top_team = None
        
        for row in results:
            labels.append(row['team'])
            values.append(row['requests'])
            if not top_team:
                top_team = {'name': row['team'], 'requests': row['requests'], 
                           'percentage': round((row['requests'] / total_requests * 100), 1) if total_requests > 0 else 0}
        
        return {'labels': labels, 'values': values, 'top_team': top_team or {'name': 'N/A', 'requests': 0, 'percentage': 0}}
    
    def get_usage_by_day(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Obtener distribución de uso por día"""
        query = """SELECT DATE(request_timestamp) as date, COUNT(*) as requests"""
        results = self.db.execute_query(query, (start_date, end_date))
        
        labels, values = [], []
        peak_day = {'date': '', 'requests': 0}
        
        for row in results:
            date_str = row['date'].strftime('%Y-%m-%d')
            labels.append(date_str)
            values.append(row['requests'])
            if row['requests'] > peak_day['requests']:
                peak_day = {'date': date_str, 'requests': row['requests']}
        
        return {'labels': labels, 'values': values, 'peak_day': peak_day}
    
    def get_response_status(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Obtener distribución de estados de respuesta"""
        query = """SELECT response_status, COUNT(*) as count"""
        results = self.db.execute_query(query, (start_date, end_date))
        
        status_labels = {'success': 'Success (200)', 'rate_limited': 'Rate Limited (429)', 
                        'auth_error': 'Auth Error (401)', 'server_error': 'Server Error (500)',
                        'timeout': 'Timeout', 'error': 'Other Errors'}
        
        labels, values = [], []
        total_requests = sum(row['count'] for row in results)
        successful_requests = 0
        
        for row in results:
            status, count = row['response_status'], row['count']
            labels.append(status_labels.get(status, f"{status.title()}"))
            values.append(count)
            if status == 'success':
                successful_requests = count
        
        success_rate = {'percentage': round((successful_requests / total_requests * 100), 1) if total_requests > 0 else 0,
                       'successful_requests': successful_requests, 'total_requests': total_requests}
        
        return {'labels': labels, 'values': values, 'success_rate': success_rate}
    
    def get_usage_trend(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Obtener tendencia de uso por equipo"""
        query = """SELECT DATE(u.request_timestamp) as date, COALESCE(cg.group_name, 'Sin Grupo') as team, COUNT(*) as requests"""
        results = self.db.execute_query(query, (start_date, end_date))
        
        teams_data, all_dates = {}, set()
        
        for row in results:
            date_str = row['date'].strftime('%Y-%m-%d')
            team, requests = row['team'], row['requests']
            all_dates.add(date_str)
            if team not in teams_data:
                teams_data[team] = {}
            teams_data[team][date_str] = requests
        
        labels = sorted(list(all_dates))
        datasets = [{'label': team, 'data': [data.get(date, 0) for date in labels]} for team, data in teams_data.items()]
        
        return {'labels': labels, 'datasets': datasets}
    
    def get_usage_by_user(self, start_date: datetime, end_date: datetime, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """Obtener uso detallado por usuario con paginación"""
        offset = (page - 1) * page_size
        query = """SELECT u.cognito_email as email"""
        results = self.db.execute_query(query, (start_date, end_date, page_size, offset))
        count_result = self.db.execute_query("COUNT", (start_date, end_date))
        
        total_records = count_result[0]['total'] if count_result else 0
        total_pages = (total_records + page_size - 1) // page_size
        
        users = [{'email': row['email'], 'person': row.get('person') or row['email'], 'team': row.get('team', 'N/A'),
                 'requests': row.get('requests', 0), 'tokens': int(row.get('tokens', 0)) if row.get('tokens') else 0,
                 'cost': float(row.get('cost', 0)) if row.get('cost') else 0.0} for row in results]
        
        return {'users': users, 'pagination': {'page': page, 'page_size': page_size, 'total_records': total_records, 'total_pages': total_pages}}
    
    def _get_period_stats(self, start_date: datetime, end_date: datetime, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Obtener estadísticas para un período"""
        query = """SELECT COUNT(*) as total_requests"""
        result = self.db.execute_query(query, (start_date, end_date))
        
        if result:
            row = result[0]
            return {'total_requests': row.get('total_requests', 0), 'total_tokens': int(row.get('total_tokens', 0)) if row.get('total_tokens') else 0,
                   'total_cost': Decimal(str(row.get('total_cost', 0))) if row.get('total_cost') else Decimal('0'),
                   'avg_response_time': int(row.get('avg_response_time', 0)) if row.get('avg_response_time') else 0}
        return {'total_requests': 0, 'total_tokens': 0, 'total_cost': Decimal('0'), 'avg_response_time': 0}
    
    def _calculate_change(self, current: Any, previous: Any, inverse: bool = False) -> str:
        """Calcular cambio porcentual"""
        if not previous or previous == 0:
            return "+100.0%" if current > 0 else "0.0%"
        change = ((float(current) - float(previous)) / float(previous)) * 100
        if inverse:
            change = -change
        return f"{'+' if change >= 0 else ''}{change:.1f}%"


class MockDatabaseService:
    """Mock del servicio de base de datos"""
    
    def execute_query(self, query, params):
        """Simular ejecución de query"""
        if "EXTRACT(HOUR FROM request_timestamp)" in query:
            return [{'hour': 9, 'requests': 150}, {'hour': 10, 'requests': 200}, {'hour': 11, 'requests': 180}, 
                   {'hour': 14, 'requests': 250}, {'hour': 15, 'requests': 220}]
        elif "COALESCE(cg.group_name" in query and "COUNT(*) as requests" in query and "DATE(u.request_timestamp)" not in query:
            return [{'team': 'Team Alpha', 'requests': 5678}, {'team': 'Team Beta', 'requests': 3456}, 
                   {'team': 'Team Gamma', 'requests': 2345}, {'team': 'Sin Grupo', 'requests': 979}]
        elif "DATE(request_timestamp) as date" in query and "DATE(u.request_timestamp)" not in query:
            start_date = params[0]
            return [{'date': (start_date + timedelta(days=i)).date(), 'requests': 1500 + (i * 100) + (200 if i == 3 else 0)} for i in range(7)]
        elif "response_status" in query and "COUNT(*) as count" in query:
            return [{'response_status': 'success', 'count': 12271}, {'response_status': 'rate_limited', 'count': 98},
                   {'response_status': 'auth_error', 'count': 45}, {'response_status': 'server_error', 'count': 23},
                   {'response_status': 'timeout', 'count': 15}, {'response_status': 'error', 'count': 6}]
        elif "DATE(u.request_timestamp)" in query and "cg.group_name" in query:
            start_date, results, teams = params[0], [], ['Team Alpha', 'Team Beta', 'Team Gamma']
            for i in range(7):
                for j, team in enumerate(teams):
                    results.append({'date': (start_date + timedelta(days=i)).date(), 'team': team, 'requests': 800 + (j * 200) + (i * 50)})
            return results
        elif "u.cognito_email as email" in query and "LIMIT" in query:
            return [{'email': 'john.doe@example.com', 'person': 'John Doe', 'team': 'Team Alpha', 'requests': 1234, 'tokens': 245600, 'cost': Decimal('12.28')},
                   {'email': 'jane.smith@example.com', 'person': 'Jane Smith', 'team': 'Team Beta', 'requests': 987, 'tokens': 198400, 'cost': Decimal('9.92')},
                   {'email': 'bob.wilson@example.com', 'person': 'Bob Wilson', 'team': 'Team Alpha', 'requests': 756, 'tokens': 151200, 'cost': Decimal('7.56')}]
        elif "COUNT" in query:
            return [{'total': 45}]
        elif "COUNT(*) as total_requests" in query:
            return [{'total_requests': 12458, 'total_tokens': 2400000, 'total_cost': Decimal('124.50'), 'avg_response_time': 1234}]
        return []


def print_section(title):
    print("\n" + "=" * 80 + f"\n  {title}\n" + "=" * 80)


def print_result(test_name, result, success=True):
    print(f"\n{'✅ PASS' if success else '❌ FAIL'} - {test_name}\n" + "-" * 80)
    print(json.dumps(result, indent=2, default=str))


def main():
    print_section("PROXY USAGE SERVICE - TEST SUITE (STANDALONE)")
    
    mock_db = MockDatabaseService()
    service = ProxyUsageService(mock_db)
    
    end_date, start_date = datetime.now(), datetime.now() - timedelta(days=7)
    print(f"\n📅 Período: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
    
    results = []
    
    for i, (name, method, args) in enumerate([
        ("get_summary()", service.get_summary, (start_date, end_date)),
        ("get_usage_by_hour()", service.get_usage_by_hour, (start_date, end_date)),
        ("get_usage_by_team()", service.get_usage_by_team, (start_date, end_date)),
        ("get_usage_by_day()", service.get_usage_by_day, (start_date, end_date)),
        ("get_response_status()", service.get_response_status, (start_date, end_date)),
        ("get_usage_trend()", service.get_usage_trend, (start_date, end_date)),
        ("get_usage_by_user()", service.get_usage_by_user, (start_date, end_date, 1, 5))
    ], 1):
        print_section(f"TEST {i}: {name}")
        try:
            result = method(*args)
            print_result(name, result, True)
            results.append(True)
        except Exception as e:
            print_result(name, {"error": str(e)}, False)
            results.append(False)
    
    print_section("RESUMEN")
    passed = sum(results)
    print(f"\n✅ Pruebas exitosas: {passed}/{len(results)} ({passed/len(results)*100:.1f}%)")
    print("\n🎉 ¡Todas las pruebas pasaron!" if passed == len(results) else f"\n⚠️  {len(results)-passed} prueba(s) fallaron")
    print("\n📝 Nota: Pruebas con datos mock. Para datos reales, ejecutar desde entorno con acceso a RDS.")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)