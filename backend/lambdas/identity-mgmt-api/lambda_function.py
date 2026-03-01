"""
Identity Manager API Lambda Function
=====================================
Función Lambda principal para gestión de usuarios, tokens JWT y perfiles de inferencia.

Nombre: identity-mgmt-dev-api-lmbd
Runtime: Python 3.12
"""

import json
import jwt
import logging
import os
from datetime import datetime
from typing import Dict, Any

# Configurar logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Importar servicios
from services.cognito_service import CognitoService
from services.database_service import DatabaseService
from services.jwt_service import JWTService
from services.email_service import EmailService
from services.permissions_service import PermissionsService
from utils.validators import validate_request
from utils.response_builder import build_response, build_error_response

# Inicializar servicios
cognito_service = None
database_service = None
jwt_service = None
email_service = None
permissions_service = None


def initialize_services():
    """Inicializar servicios en el primer invocación (lazy loading)"""
    global cognito_service, database_service, jwt_service, email_service, permissions_service
    
    if cognito_service is None:
        cognito_service = CognitoService()
    if database_service is None:
        database_service = DatabaseService()
    if jwt_service is None:
        jwt_service = JWTService()
    if email_service is None:
        email_service = EmailService()
    if permissions_service is None:
        permissions_service = PermissionsService()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handler principal de la Lambda
    
    Args:
        event: Evento de API Gateway con el request
        context: Contexto de ejecución de Lambda
        
    Returns:
        Response con el resultado de la operación
    """
    request_id = context.aws_request_id if context else 'local'
    
    logger.info(f"[{request_id}] Iniciando procesamiento de request")
    
    try:
        # Inicializar servicios
        initialize_services()
        
        # Parsear body del request
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extraer operación
        operation = body.get('operation')
        
        if not operation:
            return build_error_response(
                'MISSING_PARAMETERS',
                'El parámetro "operation" es requerido',
                400
            )
        
        logger.info(f"[{request_id}] Operación solicitada: {operation}")
        
        # Validar request según operación
        validation_error = validate_request(operation, body)
        if validation_error:
            return build_error_response(
                'VALIDATION_ERROR',
                validation_error,
                400
            )
        
        # Routing de operaciones
        result = route_operation(operation, body, request_id)
        
        logger.info(f"[{request_id}] Operación completada exitosamente")
        
        return build_response(result)
        
    except ValueError as e:
        logger.error(f"[{request_id}] Error de validación: {str(e)}")
        return build_error_response('VALIDATION_ERROR', str(e), 400)
        
    except Exception as e:
        logger.error(f"[{request_id}] Error inesperado: {str(e)}", exc_info=True)
        return build_error_response(
            'INTERNAL_ERROR',
            'Error interno del servidor',
            500,
            {'detail': str(e)}
        )


def route_operation(operation: str, body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """
    Enrutar la operación al handler correspondiente
    
    Args:
        operation: Nombre de la operación
        body: Datos del request
        request_id: ID del request para logging
        
    Returns:
        Resultado de la operación
    """
    operations = {
        # Operaciones de usuarios
        'list_users': handle_list_users,
        'create_user': handle_create_user,
        'delete_user': handle_delete_user,
        
        # Operaciones de tokens
        'list_tokens': handle_list_tokens,
        'create_token': handle_create_token,
        'validate_token': handle_validate_token,
        'revoke_token': handle_revoke_token,
        'restore_token': handle_restore_token,
        'delete_token': handle_delete_token,
        
        # Operaciones de perfiles
        'list_profiles': handle_list_profiles,
        
        # Operaciones de grupos
        'list_groups': handle_list_groups,
        
        # Operaciones de permisos
        'assign_app_permission': handle_assign_app_permission,
        'assign_module_permission': handle_assign_module_permission,
        'revoke_app_permission': handle_revoke_app_permission,
        'revoke_module_permission': handle_revoke_module_permission,
        'get_user_permissions': handle_get_user_permissions,
        'list_all_permissions': handle_list_all_permissions,
        'list_permission_types': handle_list_permission_types,
        'list_applications': handle_list_applications,
        'list_modules': handle_list_modules,

        # Operaciones de configuración
        'get_config': handle_get_config,
    }
    
    handler = operations.get(operation)
    
    if not handler:
        raise ValueError(f'Operación no reconocida: {operation}')
    
    return handler(body, request_id)


# ============================================================================
# HANDLERS DE OPERACIONES - USUARIOS
# ============================================================================

def handle_list_users(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Listar usuarios de Cognito"""
    logger.info(f"[{request_id}] Listando usuarios")
    
    filters = body.get('filters', {})
    pagination = body.get('pagination', {})
    
    result = cognito_service.list_users(
        group=filters.get('group'),
        status=filters.get('status'),
        limit=pagination.get('limit', 60),
        pagination_token=pagination.get('pagination_token')
    )
    
    return result


def handle_create_user(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Crear nuevo usuario en Cognito"""
    logger.info(f"[{request_id}] Creando usuario")
    
    data = body.get('data', {})
    email = data['email']
    
    # Verificar si el usuario ya existe
    try:
        existing_user = cognito_service.get_user(email)
        # Si llegamos aquí, el usuario existe
        logger.warning(f"[{request_id}] Usuario {email} ya existe")
        raise ValueError(f'El usuario con email {email} ya existe en el sistema')
    except ValueError as e:
        # Si el error es "Usuario no encontrado", está bien, podemos crear el usuario
        if 'no encontrado' in str(e).lower():
            logger.info(f"[{request_id}] Usuario {email} no existe, procediendo con creación")
        else:
            # Si es otro error de validación, propagarlo
            logger.error(f"[{request_id}] Error de validación: {e}")
            raise
    except Exception as e:
        # Si hay otro error al verificar, loguear y continuar con la creación
        logger.warning(f"[{request_id}] Error verificando usuario existente: {e}, continuando con creación")
    
    result = cognito_service.create_user(
        email=email,
        person=data['person'],
        group=data['group'],
        temporary_password=data.get('temporary_password'),
        send_email=data.get('send_email', True),
        auto_regenerate_tokens=data.get('auto_regenerate_tokens', True)
    )
    
    # Registrar en auditoría
    database_service.log_audit(
        operation_type='CREATE_USER',
        resource_type='cognito_user',
        resource_id=result['user']['user_id'],
        cognito_user_id=result['user']['user_id'],
        cognito_email=result['user']['email'],
        new_value=result['user'],
        request_id=request_id
    )
    
    return result


def handle_delete_user(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Eliminar usuario y todos sus datos relacionados"""
    logger.info(f"[{request_id}] Eliminando usuario")
    
    user_id = body.get('user_id')
    
    # Obtener info del usuario antes de eliminar
    user_info = cognito_service.get_user(user_id)
    
    # Eliminar datos en BD (tokens, permisos)
    deleted_data = database_service.delete_user_data(user_id)
    
    # Eliminar usuario de Cognito
    cognito_service.delete_user(user_id)
    
    # Registrar en auditoría
    database_service.log_audit(
        operation_type='DELETE_USER',
        resource_type='cognito_user',
        resource_id=user_id,
        cognito_user_id=user_id,
        cognito_email=user_info.get('email'),
        previous_value=user_info,
        request_id=request_id
    )
    
    result = {
        'success': True,
        'deleted': {
            'cognito_user': True,
            **deleted_data
        },
        'message': 'Usuario y todos sus datos eliminados correctamente'
    }
    
    return result


# ============================================================================
# HANDLERS DE OPERACIONES - TOKENS
# ============================================================================

def handle_list_tokens(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Listar tokens JWT"""
    logger.info(f"[{request_id}] Listando tokens")
    
    filters = body.get('filters', {})
    pagination = body.get('pagination', {})
    
    result = database_service.list_tokens(
        user_id=filters.get('user_id'),
        status=filters.get('status', 'all'),
        profile_id=filters.get('profile_id'),
        limit=pagination.get('limit', 50),
        offset=pagination.get('offset', 0)
    )
    
    return result


def handle_create_token(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Crear nuevo token JWT"""
    logger.info(f"[{request_id}] Creando token JWT")
    
    data = body.get('data', {})
    user_id = data['user_id']
    validity_period = data.get('validity_period', '90_days')
    profile_id = data['application_profile_id']
    
    # Obtener información del usuario de Cognito
    user_info = cognito_service.get_user(user_id)
    
    # Obtener información del perfil
    profile_info = database_service.get_profile(profile_id)
    
    if not profile_info or not profile_info.get('is_active'):
        raise ValueError('Perfil de inferencia no encontrado o inactivo')
    
    # Verificar límite de tokens activos
    active_tokens_count = database_service.count_active_tokens(user_id)
    max_tokens = database_service.get_config_value('max_tokens_per_user', 2)
    
    if active_tokens_count >= int(max_tokens):
        raise ValueError(f'Usuario ha alcanzado el límite de {max_tokens} tokens activos')
    
    # Obtener audiences desde configuración
    audiences_config = database_service.get_config_value('jwt_token_audiences', 'bedrock-proxy')
    audiences = [aud.strip() for aud in audiences_config.split(',')]
    
    # Generar token JWT
    token_data = jwt_service.generate_token(
        user_info=user_info,
        profile_info=profile_info,
        validity_period=validity_period,
        audiences=audiences
    )
    
    # Guardar en BD
    token_record = database_service.save_token(
        user_id=user_id,
        email=user_info['email'],
        jti=token_data['jti'],
        token_hash=token_data['token_hash'],
        profile_id=profile_id,
        expires_at=token_data['expires_at']
    )
    
    # Registrar en auditoría
    database_service.log_audit(
        operation_type='CREATE_TOKEN',
        resource_type='jwt_token',
        resource_id=token_record['token_id'],
        cognito_user_id=user_id,
        cognito_email=user_info['email'],
        new_value={'jti': token_data['jti'], 'user_id': user_id},
        request_id=request_id
    )
    
    # Preparar resultado
    result = {
        'success': True,
        'token': {
            'jwt': token_data['jwt'],
            'token_id': token_record['token_id'],
            'jti': token_data['jti'],
            'issued_at': token_data['issued_at'],
            'expires_at': token_data['expires_at'],
            'validity_days': token_data['validity_days'],
            'profile': {
                'profile_name': profile_info['profile_name'],
                'model': profile_info['model_id'],
                'application': profile_info.get('application_name')
            }
        },
        'message': 'Token JWT creado correctamente'
    }
    
    # Enviar email si se solicitó
    send_email = data.get('send_email', False)
    if send_email:
        logger.info(f"[{request_id}] Enviando token por email a {user_info['email']}")
        email_sent = email_service.send_token_email(
            recipient_email=user_info['email'],
            recipient_name=user_info.get('person', user_info['email']),
            token=token_data['jwt'],
            token_info=result['token']
        )
        
        if email_sent:
            result['message'] += ' Email enviado correctamente.'
            result['email_sent'] = True
            logger.info(f"[{request_id}] Email enviado exitosamente")
        else:
            result['message'] += ' Advertencia: No se pudo enviar el email.'
            result['email_sent'] = False
            logger.warning(f"[{request_id}] No se pudo enviar el email")
    else:
        result['email_sent'] = False
    
    return result


def handle_validate_token(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Validar token JWT"""
    logger.info(f"[{request_id}] Validando token JWT")
    
    token = body.get('token')
    
    if not token:
        raise ValueError('El parámetro "token" es requerido')
    
    try:
        # Validar firma y expiración del token
        payload = jwt_service.validate_token(token)
        
        # Calcular hash del token
        token_hash = jwt_service._calculate_hash(token)
        
        # Verificar si el token existe en BD y no está revocado
        token_record = database_service.get_token_by_jti(payload['jti'])
        
        if not token_record:
            return {
                'valid': False,
                'reason': 'Token no encontrado en la base de datos',
                'payload': payload
            }
        
        if token_record.get('is_revoked'):
            return {
                'valid': False,
                'reason': 'Token revocado',
                'revoked_at': token_record.get('revoked_at'),
                'revocation_reason': token_record.get('revocation_reason'),
                'payload': payload
            }
        
        # Verificar hash del token
        if not jwt_service.verify_token_hash(token, token_record['token_hash']):
            return {
                'valid': False,
                'reason': 'Hash del token no coincide',
                'payload': payload
            }
        
        # Token válido
        return {
            'valid': True,
            'payload': payload,
            'token_info': {
                'token_id': token_record['token_id'],
                'user_id': token_record['user_id'],
                'email': token_record['email'],
                'profile_id': token_record['application_profile_id'],
                'issued_at': token_record['created_at'],
                'expires_at': token_record['expires_at']
            },
            'message': 'Token válido'
        }
        
    except jwt.ExpiredSignatureError:
        logger.warning(f"[{request_id}] Token expirado")
        # Decodificar sin validar para obtener info
        payload = jwt_service.decode_token_without_validation(token)
        return {
            'valid': False,
            'reason': 'Token expirado',
            'payload': payload
        }
    
    except jwt.InvalidTokenError as e:
        logger.error(f"[{request_id}] Token inválido: {e}")
        return {
            'valid': False,
            'reason': f'Token inválido: {str(e)}'
        }
    
    except Exception as e:
        logger.error(f"[{request_id}] Error validando token: {e}")
        raise


def handle_revoke_token(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Revocar token JWT"""
    logger.info(f"[{request_id}] Revocando token")

    token_id = body.get('token_id')
    reason = body.get('reason', 'No especificada')

    # Obtener info del token ANTES de revocarlo (para auditoría)
    token_info = database_service.get_token(token_id)

    # Revocar en BD
    result = database_service.revoke_token(token_id, reason)

    # Registrar en auditoría
    database_service.log_audit(
        operation_type='REVOKE_TOKEN',
        resource_type='jwt_token',
        resource_id=token_id,
        cognito_user_id=token_info.get('cognito_user_id'),
        cognito_email=token_info.get('cognito_email'),
        new_value={'revoked': True, 'reason': reason},
        request_id=request_id
    )
    
    return {
        'success': True,
        'token': result,
        'message': 'Token revocado correctamente'
    }


def handle_restore_token(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Restaurar token revocado"""
    logger.info(f"[{request_id}] Restaurando token")
    
    token_id = body.get('token_id')
    
    # Obtener info del token ANTES de restaurarlo (para auditoría)
    token_info = database_service.get_token(token_id)
    
    # Restaurar en BD
    result = database_service.restore_token(token_id)
    
    # Registrar en auditoría
    database_service.log_audit(
        operation_type='RESTORE_TOKEN',
        resource_type='jwt_token',
        resource_id=token_id,
        cognito_user_id=token_info.get('cognito_user_id'),
        cognito_email=token_info.get('cognito_email'),
        new_value={'revoked': False, 'restored': True},
        request_id=request_id
    )
    
    return {
        'success': True,
        'token': result,
        'message': 'Token restored successfully'
    }


def handle_delete_token(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Eliminar token permanentemente"""
    logger.info(f"[{request_id}] Eliminando token")
    
    token_id = body.get('token_id')
    
    # Obtener info antes de eliminar
    token_info = database_service.get_token(token_id)
    
    # Eliminar de BD
    database_service.delete_token(token_id)
    
    # Registrar en auditoría
    database_service.log_audit(
        operation_type='DELETE_TOKEN',
        resource_type='jwt_token',
        resource_id=token_id,
        cognito_user_id=token_info.get('cognito_user_id'),
        cognito_email=token_info.get('cognito_email'),
        previous_value=token_info,
        request_id=request_id
    )
    
    return {
        'success': True,
        'message': 'Token eliminado permanentemente de la base de datos'
    }


# ============================================================================
# HANDLERS DE OPERACIONES - PERFILES Y GRUPOS
# ============================================================================

def handle_list_profiles(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Listar perfiles de inferencia"""
    logger.info(f"[{request_id}] Listando perfiles")
    
    filters = body.get('filters', {})
    
    result = database_service.list_profiles(
        application_id=filters.get('application_id'),
        is_active=filters.get('is_active', True)
    )
    
    return result


def handle_list_groups(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Listar grupos de Cognito"""
    logger.info(f"[{request_id}] Listando grupos")
    
    result = cognito_service.list_groups()
    
    return result


def handle_get_config(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Obtener configuración del sistema"""
    logger.info(f"[{request_id}] Obteniendo configuración")
    logger.info(f"[{request_id}] Llamando a database_service.get_config()")
    
    result = database_service.get_config()
    
    logger.info(f"[{request_id}] Configuración obtenida exitosamente")
    return result


# ============================================================================
# HANDLERS DE OPERACIONES - PERMISOS
# ============================================================================

def handle_assign_app_permission(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Asignar permiso de aplicación a un usuario"""
    logger.info(f"[{request_id}] Asignando permiso de aplicación")
    
    data = body.get('data', {})
    user_id = data['user_id']
    user_email = data['user_email']
    app_id = data['application_id']
    permission_type_id = data['permission_type_id']
    duration_days = data.get('duration_days')
    
    # Asignar permiso
    result = permissions_service.assign_app_permission(
        user_id=user_id,
        user_email=user_email,
        app_id=app_id,
        permission_type_id=permission_type_id,
        duration_days=duration_days
    )
    
    # Registrar en auditoría
    database_service.log_audit(
        operation_type='ASSIGN_APP_PERMISSION',
        resource_type='app_permission',
        resource_id=result['permission']['permission_id'],
        cognito_user_id=user_id,
        cognito_email=user_email,
        new_value=result['permission'],
        request_id=request_id
    )
    
    return result


def handle_assign_module_permission(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Asignar permiso de módulo a un usuario"""
    logger.info(f"[{request_id}] Asignando permiso de módulo")
    
    data = body.get('data', {})
    user_id = data['user_id']
    user_email = data['user_email']
    module_id = data['module_id']
    permission_type_id = data['permission_type_id']
    duration_days = data.get('duration_days')
    
    # Asignar permiso
    result = permissions_service.assign_module_permission(
        user_id=user_id,
        user_email=user_email,
        module_id=module_id,
        permission_type_id=permission_type_id,
        duration_days=duration_days
    )
    
    # Registrar en auditoría
    database_service.log_audit(
        operation_type='ASSIGN_MODULE_PERMISSION',
        resource_type='module_permission',
        resource_id=result['permission']['permission_id'],
        cognito_user_id=user_id,
        cognito_email=user_email,
        new_value=result['permission'],
        request_id=request_id
    )
    
    return result


def handle_revoke_app_permission(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Revocar permiso de aplicación"""
    logger.info(f"[{request_id}] Revocando permiso de aplicación")
    
    user_id = body.get('user_id')
    app_id = body.get('application_id')
    
    # Revocar permiso
    result = permissions_service.revoke_app_permission(user_id, app_id)
    
    # Registrar en auditoría
    database_service.log_audit(
        operation_type='REVOKE_APP_PERMISSION',
        resource_type='app_permission',
        resource_id=result['permission_id'],
        cognito_user_id=user_id,
        cognito_email=None,  # No disponible en este contexto
        new_value={'revoked': True},
        request_id=request_id
    )
    
    return result


def handle_revoke_module_permission(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Revocar permiso de módulo"""
    logger.info(f"[{request_id}] Revocando permiso de módulo")
    
    user_id = body.get('user_id')
    module_id = body.get('module_id')
    
    # Revocar permiso
    result = permissions_service.revoke_module_permission(user_id, module_id)
    
    # Registrar en auditoría
    database_service.log_audit(
        operation_type='REVOKE_MODULE_PERMISSION',
        resource_type='module_permission',
        resource_id=result['permission_id'],
        cognito_user_id=user_id,
        cognito_email=None,  # No disponible en este contexto
        new_value={'revoked': True},
        request_id=request_id
    )
    
    return result


def handle_get_user_permissions(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Obtener permisos de un usuario"""
    logger.info(f"[{request_id}] Obteniendo permisos de usuario")
    
    user_id = body.get('user_id')
    
    result = permissions_service.get_user_permissions(user_id)
    
    return result


def handle_list_all_permissions(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Listar todos los permisos del sistema"""
    logger.info(f"[{request_id}] Listando todos los permisos")
    
    result = permissions_service.list_all_permissions()
    
    return result


def handle_list_permission_types(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Listar tipos de permisos"""
    logger.info(f"[{request_id}] Listando tipos de permisos")
    
    result = permissions_service.list_permission_types()
    
    return result


def handle_list_applications(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Listar aplicaciones"""
    logger.info(f"[{request_id}] Listando aplicaciones")
    
    result = permissions_service.list_applications()
    
    return result


def handle_list_modules(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Listar módulos"""
    logger.info(f"[{request_id}] Listando módulos")
    
    app_id = body.get('application_id')
    
    result = permissions_service.list_modules(app_id)
    
    return result
