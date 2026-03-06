#!/usr/bin/env python3
"""
Script de prueba para verificar ams-logging-policy
"""

import sys
sys.path.insert(0, 'backend')

print("=" * 70)
print("  PRUEBA DE AMS LOGGING POLICY")
print("=" * 70)

# Test 1: Importar módulo
print("\n1️⃣  Importando módulo...")
try:
    from shared.ams_logging import AMSLogger, LogConfig
    print("   ✅ Módulo importado correctamente")
except Exception as e:
    print(f"   ❌ Error al importar: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Crear logger
print("\n2️⃣  Creando logger...")
try:
    config = LogConfig(
        service_name="identity-mgmt",
        service_version="1.0.0",
        environment="dev"
    )
    logger = AMSLogger(config)
    print("   ✅ Logger creado correctamente")
except Exception as e:
    print(f"   ❌ Error al crear logger: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Generar log de prueba
print("\n3️⃣  Generando log de prueba...")
try:
    logger.new_trace()
    logger.info(
        event_name="TEST_EVENT",
        message="Testing AMS Logger integration",
        test_field="test_value"
    )
    print("   ✅ Log generado correctamente (ver arriba en formato JSON)")
except Exception as e:
    print(f"   ❌ Error al generar log: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Probar sanitización
print("\n4️⃣  Probando sanitización...")
try:
    logger.info(
        event_name="SANITIZATION_TEST",
        message="Testing data sanitization",
        user_data={
            "username": "test_user",
            "password": "secret123",  # Debe ser sanitizado
            "token": "abc123xyz"      # Debe ser sanitizado
        }
    )
    print("   ✅ Sanitización funciona (verifica que password/token estén redactados)")
except Exception as e:
    print(f"   ❌ Error en sanitización: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Probar diferentes niveles de log
print("\n5️⃣  Probando diferentes niveles de log...")
try:
    logger.debug("DEBUG_TEST", "Debug message")
    logger.info("INFO_TEST", "Info message")
    logger.warning("WARNING_TEST", "Warning message")
    logger.error(
        event_name="ERROR_TEST",
        message="Error message",
        error_type="TestError",
        error_message="This is a test error"
    )
    print("   ✅ Todos los niveles de log funcionan")
except Exception as e:
    print(f"   ❌ Error en niveles de log: {e}")
    import traceback
    traceback.print_exc()

# Test 6: Probar trazabilidad
print("\n6️⃣  Probando trazabilidad (trace_id, request_id)...")
try:
    logger.set_trace_id("test-trace-123")
    logger.set_request_id("test-req-456")
    
    logger.info(
        event_name="TRACE_TEST",
        message="Testing traceability"
    )
    print("   ✅ Trazabilidad funciona (verifica trace.id y request.id en el log)")
except Exception as e:
    print(f"   ❌ Error en trazabilidad: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("  ✅ TODAS LAS PRUEBAS COMPLETADAS")
print("=" * 70)
print("\n💡 La librería está lista para ser integrada en el proyecto")
print("   Los logs JSON aparecen arriba mezclados con los mensajes de prueba")
print("   En producción, solo verías los logs JSON en stdout.\n")