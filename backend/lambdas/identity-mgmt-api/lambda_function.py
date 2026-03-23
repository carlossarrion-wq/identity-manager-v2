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
from services.proxy_usage_service import ProxyUsageService
from services.token_regeneration_service import TokenRegenerationService
from utils.validators import validate_request
from utils.response_builder import build_response, build_error_response

# Inicializar servicios
cognito_service = None
database_service = None
jwt_service = None
email_service = None
permissions_service = None
proxy_usage_service = None
token_regeneration_service = None


def initialize_services():
    """Inicializar servicios en el primer invocación (lazy loading)"""
    global cognito_service, database_service, jwt_service, email_service, permissions_service, proxy_usage_service, token_regeneration_service
    
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
    if proxy_usage_service is None:
        proxy_usage_service = ProxyUsageService(database_service)
    if token_regeneration_service is None:
        token_regeneration_service = TokenRegenerationService(database_service, cognito_service, email_service)


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
        # ============================================================
        # VALIDACIÓN DE AUTENTICACIÓN Y AUTORIZACIÓN
        # ============================================================
        
        # Extraer contexto del Authorizer custom
        authorizer_context = event.get('requestContext', {}).get('authorizer', {})
        
        if not authorizer_context or 'sub' not in authorizer_context:
            logger.warning(f"[{request_id}] No authorizer context found - authentication required")
            return build_error_response(
                'UNAUTHORIZED',
                'Authentication required',
                401
            )
        
        # Extraer información del usuario del contexto del authorizer
        user_id = authorizer_context.get('sub')
        user_email = authorizer_context.get('email')
        user_name = user_email  # El authorizer no pasa 'name', solo email
        
        logger.info(f"[{request_id}] Request from user: {user_email} (ID: {user_id})")
        
        # DEBUG: Log del contexto completo del authorizer
        logger.info(f"[{request_id}] Authorizer context keys: {list(authorizer_context.keys())}")
        logger.info(f"[{request_id}] Authorizer context: {json.dumps(authorizer_context)}")
        
        # Parsear app_permissions del contexto del authorizer (vienen como string JSON)
        app_permissions_str = authorizer_context.get('app_permissions', '[]')
        logger.info(f"[{request_id}] app_permissions_str type: {type(app_permissions_str)}, value: {app_permissions_str}")
        
        try:
            app_permissions = json.loads(app_permissions_str) if isinstance(app_permissions_str, str) else app_permissions_str
            logger.info(f"[{request_id}] Parsed app_permissions: {app_permissions}")
        except json.JSONDecodeError as e:
            logger.error(f"[{request_id}] Invalid app_permissions format in authorizer context: {e}")
            app_permissions = []
        
        # Verificar permiso de identity-mgmt
        identity_mgmt_perm = None
        for perm in app_permissions:
            if perm.get('app_name') == 'identity-mgmt':
                identity_mgmt_perm = perm
                break
        
        if not identity_mgmt_perm:
            logger.warning(f"[{request_id}] User {user_email} has no identity-mgmt permissions")
            return build_error_response(
                'FORBIDDEN',
                'You do not have permissions to access Identity Manager',
                403
            )
        
        permission_level = identity_mgmt_perm.get('permission_level', 0)
        permission_type = identity_mgmt_perm.get('permission_type', 'read')
        
        logger.info(f"[{request_id}] User has {permission_type} permission (level {permission_level})")
        
        # ============================================================
        # PROCESAMIENTO DE LA OPERACIÓN
        # ============================================================
        
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
        
        # Validar nivel de permiso según operación
        OPERATION_REQUIREMENTS = {
            # Operaciones de lectura - nivel 10 (read)
            'list_users': 10,
            'list_tokens': 10,
            'list_profiles': 10,
            'list_groups': 10,
            'get_user_permissions': 10,
            'list_all_permissions': 10,
            'list_permission_types': 10,
            'list_applications': 10,
            'list_modules': 10,
            'get_config': 10,
            'get_proxy_usage_summary': 10,
            'get_proxy_usage_by_hour': 10,
            'get_proxy_usage_by_team': 10,
            'get_proxy_usage_by_day': 10,
            'get_proxy_usage_response_status': 10,
            'get_proxy_usage_trend': 10,
            'get_proxy_usage_by_user': 10,
            'get_available_teams': 10,
            'get_user_quotas_today': 10,
            
            # Operaciones de escritura - nivel 50 (write)
            'create_user': 50,
            'create_token': 50,
            'revoke_token': 50,
            'restore_token': 50,
            'assign_app_permission': 50,
            'assign_module_permission': 50,
            'revoke_app_permission': 50,
            'revoke_module_permission': 50,
            'regenerate_token': 50,
            
            # Operaciones administrativas - nivel 100 (admin)
            'delete_user': 100,
            'delete_token': 100,
            'reset_password': 100,
            'block_user': 100,
            'unblock_user': 100,
            'set_admin_safe': 100,
        }
        
        required_level = OPERATION_REQUIREMENTS.get(operation, 100)  # Por defecto requiere admin
        
        if permission_level < required_level:
            logger.warning(
                f"[{request_id}] User {user_email} attempted {operation} "
                f"with insufficient permissions (has {permission_level}, needs {required_level})"
            )
            return build_error_response(
                'FORBIDDEN',
                f'Operation "{operation}" requires permission level {required_level}. You have level {permission_level}.',
                403
            )
        
        logger.info(f"[{request_id}] Operation {operation} authorized for {user_email}")
        
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
        'list_users_light': handle_list_users_light,
        'create_user': handle_create_user,
        'delete_user': handle_delete_user,
        
        # Operaciones de tokens
        'list_tokens': handle_list_tokens,
        'create_token': handle_create_token,
        'validate_token': handle_validate_token,
        'revoke_token': handle_revoke_token,
        'restore_token': handle_restore_token,
        'delete_token': handle_delete_token,
        'regenerate_token': handle_regenerate_token,
        
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
        
        # Operaciones de uso del proxy
        'get_proxy_usage_summary': handle_get_proxy_usage_summary,
        'get_proxy_usage_by_hour': handle_get_proxy_usage_by_hour,
        'get_proxy_usage_by_team': handle_get_proxy_usage_by_team,
        'get_proxy_usage_by_day': handle_get_proxy_usage_by_day,
        'get_proxy_usage_response_status': handle_get_proxy_usage_response_status,
        'get_proxy_usage_trend': handle_get_proxy_usage_trend,
        'get_proxy_usage_by_user': handle_get_proxy_usage_by_user,
        'get_available_teams': handle_get_available_teams,
        
        # Operaciones de cuotas de usuarios
        'get_user_quotas_today': handle_get_user_quotas_today,
        'block_user': handle_block_user,
        'unblock_user': handle_unblock_user,
        'set_admin_safe': handle_set_admin_safe,
        
        # Operaciones de reset de contraseña
        'reset_password': handle_reset_password,
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


def handle_list_users_light(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """
    Listar usuarios de Cognito (versión LIGERA y RÁPIDA)
    
    Solo devuelve: user_id, email, person, status
    NO obtiene grupos (elimina N llamadas adicionales a Cognito)
    Ideal para dropdowns, selects, y listados simples
    """
    logger.info(f"[{request_id}] Listando usuarios (LIGHT mode)")
    
    filters = body.get('filters', {})
    pagination = body.get('pagination', {})
    
    result = cognito_service.list_users_light(
        group=filters.get('group'),
        status=filters.get('status'),
        limit=pagination.get('limit'),
        pagination_token=pagination.get('pagination_token')
    )
    
    logger.info(f"[{request_id}] Usuarios obtenidos (LIGHT): {result['total_count']}")
    
    return result


def handle_create_user(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Crear nuevo usuario en Cognito"""
    logger.info(f"[{request_id}] Creando usuario")
    
    data = body.get('data', {})
    email = data['email'].lower()  # Normalizar email a minúsculas
    
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
    
    # Si no se especifica limit en pagination, no pasar ninguno (devuelve todos)
    limit = pagination.get('limit') if 'limit' in pagination else None
    
    result = database_service.list_tokens(
        user_id=filters.get('user_id'),
        status=filters.get('status', 'all'),
        profile_id=filters.get('profile_id'),
        limit=limit,
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


def handle_regenerate_token(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """
    Regenerar token JWT expirado automáticamente
    
    Este endpoint es llamado por el proxy cuando detecta un token expirado
    y el usuario tiene habilitada la regeneración automática.
    """
    logger.info(f"[{request_id}] Regenerando token expirado")
    
    data = body.get('data', {})
    expired_token_jti = data.get('expired_token_jti')
    user_id = data.get('user_id')
    client_ip = data.get('client_ip')
    user_agent = data.get('user_agent')
    
    if not expired_token_jti or not user_id:
        raise ValueError('Los parámetros "expired_token_jti" y "user_id" son requeridos')
    
    # Llamar al servicio de regeneración
    result = token_regeneration_service.regenerate_expired_token(
        expired_token_jti=expired_token_jti,
        user_id=user_id,
        client_ip=client_ip,
        user_agent=user_agent
    )
    
    # Si la regeneración fue exitosa, registrar en auditoría
    if result.get('success'):
        database_service.log_audit(
            operation_type='REGENERATE_TOKEN',
            resource_type='jwt_token',
            resource_id=result['new_token_jti'],
            cognito_user_id=user_id,
            cognito_email=None,  # Se obtiene del token info
            new_value={
                'new_jti': result['new_token_jti'],
                'old_jti': expired_token_jti,
                'email_sent': result.get('email_sent', False)
            },
            request_id=request_id
        )
        
        logger.info(f"[{request_id}] Token regenerado exitosamente: {result['new_token_jti']}")
    else:
        logger.warning(f"[{request_id}] Regeneración fallida: {result.get('error', 'unknown')}")
    
    return result


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
    
    # Determinar tipo de operación según el action devuelto
    # Si action es 'updated' y el permiso estaba revocado, es una restauración
    operation_type = 'RESTORE_APP_PERMISSION' if result['action'] == 'updated' else 'ASSIGN_APP_PERMISSION'
    
    # Registrar en auditoría
    database_service.log_audit(
        operation_type=operation_type,
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
    
    # Determinar tipo de operación según el action devuelto
    # Si action es 'updated' y el permiso estaba revocado, es una restauración
    operation_type = 'RESTORE_MODULE_PERMISSION' if result['action'] == 'updated' else 'ASSIGN_MODULE_PERMISSION'
    
    # Registrar en auditoría
    database_service.log_audit(
        operation_type=operation_type,
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
    
    # Obtener permisos del usuario para extraer el email
    user_permissions = permissions_service.get_user_permissions(user_id)
    user_email = None
    if user_permissions and user_permissions.get('permissions'):
        # Buscar el email en cualquier permiso del usuario
        for perm in user_permissions['permissions']:
            if perm.get('email'):
                user_email = perm['email']
                break
    
    # Revocar permiso
    result = permissions_service.revoke_app_permission(user_id, app_id)
    
    # Registrar en auditoría
    database_service.log_audit(
        operation_type='REVOKE_APP_PERMISSION',
        resource_type='app_permission',
        resource_id=result['permission_id'],
        cognito_user_id=user_id,
        cognito_email=user_email,
        new_value={'revoked': True},
        request_id=request_id
    )
    
    return result


def handle_revoke_module_permission(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Revocar permiso de módulo"""
    logger.info(f"[{request_id}] Revocando permiso de módulo")
    
    user_id = body.get('user_id')
    module_id = body.get('module_id')
    
    # Obtener permisos del usuario para extraer el email
    user_permissions = permissions_service.get_user_permissions(user_id)
    user_email = None
    if user_permissions and user_permissions.get('permissions'):
        # Buscar el email en cualquier permiso del usuario
        for perm in user_permissions['permissions']:
            if perm.get('email'):
                user_email = perm['email']
                break
    
    # Revocar permiso
    result = permissions_service.revoke_module_permission(user_id, module_id)
    
    # Registrar en auditoría
    database_service.log_audit(
        operation_type='REVOKE_MODULE_PERMISSION',
        resource_type='module_permission',
        resource_id=result['permission_id'],
        cognito_user_id=user_id,
        cognito_email=user_email,
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


# ============================================================================
# HANDLERS DE OPERACIONES - USO DEL PROXY
# ============================================================================

def _parse_date_filter(date_str: str, is_end_date: bool = False) -> datetime:
    """
    Parse date string from filters, handling both YYYY-MM-DD and ISO formats
    
    Args:
        date_str: Date string to parse
        is_end_date: If True, set time to end of day (23:59:59)
        
    Returns:
        datetime object
    """
    if 'T' not in date_str:
        # YYYY-MM-DD format - convert to full day range
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        if is_end_date:
            return dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        else:
            return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        # ISO format with time
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))


def handle_get_proxy_usage_summary(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Obtener resumen de uso del proxy"""
    logger.info(f"[{request_id}] Obteniendo resumen de uso del proxy")
    
    filters = body.get('filters', {})
    
    # Parse dates - handle both YYYY-MM-DD and ISO format
    start_date_str = filters['start_date']
    end_date_str = filters['end_date']
    
    # If date is in YYYY-MM-DD format, convert to full day range
    if 'T' not in start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
    
    if 'T' not in end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999)
    else:
        end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
    
    logger.info(f"[{request_id}] Date range: {start_date} to {end_date}")
    
    user_id = filters.get('user_id')
    team = filters.get('team')
    
    result = proxy_usage_service.get_summary(start_date, end_date, user_id, team)
    
    return {'success': True, 'data': result}


def handle_get_proxy_usage_by_hour(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Obtener uso del proxy por hora"""
    logger.info(f"[{request_id}] Obteniendo uso por hora")
    
    filters = body.get('filters', {})
    start_date = _parse_date_filter(filters['start_date'], is_end_date=False)
    end_date = _parse_date_filter(filters['end_date'], is_end_date=True)
    team = filters.get('team')
    
    logger.info(f"[{request_id}] Date range: {start_date} to {end_date}")
    
    result = proxy_usage_service.get_usage_by_hour(start_date, end_date, team)
    
    return {'success': True, 'data': result}


def handle_get_proxy_usage_by_team(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Obtener uso del proxy por equipo"""
    logger.info(f"[{request_id}] Obteniendo uso por equipo")
    
    filters = body.get('filters', {})
    start_date = _parse_date_filter(filters['start_date'], is_end_date=False)
    end_date = _parse_date_filter(filters['end_date'], is_end_date=True)
    team = filters.get('team')
    
    logger.info(f"[{request_id}] Date range: {start_date} to {end_date}")
    
    result = proxy_usage_service.get_usage_by_team(start_date, end_date, team)
    
    return {'success': True, 'data': result}


def handle_get_proxy_usage_by_day(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Obtener uso del proxy por día"""
    logger.info(f"[{request_id}] Obteniendo uso por día")
    
    filters = body.get('filters', {})
    start_date = _parse_date_filter(filters['start_date'], is_end_date=False)
    end_date = _parse_date_filter(filters['end_date'], is_end_date=True)
    team = filters.get('team')
    
    logger.info(f"[{request_id}] Date range: {start_date} to {end_date}")
    
    result = proxy_usage_service.get_usage_by_day(start_date, end_date, team)
    
    return {'success': True, 'data': result}


def handle_get_proxy_usage_response_status(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Obtener distribución de estados de respuesta"""
    logger.info(f"[{request_id}] Obteniendo estados de respuesta")
    
    filters = body.get('filters', {})
    start_date = _parse_date_filter(filters['start_date'], is_end_date=False)
    end_date = _parse_date_filter(filters['end_date'], is_end_date=True)
    team = filters.get('team')
    
    logger.info(f"[{request_id}] Date range: {start_date} to {end_date}")
    
    result = proxy_usage_service.get_response_status(start_date, end_date, team)
    
    return {'success': True, 'data': result}


def handle_get_proxy_usage_trend(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Obtener tendencia de uso por equipo"""
    logger.info(f"[{request_id}] Obteniendo tendencia de uso")
    
    filters = body.get('filters', {})
    start_date = _parse_date_filter(filters['start_date'], is_end_date=False)
    end_date = _parse_date_filter(filters['end_date'], is_end_date=True)
    team = filters.get('team')
    
    logger.info(f"[{request_id}] Date range: {start_date} to {end_date}")
    
    result = proxy_usage_service.get_usage_trend(start_date, end_date, team)
    
    return {'success': True, 'data': result}


def handle_get_proxy_usage_by_user(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Obtener uso por usuario con paginación"""
    logger.info(f"[{request_id}] Obteniendo uso por usuario")
    
    filters = body.get('filters', {})
    pagination = body.get('pagination', {})
    
    start_date = _parse_date_filter(filters['start_date'], is_end_date=False)
    end_date = _parse_date_filter(filters['end_date'], is_end_date=True)
    page = pagination.get('page', 1)
    page_size = pagination.get('page_size', 100)
    team = filters.get('team')
    
    logger.info(f"[{request_id}] Date range: {start_date} to {end_date}")
    
    result = proxy_usage_service.get_usage_by_user(start_date, end_date, page, page_size, team)
    
    return {'success': True, 'data': result}


def handle_get_available_teams(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Obtener lista completa de equipos disponibles (sin límite)"""
    logger.info(f"[{request_id}] Obteniendo lista de equipos disponibles")
    
    result = proxy_usage_service.get_available_teams()
    
    return {'success': True, 'data': result}


# ============================================================================
# HANDLERS DE OPERACIONES - CUOTAS DE USUARIOS
# ============================================================================

def handle_get_user_quotas_today(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """
    Obtener cuotas de usuarios para el día actual
    
    Retorna información de cuotas incluyendo:
    - Usuarios con uso en el día actual
    - Peticiones realizadas hoy
    - Límite diario establecido
    - Estado (ACTIVE, BLOCKED, ADMIN_SAFE)
    - Fecha de desbloqueo si aplica
    """
    logger.info(f"[{request_id}] Obteniendo cuotas de usuarios del día actual")
    
    result = database_service.get_user_quotas_today()
    
    # build_response() ya envuelve el resultado en {success, data, timestamp}
    # por lo que solo debemos devolver el array directamente
    return result


def handle_block_user(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """
    Bloquear manualmente a un usuario hasta una fecha específica
    
    Args:
        body: Datos del request con cognito_user_id, blocked_until, block_reason, performed_by
        request_id: ID del request para logging
        
    Returns:
        Dict con información del usuario bloqueado
    """
    logger.info(f"[{request_id}] Bloqueando usuario manualmente")
    
    data = body.get('data', {})
    cognito_user_id = data.get('cognito_user_id')
    blocked_until = data.get('blocked_until')
    block_reason = data.get('block_reason')
    performed_by = data.get('performed_by')
    
    if not all([cognito_user_id, blocked_until, block_reason, performed_by]):
        raise ValueError('Los parámetros cognito_user_id, blocked_until, block_reason y performed_by son requeridos')
    
    # Bloquear usuario
    result = database_service.block_user_quota(
        cognito_user_id=cognito_user_id,
        blocked_until=blocked_until,
        block_reason=block_reason,
        performed_by=performed_by
    )
    
    # Registrar en auditoría
    database_service.log_audit(
        operation_type='BLOCK_USER_QUOTA',
        resource_type='user_quota',
        resource_id=cognito_user_id,
        cognito_user_id=cognito_user_id,
        cognito_email=result.get('cognito_email'),
        new_value={
            'status': 'BLOCKED',
            'blocked_until': blocked_until,
            'block_reason': block_reason,
            'blocked_by': performed_by
        },
        request_id=request_id
    )
    
    logger.info(f"[{request_id}] Usuario {cognito_user_id} bloqueado exitosamente")
    
    return {
        'success': True,
        'operation': 'block_user',
        'user': result
    }


def handle_unblock_user(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """
    Desbloquear manualmente a un usuario o quitar Admin-Safe
    
    Args:
        body: Datos del request con cognito_user_id, unblock_reason, performed_by
        request_id: ID del request para logging
        
    Returns:
        Dict con información del usuario desbloqueado
    """
    logger.info(f"[{request_id}] Desbloqueando usuario manualmente")
    
    data = body.get('data', {})
    cognito_user_id = data.get('cognito_user_id')
    unblock_reason = data.get('unblock_reason')
    performed_by = data.get('performed_by')
    
    if not all([cognito_user_id, unblock_reason, performed_by]):
        raise ValueError('Los parámetros cognito_user_id, unblock_reason y performed_by son requeridos')
    
    # Desbloquear usuario
    result = database_service.unblock_user_quota(
        cognito_user_id=cognito_user_id,
        unblock_reason=unblock_reason,
        performed_by=performed_by
    )
    
    # Registrar en auditoría
    database_service.log_audit(
        operation_type='UNBLOCK_USER_QUOTA',
        resource_type='user_quota',
        resource_id=cognito_user_id,
        cognito_user_id=cognito_user_id,
        cognito_email=result.get('cognito_email'),
        new_value={
            'status': 'ACTIVE',
            'previous_state': result.get('previous_state'),
            'unblock_reason': unblock_reason,
            'unblocked_by': performed_by
        },
        request_id=request_id
    )
    
    logger.info(f"[{request_id}] Usuario {cognito_user_id} desbloqueado exitosamente")
    
    return {
        'success': True,
        'operation': 'unblock_user',
        'user': result
    }


def handle_reset_password(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """
    Resetear contraseña de un usuario
    
    Args:
        body: Datos del request con user_id, new_password (optional), reason (optional), send_email
        request_id: ID del request para logging
        
    Returns:
        Dict con información del reset
    """
    logger.info(f"[{request_id}] Reseteando contraseña de usuario")
    
    data = body.get('data', {})
    user_id = data.get('user_id')
    new_password = data.get('new_password')  # Opcional
    reason = data.get('reason', 'No reason provided')
    send_email = data.get('send_email', True)
    
    if not user_id:
        raise ValueError('El parámetro user_id es requerido')
    
    # Obtener info del usuario
    user_info = cognito_service.get_user(user_id)
    
    # Resetear contraseña en Cognito
    reset_result = cognito_service.reset_user_password(
        username=user_id,
        new_password=new_password if new_password else None,
        send_email=send_email
    )
    
    # Enviar email si se solicitó
    email_sent = False
    if send_email:
        # Obtener email del usuario que realiza el reset desde el contexto
        # Por ahora usamos 'system' como default
        reset_by = 'System Administrator'
        
        email_sent = email_service.send_password_reset_email(
            recipient_email=user_info['email'],
            recipient_name=user_info.get('person', user_info['email']),
            temporary_password=reset_result.get('password', '****'),
            reset_by=reset_by,
            reason=reason if reason != 'No reason provided' else None
        )
    
    # Registrar en auditoría
    database_service.log_audit(
        operation_type='RESET_PASSWORD',
        resource_type='cognito_user',
        resource_id=user_id,
        cognito_user_id=user_id,
        cognito_email=user_info['email'],
        new_value={
            'reason': reason,
            'password_generated': reset_result.get('password_generated', False),
            'email_sent': email_sent
        },
        request_id=request_id
    )
    
    logger.info(f"[{request_id}] Contraseña reseteada exitosamente para usuario {user_id}")
    
    # Preparar respuesta
    response = {
        'success': True,
        'message': 'Password reset successfully',
        'email_sent': email_sent,
        'password_generated': reset_result.get('password_generated', False)
    }
    
    # Solo incluir password si no se envió por email
    if not send_email and reset_result.get('password'):
        response['temporary_password'] = reset_result['password']
    
    return response


def handle_set_admin_safe(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """
    Establecer protección Admin-Safe para un usuario
    
    Args:
        body: Datos del request con cognito_user_id, admin_safe_reason, performed_by
        request_id: ID del request para logging
        
    Returns:
        Dict con información del usuario protegido
    """
    logger.info(f"[{request_id}] Estableciendo Admin-Safe para usuario")
    
    data = body.get('data', {})
    cognito_user_id = data.get('cognito_user_id')
    admin_safe_reason = data.get('admin_safe_reason')
    performed_by = data.get('performed_by')
    
    if not all([cognito_user_id, admin_safe_reason, performed_by]):
        raise ValueError('Los parámetros cognito_user_id, admin_safe_reason y performed_by son requeridos')
    
    # Establecer Admin-Safe
    result = database_service.set_admin_safe_quota(
        cognito_user_id=cognito_user_id,
        admin_safe_reason=admin_safe_reason,
        performed_by=performed_by
    )
    
    # Registrar en auditoría
    database_service.log_audit(
        operation_type='SET_ADMIN_SAFE_QUOTA',
        resource_type='user_quota',
        resource_id=cognito_user_id,
        cognito_user_id=cognito_user_id,
        cognito_email=result.get('cognito_email'),
        new_value={
            'status': 'ADMIN_SAFE',
            'previous_state': result.get('previous_state'),
            'admin_safe_reason': admin_safe_reason,
            'administrative_safe_set_by': performed_by
        },
        request_id=request_id
    )
    
    logger.info(f"[{request_id}] Usuario {cognito_user_id} establecido como Admin-Safe exitosamente")
    
    return {
        'success': True,
        'operation': 'set_admin_safe',
        'user': result
    }
