"""
Test Script for Proxy Usage Service
====================================
Script para probar las funciones del servicio de uso del proxy.

Uso:
    python test_proxy_usage.py
"""

import json
import sys
from datetime import datetime, timedelta
from services.database_service import DatabaseService
from services.proxy_usage_service import ProxyUsageService


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


def test_get_summary(service, start_date, end_date):
    """Test: get_summary()"""
    print_section("TEST 1: get_summary()")
    
    try:
        result = service.get_summary(start_date, end_date)
        
        # Validaciones
        assert 'total_requests' in result, "Falta 'total_requests'"
        assert 'requests_change' in result, "Falta 'requests_change'"
        assert 'total_tokens' in result, "Falta 'total_tokens'"
        assert 'total_cost' in result, "Falta 'total_cost'"
        assert 'avg_response_time' in result, "Falta 'avg_response_time'"
        assert 'period' in result, "Falta 'period'"
        
        # Validar formato de cambios
        assert '%' in result['requests_change'], "Formato de cambio incorrecto"
        
        print_result("get_summary()", result, True)
        return True
        
    except Exception as e:
        print_result("get_summary()", {"error": str(e)}, False)
        return False


def test_get_usage_by_hour(service, start_date, end_date):
    """Test: get_usage_by_hour()"""
    print_section("TEST 2: get_usage_by_hour()")
    
    try:
        result = service.get_usage_by_hour(start_date, end_date)
        
        # Validaciones
        assert 'labels' in result, "Falta 'labels'"
        assert 'values' in result, "Falta 'values'"
        assert 'peak_hour' in result, "Falta 'peak_hour'"
        assert len(result['labels']) == 24, "Debe haber 24 horas"
        assert len(result['values']) == 24, "Debe haber 24 valores"
        assert 'hour' in result['peak_hour'], "Falta 'hour' en peak_hour"
        assert 'requests' in result['peak_hour'], "Falta 'requests' en peak_hour"
        
        print_result("get_usage_by_hour()", result, True)
        return True
        
    except Exception as e:
        print_result("get_usage_by_hour()", {"error": str(e)}, False)
        return False


def test_get_usage_by_team(service, start_date, end_date):
    """Test: get_usage_by_team()"""
    print_section("TEST 3: get_usage_by_team()")
    
    try:
        result = service.get_usage_by_team(start_date, end_date)
        
        # Validaciones
        assert 'labels' in result, "Falta 'labels'"
        assert 'values' in result, "Falta 'values'"
        assert 'top_team' in result, "Falta 'top_team'"
        assert len(result['labels']) == len(result['values']), "Labels y values deben tener mismo tamaño"
        assert 'name' in result['top_team'], "Falta 'name' en top_team"
        assert 'requests' in result['top_team'], "Falta 'requests' en top_team"
        assert 'percentage' in result['top_team'], "Falta 'percentage' en top_team"
        
        print_result("get_usage_by_team()", result, True)
        return True
        
    except Exception as e:
        print_result("get_usage_by_team()", {"error": str(e)}, False)
        return False


def test_get_usage_by_day(service, start_date, end_date):
    """Test: get_usage_by_day()"""
    print_section("TEST 4: get_usage_by_day()")
    
    try:
        result = service.get_usage_by_day(start_date, end_date)
        
        # Validaciones
        assert 'labels' in result, "Falta 'labels'"
        assert 'values' in result, "Falta 'values'"
        assert 'peak_day' in result, "Falta 'peak_day'"
        assert len(result['labels']) == len(result['values']), "Labels y values deben tener mismo tamaño"
        assert 'date' in result['peak_day'], "Falta 'date' en peak_day"
        assert 'requests' in result['peak_day'], "Falta 'requests' en peak_day"
        
        print_result("get_usage_by_day()", result, True)
        return True
        
    except Exception as e:
        print_result("get_usage_by_day()", {"error": str(e)}, False)
        return False


def test_get_response_status(service, start_date, end_date):
    """Test: get_response_status()"""
    print_section("TEST 5: get_response_status()")
    
    try:
        result = service.get_response_status(start_date, end_date)
        
        # Validaciones
        assert 'labels' in result, "Falta 'labels'"
        assert 'values' in result, "Falta 'values'"
        assert 'success_rate' in result, "Falta 'success_rate'"
        assert len(result['labels']) == len(result['values']), "Labels y values deben tener mismo tamaño"
        assert 'percentage' in result['success_rate'], "Falta 'percentage' en success_rate"
        assert 'successful_requests' in result['success_rate'], "Falta 'successful_requests'"
        assert 'total_requests' in result['success_rate'], "Falta 'total_requests'"
        
        print_result("get_response_status()", result, True)
        return True
        
    except Exception as e:
        print_result("get_response_status()", {"error": str(e)}, False)
        return False


def test_get_usage_trend(service, start_date, end_date):
    """Test: get_usage_trend()"""
    print_section("TEST 6: get_usage_trend()")
    
    try:
        result = service.get_usage_trend(start_date, end_date)
        
        # Validaciones
        assert 'labels' in result, "Falta 'labels'"
        assert 'datasets' in result, "Falta 'datasets'"
        assert isinstance(result['datasets'], list), "datasets debe ser una lista"
        
        if len(result['datasets']) > 0:
            dataset = result['datasets'][0]
            assert 'label' in dataset, "Falta 'label' en dataset"
            assert 'data' in dataset, "Falta 'data' en dataset"
            assert len(dataset['data']) == len(result['labels']), "data y labels deben tener mismo tamaño"
        
        print_result("get_usage_trend()", result, True)
        return True
        
    except Exception as e:
        print_result("get_usage_trend()", {"error": str(e)}, False)
        return False


def test_get_usage_by_user(service, start_date, end_date):
    """Test: get_usage_by_user()"""
    print_section("TEST 7: get_usage_by_user()")
    
    try:
        result = service.get_usage_by_user(start_date, end_date, page=1, page_size=5)
        
        # Validaciones
        assert 'users' in result, "Falta 'users'"
        assert 'pagination' in result, "Falta 'pagination'"
        assert isinstance(result['users'], list), "users debe ser una lista"
        
        # Validar paginación
        pagination = result['pagination']
        assert 'page' in pagination, "Falta 'page' en pagination"
        assert 'page_size' in pagination, "Falta 'page_size' en pagination"
        assert 'total_records' in pagination, "Falta 'total_records' en pagination"
        assert 'total_pages' in pagination, "Falta 'total_pages' en pagination"
        assert pagination['page'] == 1, "page debe ser 1"
        assert pagination['page_size'] == 5, "page_size debe ser 5"
        
        # Validar estructura de usuarios
        if len(result['users']) > 0:
            user = result['users'][0]
            assert 'email' in user, "Falta 'email' en user"
            assert 'person' in user, "Falta 'person' en user"
            assert 'team' in user, "Falta 'team' en user"
            assert 'requests' in user, "Falta 'requests' en user"
            assert 'tokens' in user, "Falta 'tokens' en user"
            assert 'cost' in user, "Falta 'cost' en user"
        
        print_result("get_usage_by_user()", result, True)
        return True
        
    except Exception as e:
        print_result("get_usage_by_user()", {"error": str(e)}, False)
        return False


def test_edge_cases(service):
    """Test: Casos edge"""
    print_section("TEST 8: Casos Edge")
    
    results = []
    
    # Test 1: Período sin datos (futuro)
    try:
        future_start = datetime.now() + timedelta(days=365)
        future_end = future_start + timedelta(days=7)
        result = service.get_summary(future_start, future_end)
        
        assert result['total_requests'] == 0, "Debe retornar 0 requests para período futuro"
        print("  ✅ Período sin datos: OK")
        results.append(True)
    except Exception as e:
        print(f"  ❌ Período sin datos: {e}")
        results.append(False)
    
    # Test 2: Período de 1 día
    try:
        one_day_start = datetime.now() - timedelta(days=1)
        one_day_end = datetime.now()
        result = service.get_usage_by_day(one_day_start, one_day_end)
        
        assert 'labels' in result, "Debe retornar labels"
        print("  ✅ Período de 1 día: OK")
        results.append(True)
    except Exception as e:
        print(f"  ❌ Período de 1 día: {e}")
        results.append(False)
    
    # Test 3: Paginación con página vacía
    try:
        start = datetime.now() - timedelta(days=7)
        end = datetime.now()
        result = service.get_usage_by_user(start, end, page=999, page_size=10)
        
        assert len(result['users']) == 0, "Debe retornar lista vacía para página inexistente"
        print("  ✅ Paginación vacía: OK")
        results.append(True)
    except Exception as e:
        print(f"  ❌ Paginación vacía: {e}")
        results.append(False)
    
    return all(results)


def main():
    """Función principal"""
    print("\n" + "=" * 80)
    print("  PROXY USAGE SERVICE - TEST SUITE")
    print("=" * 80)
    
    try:
        # Inicializar servicios
        print("\n📦 Inicializando servicios...")
        db_service = DatabaseService()
        proxy_usage_service = ProxyUsageService(db_service)
        print("✅ Servicios inicializados correctamente")
        
        # Definir período de prueba (últimos 30 días)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        print(f"\n📅 Período de prueba:")
        print(f"   Inicio: {start_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Fin:    {end_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Ejecutar pruebas
        results = []
        
        results.append(test_get_summary(proxy_usage_service, start_date, end_date))
        results.append(test_get_usage_by_hour(proxy_usage_service, start_date, end_date))
        results.append(test_get_usage_by_team(proxy_usage_service, start_date, end_date))
        results.append(test_get_usage_by_day(proxy_usage_service, start_date, end_date))
        results.append(test_get_response_status(proxy_usage_service, start_date, end_date))
        results.append(test_get_usage_trend(proxy_usage_service, start_date, end_date))
        results.append(test_get_usage_by_user(proxy_usage_service, start_date, end_date))
        results.append(test_edge_cases(proxy_usage_service))
        
        # Resumen final
        print_section("RESUMEN DE PRUEBAS")
        
        passed = sum(results)
        total = len(results)
        percentage = (passed / total * 100) if total > 0 else 0
        
        print(f"\n✅ Pruebas exitosas: {passed}/{total} ({percentage:.1f}%)")
        
        if passed == total:
            print("\n🎉 ¡Todas las pruebas pasaron exitosamente!")
            return 0
        else:
            print(f"\n⚠️  {total - passed} prueba(s) fallaron")
            return 1
            
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())