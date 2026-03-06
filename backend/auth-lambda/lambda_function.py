"""
Auth Lambda Function
====================
Lambda para autenticación de usuarios con Cognito y gestión de permisos

Endpoints:
- POST /auth/login: Autenticación con Cognito
- POST /auth/verify: Validación de token JWT
"""

import json
import logging
import os
from typing import Dict, Any

from auth_service import AuthService
from shared.utils.response_builder import build_response, build_error_response
from shared.logging import get_logger, configure_logger

# Configurar logging estándar
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Inicializar servicios (lazy loading)
auth_service = None
ams_logger = None


def initialize_services():
    """Inicializar servicios en la primera invocación (lazy loading)"""
    global auth_service, ams_logger
    
    if auth_service is None:
        logger.info("Inicializando AuthService...")
        auth_service = AuthService()
        logger.info("AuthService inicializado correctamente")
    
    if ams_logger is None:
        logger.info("Inicializando AMS Logger...")
        ams_logger = configure_logger(
            service_version="1.0.0",
            environment=os.environ.get('ENVIRONMENT', 'dev')
        )
        logger.info("AMS Logger inicializado correctamente")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handler principal de la Lambda
    
    Args:
        event: Evento de API Gateway
        context: Contexto de ejecución
        
    Returns:
        Response HTTP
    """
    request_id = context.aws_request_id if context else 'local'
    
    logger.info(f"[{request_id}] Iniciando procesamiento de request")
    logger.info(f"[{request_id}] Event: {json.dumps(event)}")
    
    # Extraer método HTTP PRIMERO
    http_method = event.get('httpMethod', event.get('requestContext', {}).get('http', {}).get('method', 'POST'))
    path = event.get('path', event.get('rawPath', ''))
    
    logger.info(f"[{request_id}] {http_method} {path}")
    
    # Manejar preflight CORS (OPTIONS) ANTES de cualquier otra cosa
    if http_method == 'OPTIONS':
        logger.info(f"[{request_id}] Respondiendo a preflight CORS")
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': ''
        }
    
    try:
        # Inicializar servicios
        initialize_services()
        
        # Configurar trazabilidad en AMS Logger
        headers = event.get('headers', {})
        trace_id = headers.get('X-Trace-Id') or headers.get('x-trace-id')
        
        if trace_id:
            ams_logger.set_trace_id(trace_id)
        else:
            ams_logger.new_trace()
        
        ams_logger.set_request_id(request_id)
        
        # Log estructurado de inicio de request
        ams_logger.info(
            event_name="AUTH_REQUEST_RECEIVED",
            message=f"Processing {http_method} {path}",
            http_method=http_method,
            path=path
        )
        
        # Parsear body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Routing
        if path == '/auth/login' and http_method == 'POST':
            result = handle_login(body, request_id)
        elif path == '/auth/verify' and http_method == 'POST':
            result = handle_verify(body, request_id)
        elif path == '/auth/forgot-password' and http_method == 'POST':
            result = handle_forgot_password(body, request_id)
        else:
            ams_logger.warning(
                event_name="AUTH_ENDPOINT_NOT_FOUND",
                message=f"Endpoint not found: {http_method} {path}",
                http_method=http_method,
                path=path
            )
            return build_error_response(
                'NOT_FOUND',
                f'Endpoint no encontrado: {http_method} {path}',
                404
            )
        
        logger.info(f"[{request_id}] Operación completada exitosamente")
        ams_logger.info(
            event_name="AUTH_REQUEST_COMPLETED",
            message="Request completed successfully",
            http_method=http_method,
            path=path
        )
        return build_response(result)
        
    except ValueError as e:
        error_message = str(e)
        logger.error(f"[{request_id}] Error de validación: {error_message}")
        
        # Log estructurado de error de validación
        ams_logger.error(
            event_name="AUTH_VALIDATION_ERROR",
            message="Validation error occurred",
            error_type="ValueError",
            error_message=error_message,
            http_method=http_method,
            path=path
        )
        
        # Si es NEW_PASSWORD_REQUIRED, devolver código especial
        if error_message == 'NEW_PASSWORD_REQUIRED':
            return build_response({
                'success': False,
                'requiresPasswordChange': True,
                'message': 'Se requiere cambio de contraseña temporal'
            })
        
        # Si es INSUFFICIENT_PERMISSIONS, devolver error 403
        if error_message.startswith('INSUFFICIENT_PERMISSIONS'):
            app_id = error_message.split(':')[1] if ':' in error_message else 'desconocida'
            return build_error_response(
                'INSUFFICIENT_PERMISSIONS',
                f'No tienes permisos para acceder a esta aplicación (ID: {app_id})',
                403
            )
        
        return build_error_response('VALIDATION_ERROR', error_message, 400)
        
    except Exception as e:
        logger.error(f"[{request_id}] Error inesperado: {str(e)}", exc_info=True)
        
        # Log estructurado de error crítico
        ams_logger.fatal(
            event_name="AUTH_SYSTEM_ERROR",
            message="Unexpected system error occurred",
            error_type=type(e).__name__,
            error_message=str(e),
            http_method=http_method,
            path=path
        )
        
        return build_error_response(
            'INTERNAL_ERROR',
            'Error interno del servidor',
            500,
            {'detail': str(e)}
        )


def handle_login(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """
    Handler para login
    
    Args:
        body: Datos del request
        request_id: ID del request
        
    Returns:
        Resultado del login
    """
    logger.info(f"[{request_id}] Procesando login")
    
    # Validar parámetros
    email = body.get('email')
    password = body.get('password')
    new_password = body.get('new_password')  # Para cambio de contraseña
    required_app_id = body.get('app_id')  # ID de aplicación requerida (opcional)
    
    if not email or not password:
        raise ValueError('Los parámetros "email" y "password" son requeridos')
    
    # Autenticar (con nueva contraseña y validación de permisos si se proporciona)
    result = auth_service.login(email, password, new_password, required_app_id)
    
    logger.info(f"[{request_id}] Login exitoso para {email}")
    
    return result


def handle_verify(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """
    Handler para verificación de token
    
    Args:
        body: Datos del request
        request_id: ID del request
        
    Returns:
        Resultado de la verificación
    """
    logger.info(f"[{request_id}] Verificando token")
    
    # Validar parámetros
    token = body.get('token')
    
    if not token:
        raise ValueError('El parámetro "token" es requerido')
    
    # Verificar
    result = auth_service.verify_token(token)
    
    if result.get('valid'):
        logger.info(f"[{request_id}] Token verificado exitosamente")
    else:
        logger.warning(f"[{request_id}] Token inválido: {result.get('error')}")
    
    return result


def handle_forgot_password(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """
    Handler para recuperación de contraseña
    
    Args:
        body: Datos del request
        request_id: ID del request
        
    Returns:
        Resultado de la operación
    """
    logger.info(f"[{request_id}] Procesando recuperación de contraseña")
    
    # Validar parámetros
    email = body.get('email')
    
    if not email:
        raise ValueError('El parámetro "email" es requerido')
    
    # Resetear contraseña
    result = auth_service.forgot_password(email)
    
    logger.info(f"[{request_id}] Contraseña reseteada para {email}")
    
    return result


# Para testing local
if __name__ == '__main__':
    # Simular evento de API Gateway para login
    test_event_login = {
        'path': '/auth/login',
        'httpMethod': 'POST',
        'body': json.dumps({
            'email': 'test@example.com',
            'password': 'TestPassword123!'
        })
    }
    
    # Simular contexto
    class MockContext:
        aws_request_id = 'test-request-id'
    
    print("Testing login endpoint...")
    response = lambda_handler(test_event_login, MockContext())
    print(json.dumps(response, indent=2))