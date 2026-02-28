"""
Response Builder
================
Constructor de respuestas HTTP para API Gateway
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional


def build_response(
    data: Any,
    status_code: int = 200,
    message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Construir respuesta exitosa
    
    Args:
        data: Datos de respuesta
        status_code: Código HTTP
        message: Mensaje opcional
        
    Returns:
        Dict con respuesta formateada para API Gateway
    """
    body = {
        'success': True,
        'data': data,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    
    if message:
        body['message'] = message
    
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json'
            # CORS headers are managed by Lambda Function URL configuration
        },
        'body': json.dumps(body, default=str)
    }


def build_error_response(
    error_code: str,
    error_message: str,
    status_code: int = 400,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Construir respuesta de error
    
    Args:
        error_code: Código de error
        error_message: Mensaje de error
        status_code: Código HTTP
        details: Detalles adicionales del error
        
    Returns:
        Dict con respuesta de error formateada para API Gateway
    """
    body = {
        'success': False,
        'error': {
            'code': error_code,
            'message': error_message
        },
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    
    if details:
        body['error']['details'] = details
    
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json'
            # CORS headers are managed by Lambda Function URL configuration
        },
        'body': json.dumps(body, default=str)
    }


def build_validation_error_response(validation_errors: Dict[str, str]) -> Dict[str, Any]:
    """
    Construir respuesta de error de validación
    
    Args:
        validation_errors: Dict con errores de validación por campo
        
    Returns:
        Dict con respuesta de error de validación
    """
    return build_error_response(
        'VALIDATION_ERROR',
        'Errores de validación en los datos proporcionados',
        400,
        {'validation_errors': validation_errors}
    )


def build_not_found_response(resource_type: str, resource_id: str) -> Dict[str, Any]:
    """
    Construir respuesta de recurso no encontrado
    
    Args:
        resource_type: Tipo de recurso
        resource_id: ID del recurso
        
    Returns:
        Dict con respuesta 404
    """
    return build_error_response(
        'NOT_FOUND',
        f'{resource_type} no encontrado',
        404,
        {'resource_type': resource_type, 'resource_id': resource_id}
    )


def build_unauthorized_response(message: str = 'No autorizado') -> Dict[str, Any]:
    """
    Construir respuesta de no autorizado
    
    Args:
        message: Mensaje de error
        
    Returns:
        Dict con respuesta 401
    """
    return build_error_response(
        'UNAUTHORIZED',
        message,
        401
    )


def build_forbidden_response(message: str = 'Acceso denegado') -> Dict[str, Any]:
    """
    Construir respuesta de acceso denegado
    
    Args:
        message: Mensaje de error
        
    Returns:
        Dict con respuesta 403
    """
    return build_error_response(
        'FORBIDDEN',
        message,
        403
    )


def build_conflict_response(message: str, details: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Construir respuesta de conflicto
    
    Args:
        message: Mensaje de error
        details: Detalles del conflicto
        
    Returns:
        Dict con respuesta 409
    """
    return build_error_response(
        'CONFLICT',
        message,
        409,
        details
    )


def build_rate_limit_response(retry_after: int = 60) -> Dict[str, Any]:
    """
    Construir respuesta de límite de tasa excedido
    
    Args:
        retry_after: Segundos hasta que se puede reintentar
        
    Returns:
        Dict con respuesta 429
    """
    response = build_error_response(
        'RATE_LIMIT_EXCEEDED',
        'Límite de solicitudes excedido',
        429,
        {'retry_after_seconds': retry_after}
    )
    
    response['headers']['Retry-After'] = str(retry_after)
    
    return response
