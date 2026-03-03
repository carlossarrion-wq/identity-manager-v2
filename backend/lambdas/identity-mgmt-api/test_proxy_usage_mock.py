"""
Test Script for Proxy Usage Service (Mock Version)
===================================================
Script para probar las funciones del servicio sin conexión a BD.
Usa datos mock para validar la lógica.

Uso:
    python test_proxy_usage_mock.py
"""

import json
import sys
from datetime import datetime, timedelta
from decimal import Decimal


class MockDatabaseService:
    """Mock del servicio de base de datos"""
    
    def execute_query(self, query, params):
        """Simular ejecución de query"""
        
        # Detectar tipo de query y retornar datos mock apropiados
        if "EXTRACT(HOUR FROM request_timestamp)" in query:
            # Query de uso por hora
            return [
                {'hour': 9, 'requests': 150},
                {'hour': 10, 'requests': 200},
                {'hour': 11, 'requests': 180},
                {'hour': 14, 'requests': 250},  # Hora pico
                {'hour': 15, 'requests': 220},
            ]
        
        elif "COALESCE(cg.group_name" in query and "COUNT(*) as requests" in query and "DATE(u.request_timestamp)" not in query:
            # Query de uso por equipo
            return [
                {'team': 'Team Alpha', 'requests': 5678},
                {'team': 'Team Beta', 'requests': 3456},
                {'team': 'Team Gamma', 'requests': 2345},
                {'team': 'Sin Grupo', 'requests': 979},
            ]
        
        elif "DATE(request_timestamp) as date" in query and "DATE(u.request_timestamp)" not in query:
            # Query de uso por día
            start_date = params[0]
            days = []
            for i in range(7):
                date = start_date + timedelta(days=i)
                days.append({
                    'date': date.date(),
                    'requests': 1500 + (i * 100) + (200 if i == 3 else 0)  # Día 3 es pico
                })
            return days
        
        elif "response_status" in query and "COUNT(*) as count" in query:
            # Query de estados de respuesta
            return [
                {'response_status': 'success', 'count': 12271},
                {'response_status': 'rate_limited', 'count': 98},
                {'response_status': 'auth_error', 'count': 45},
                {'response_status': 'server_error', 'count': 23},
                {'response_status': 'timeout', 'count': 15},
                {'response_status': 'error', 'count': 6},
            ]
        
        elif "DATE(u.request_timestamp)" in query and "cg.group_name" in query:
            # Query de tendencia por equipo
            start_date = params[0]
            results = []
            teams = ['Team Alpha', 'Team Beta', 'Team Gamma']
            for i in range(7):
                date = start_date + timedelta(days=i)
                for j, team in enumerate(teams):
                    results.append({
                        'date': date.date(),
                        'team': team,
                        'requests': 800 + (j * 200) + (i * 50)
                    })
            return results
        
        elif "u.cognito_email as email" in query and "LIMIT" in query:
            # Query de uso por usuario
            return [
                {
                    'email': 'john.doe@example.com',
                    'person': 'John Doe',
                    'team': 'Team Alpha',
                    'requests': 1234,
                    'tokens': 245600,
                    'cost': Decimal('12.28')
                },
                {
                    'email': 'jane.smith@example.com',
                    'person': 'Jane Smith',
                    'team': 'Team Beta',
                    'requests': 987,
                    'tokens': 198400,
                    'cost': Decimal('9.92')
                },
                {
                    'email': 'bob.wilson@example.com',
                    'person': 'Bob Wilson',
                    'team': 'Team Alpha',
                    'requests': 756,
                    'tokens': 151200,
                    'cost': Decimal('7.56')
                },
            ]
        
        elif "COUNT(DISTINCT cognito_email) as total" in query:
            # Query de conteo de usuarios
            return [{'total': 45}]
        
        elif "COUNT(*) as total_requests" in query:
            # Query de estadísticas de período
            return [{
                'total_requests': 12458,
                'total_tokens': 2400000,
                'total_cost': Decimal('124.50'),
                'avg_response_time': 1234
            }]
        
        return []


def print_section(title):
    """Imprimir sección con formato"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_result(test_name, result, success=True):
    """Imprimir resultado de prueba"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"\n{status} - {test_name}")
    print("-" * 80)
    print(json.dumps(result, indent=2, default=str))


def test_all_methods():
    """Probar todos los métodos del servicio"""
    
    print_section("PROXY USAGE SERVICE - TEST SUITE (MOCK)")
    
    # Importar el servicio
    sys.path.insert(0, '/Users/csarrion/Cline/identity-manager-v2/backend/lambdas/identity-mgmt-api')
    from services.proxy_usage_service import ProxyUsageService
    
    # Crear servicio con mock
    mock_db = MockDatabaseService()
    service = ProxyUsageService(mock_db)
    
    # Definir período de prueba
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    print(f"\n📅 Período de prueba:")
    print(f"   Inicio: {start_date.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Fin:    {end_date.strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Test 1: get_summary()
    print_section("TEST 1: get_summary()")
    try:
        result = service.get_summary(start_date, end_date)
        assert 'total_requests' in result
        assert 'requests_change' in result
        assert '%' in result['requests_change']
        print_result("get_summary()", result, True)
        results.append(True)
    except Exception as e:
        print_result("get_summary()", {"error": str(e)}, False)
        results.append(False)
    
    # Test 2: get_usage_by_hour()
    print_section("TEST 2: get_usage_by_hour()")
    try:
        result = service.get_usage_by_hour(start_date, end_date)
        assert len(result['labels']) == 24
        assert len(result['values']) == 24
        assert 'peak_hour' in result
        print_result("get_usage_by_hour()", result, True)
        results.append(True)
    except Exception as e:
        print_result("get_usage_by_hour()", {"error": str(e)}, False)
        results.append(False)
    
    # Test 3: get_usage_by_team()
    print_section("TEST 3: get_usage_by_team()")
    try:
        result = service.get_usage_by_team(start_date, end_date)
        assert 'labels' in result
        assert 'values' in result
        assert 'top_team' in result
        assert result['top_team']['name'] == 'Team Alpha'
        print_result("get_usage_by_team()", result, True)
        results.append(True)
    except Exception as e:
        print_result("get_usage_by_team()", {"error": str(e)}, False)
        results.append(False)
    
    # Test 4: get_usage_by_day()
    print_section("TEST 4: get_usage_by_day()")
    try:
        result = service.get_usage_by_day(start_date, end_date)
        assert 'labels' in result
        assert 'values' in result
        assert 'peak_day' in result
        print_result("get_usage_by_day()", result, True)
        results.append(True)
    except Exception as e:
        print_result("get_usage_by_day()", {"error": str(e)}, False)
        results.append(False)
    
    # Test 5: get_response_status()
    print_section("TEST 5: get_response_status()")
    try:
        result = service.get_response_status(start_date, end_date)
        assert 'labels' in result
        assert 'values' in result
        assert 'success_rate' in result
        assert result['success_rate']['percentage'] > 0
        print_result("get_response_status()", result, True)
        results.append(True)
    except Exception as e:
        print_result("get_response_status()", {"error": str(e)}, False)
        results.append(False)
    
    # Test 6: get_usage_trend()
    print_section("TEST 6: get_usage_trend()")
    try:
        result = service.get_usage_trend(start_date, end_date)
        assert 'labels' in result
        assert 'datasets' in result
        assert len(result['datasets']) > 0
        print_result("get_usage_trend()", result, True)
        results.append(True)
    except Exception as e:
        print_result("get_usage_trend()", {"error": str(e)}, False)
        results.append(False)
    
    # Test 7: get_usage_by_user()
    print_section("TEST 7: get_usage_by_user()")
    try:
        result = service.get_usage_by_user(start_date, end_date, page=1, page_size=5)
        assert 'users' in result
        assert 'pagination' in result
        assert result['pagination']['page'] == 1
        assert result['pagination']['page_size'] == 5
        print_result("get_usage_by_user()", result, True)
        results.append(True)
    except Exception as e:
        print_result("get_usage_by_user()", {"error": str(e)}, False)
        results.append(False)
    
    # Resumen
    print_section("RESUMEN DE PRUEBAS")
    passed = sum(results)
    total = len(results)
    percentage = (passed / total * 100) if total > 0 else 0
    
    print(f"\n✅ Pruebas exitosas: {passed}/{total} ({percentage:.1f}%)")
    
    if passed == total:
        print("\n🎉 ¡Todas las pruebas pasaron exitosamente!")
        print("\n📝 Nota: Estas pruebas usan datos mock.")
        print("   Para pruebas con datos reales, ejecutar desde un entorno con acceso a RDS.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} prueba(s) fallaron")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(test_all_methods())
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)