"""
Auth Service
============
Servicio principal de autenticación que orquesta el flujo de login y verificación
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from shared.services.cognito_service import CognitoService
from shared.services.database_service import DatabaseService
from shared.services.permissions_service import PermissionsService
from shared.services.jwt_service import JWTService
from shared.logging import get_logger
import config

logger = logging.getLogger()


class AuthService:
    """Servicio de autenticación centralizado"""
    
    def __init__(self):
        """Inicializar servicios"""
        # Configurar variables de entorno para los servicios
        os.environ['COGNITO_USER_POOL_ID'] = config.COGNITO_USER_POOL_ID
        os.environ['AWS_REGION'] = config.AWS_REGION
        os.environ['DB_SECRET_NAME'] = config.DB_SECRET_NAME
        os.environ['JWT_SECRET_NAME'] = config.JWT_SECRET_NAME
        
        self.cognito_service = CognitoService()
        self.database_service = DatabaseService()
        self.permissions_service = PermissionsService()
        self.jwt_service = JWTService()
        
        # Inicializar AMS Logger
        self.ams_logger = get_logger()
    
    def login(self, email: str, password: str, new_password: str = None, required_app_id: str = None) -> Dict[str, Any]:
        """
        Autenticar usuario y generar token con permisos
        
        Args:
            email: Email del usuario
            password: Contraseña
            new_password: Nueva contraseña (opcional, para cambio de contraseña temporal)
            required_app_id: ID de la aplicación requerida (opcional, para validar permisos específicos)
            
        Returns:
            Dict con token y datos del usuario
            
        Raises:
            ValueError: Si las credenciales son inválidas o no tiene permisos
            Exception: Si hay un error en el proceso
        """
        logger.info(f"Iniciando login para usuario: {email}")
        if required_app_id:
            logger.info(f"Validación de permiso requerida para aplicación: {required_app_id}")
        
        # Log estructurado: Intento de login
        self.ams_logger.info(
            "AUTH_LOGIN_ATTEMPT",
            "Usuario intentando autenticarse",
            cognito_email=email,
            required_app_id=required_app_id
        )
        
        try:
            # 1. Autenticar con Cognito usando InitiateAuth
            cognito_response = self._authenticate_with_cognito(email, password, new_password)
            
            # 2. Extraer información del usuario
            user_id = cognito_response.get('user_id')
            user_attributes = cognito_response.get('attributes', {})
            groups = cognito_response.get('groups', [])
            
            logger.info(f"Usuario autenticado en Cognito: {user_id}")
            
            # Log estructurado: Autenticación Cognito exitosa
            self.ams_logger.info(
                "AUTH_COGNITO_SUCCESS",
                "Usuario autenticado exitosamente en Cognito",
                cognito_user_id=user_id,
                cognito_email=email,
                groups_count=len(groups)
            )
            
            # 3. Obtener permisos del usuario desde la base de datos
            try:
                permissions_data = self.permissions_service.get_user_permissions(user_id)
                permissions = permissions_data.get('permissions', [])
                logger.info(f"Permisos obtenidos: {len(permissions)} permisos encontrados")
                
                # Log estructurado: Permisos cargados
                self.ams_logger.info(
                    "AUTH_PERMISSIONS_LOADED",
                    "Permisos de usuario cargados desde base de datos",
                    cognito_user_id=user_id,
                    permissions_count=len(permissions)
                )
                
                # Convertir datetime a strings para evitar errores de serialización
                permissions = self._serialize_datetime_fields(permissions)
            except Exception as e:
                logger.warning(f"Error obteniendo permisos, continuando sin permisos: {e}")
                permissions = []
            
            # 3.1. Validar permiso específico de aplicación si se requiere
            # IMPORTANTE: Solo validar permisos si NO es un cambio de contraseña temporal
            # Durante el cambio de contraseña, permitir que el usuario complete el proceso
            # La validación de permisos se hará en el siguiente login con la nueva contraseña
            if required_app_id and not new_password:
                has_permission = self._validate_app_permission(permissions, required_app_id, user_id)
                if not has_permission:
                    logger.warning(f"Usuario {email} no tiene permisos para la aplicación {required_app_id}")
                    raise ValueError(f'INSUFFICIENT_PERMISSIONS:{required_app_id}')
                logger.info(f"Usuario {email} tiene permisos válidos para la aplicación {required_app_id}")
            elif required_app_id and new_password:
                logger.info(f"Cambio de contraseña temporal detectado, omitiendo validación de permisos para {email}")
            
            # 4. Preparar datos del usuario
            user_data = {
                'userId': user_id,
                'email': email,
                'name': user_attributes.get('name', email),
                'groups': groups
            }
            
            # 5. Generar token JWT personalizado (1 hora de validez)
            # No incluimos permisos completos en el token, solo validamos acceso
            token_payload = {
                'sub': user_id,
                'email': email,
                'name': user_data['name'],
                'groups': groups,
                'iat': datetime.utcnow(),
                'exp': datetime.utcnow() + timedelta(hours=config.JWT_EXPIRATION_HOURS)
            }
            
            # Generar el token usando el servicio JWT
            token_data = self._generate_custom_token(token_payload)
            
            # 6. Preparar respuesta con permisos serializados
            result = {
                'success': True,
                'token': token_data['jwt'],
                'user': user_data,
                'permissions': permissions,  # Incluir permisos (ya serializados)
                'expiresAt': token_data['expires_at']
            }
            
            logger.info(f"Login exitoso para {email}")
            
            # Log estructurado: Login exitoso
            self.ams_logger.info(
                "AUTH_LOGIN_SUCCESS",
                "Login completado exitosamente",
                cognito_user_id=user_id,
                cognito_email=email,
                permissions_count=len(permissions),
                token_expires_at=token_data['expires_at']
            )
            
            return result
            
        except ValueError as e:
            logger.error(f"Error de validación en login: {e}")
            
            # Log estructurado: Login fallido
            self.ams_logger.error(
                "AUTH_LOGIN_FAILED",
                "Login fallido por error de validación",
                cognito_email=email,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise
        except Exception as e:
            logger.error(f"Error inesperado en login: {e}", exc_info=True)
            
            # Log estructurado: Error del sistema
            self.ams_logger.error(
                "AUTH_LOGIN_FAILED",
                "Login fallido por error del sistema",
                cognito_email=email,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise Exception(f"Error en el proceso de autenticación: {str(e)}")
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verificar y decodificar token JWT
        
        Args:
            token: Token JWT a verificar
            
        Returns:
            Dict con información del token
        """
        logger.info("Verificando token JWT")
        
        # Log estructurado: Intento de verificación
        self.ams_logger.info(
            "AUTH_TOKEN_VERIFY_ATTEMPT",
            "Verificando token JWT"
        )
        
        try:
            # Validar y decodificar token
            payload = self.jwt_service.validate_token(token, audiences=['auth-login'])
            
            # Preparar respuesta
            result = {
                'valid': True,
                'user': {
                    'userId': payload['sub'],
                    'email': payload['email'],
                    'name': payload.get('name', payload['email']),
                    'groups': payload.get('groups', [])
                },
                'permissions': payload.get('permissions', []),
                'expiresAt': datetime.fromtimestamp(payload['exp']).isoformat() + 'Z'
            }
            
            logger.info(f"Token válido para usuario {payload['email']}")
            
            # Log estructurado: Verificación exitosa
            self.ams_logger.info(
                "AUTH_TOKEN_VERIFY_SUCCESS",
                "Token verificado exitosamente",
                cognito_user_id=payload['sub'],
                cognito_email=payload['email']
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Token inválido: {e}")
            
            # Log estructurado: Verificación fallida
            self.ams_logger.warning(
                "AUTH_TOKEN_VERIFY_FAILED",
                "Token inválido o expirado",
                error_type=type(e).__name__,
                error_message=str(e)
            )
            
            return {
                'valid': False,
                'error': str(e)
            }
    
    def _authenticate_with_cognito(self, email: str, password: str, new_password: str = None) -> Dict[str, Any]:
        """
        Autenticar usuario con Cognito usando InitiateAuth
        
        Args:
            email: Email del usuario
            password: Contraseña
            new_password: Nueva contraseña (opcional, para cambio de contraseña temporal)
            
        Returns:
            Dict con información del usuario autenticado
            
        Raises:
            ValueError: Si las credenciales son inválidas o se requiere nueva contraseña
        """
        import boto3
        from botocore.exceptions import ClientError
        
        client = boto3.client('cognito-idp', region_name=config.AWS_REGION)
        
        try:
            # Autenticar con USER_PASSWORD_AUTH
            response = client.initiate_auth(
                ClientId=config.COGNITO_CLIENT_ID,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': email,
                    'PASSWORD': password
                }
            )
            
            # Verificar si requiere cambio de contraseña
            if response.get('ChallengeName') == 'NEW_PASSWORD_REQUIRED':
                logger.info(f"Usuario {email} requiere cambio de contraseña temporal")
                
                # Si no se proporcionó nueva contraseña, lanzar excepción especial
                if not new_password:
                    raise ValueError('NEW_PASSWORD_REQUIRED')
                
                # Cambiar la contraseña temporal por la nueva proporcionada
                response = client.respond_to_auth_challenge(
                    ClientId=config.COGNITO_CLIENT_ID,
                    ChallengeName='NEW_PASSWORD_REQUIRED',
                    Session=response['Session'],
                    ChallengeResponses={
                        'USERNAME': email,
                        'NEW_PASSWORD': new_password
                    }
                )
                logger.info(f"Contraseña temporal cambiada exitosamente para {email}")
            
            # Extraer tokens
            auth_result = response.get('AuthenticationResult', {})
            id_token = auth_result.get('IdToken')
            access_token = auth_result.get('AccessToken')
            
            if not id_token:
                raise ValueError('No se recibió token de identidad de Cognito')
            
            # Obtener información del usuario
            user_response = client.get_user(AccessToken=access_token)
            
            # Extraer atributos
            attributes = {attr['Name']: attr['Value'] for attr in user_response.get('UserAttributes', [])}
            
            # Obtener grupos del usuario
            try:
                groups_response = client.admin_list_groups_for_user(
                    UserPoolId=config.COGNITO_USER_POOL_ID,
                    Username=user_response['Username']
                )
                groups = [group['GroupName'] for group in groups_response.get('Groups', [])]
            except Exception:
                groups = []
            
            return {
                'user_id': user_response['Username'],
                'attributes': attributes,
                'groups': groups,
                'cognito_tokens': {
                    'id_token': id_token,
                    'access_token': access_token
                }
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NotAuthorizedException':
                raise ValueError('Email o contraseña incorrectos')
            elif error_code == 'UserNotFoundException':
                raise ValueError('Usuario no encontrado')
            elif error_code == 'UserNotConfirmedException':
                raise ValueError('Usuario no confirmado')
            else:
                raise ValueError(f'Error de autenticación: {e.response["Error"]["Message"]}')
    
    def forgot_password(self, email: str) -> Dict[str, Any]:
        """
        Resetear contraseña de usuario (forzar cambio)
        
        Args:
            email: Email del usuario
            
        Returns:
            Dict con resultado de la operación
        """
        import boto3
        from botocore.exceptions import ClientError
        import secrets
        import string
        
        logger.info(f"Reseteando contraseña para usuario: {email}")
        
        # Log estructurado: Intento de reset de contraseña
        self.ams_logger.info(
            "AUTH_PASSWORD_RESET_ATTEMPT",
            "Iniciando proceso de reset de contraseña",
            cognito_email=email
        )
        
        client = boto3.client('cognito-idp', region_name=config.AWS_REGION)
        
        try:
            # Generar contraseña temporal segura
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            temp_password = ''.join(secrets.choice(alphabet) for _ in range(12))
            
            # Asegurar que cumple requisitos (al menos una mayúscula, minúscula, número y especial)
            temp_password = (
                secrets.choice(string.ascii_uppercase) +
                secrets.choice(string.ascii_lowercase) +
                secrets.choice(string.digits) +
                secrets.choice("!@#$%^&*") +
                temp_password[4:]
            )
            
            # Resetear contraseña del usuario en Cognito
            client.admin_set_user_password(
                UserPoolId=config.COGNITO_USER_POOL_ID,
                Username=email,
                Password=temp_password,
                Permanent=False  # Forzar cambio en próximo login
            )
            
            logger.info(f"Contraseña reseteada exitosamente para {email}")
            
            # Log estructurado: Reset exitoso
            self.ams_logger.info(
                "AUTH_PASSWORD_RESET_SUCCESS",
                "Contraseña reseteada exitosamente",
                cognito_email=email
            )
            
            # TODO: Aquí deberías enviar un email con la contraseña temporal
            # Por ahora, la devolvemos en la respuesta (solo para desarrollo)
            
            return {
                'success': True,
                'message': 'Contraseña reseteada exitosamente. Se ha enviado una contraseña temporal a tu email.',
                'temporary_password': temp_password  # SOLO PARA DESARROLLO - Eliminar en producción
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'UserNotFoundException':
                # Log estructurado: Usuario no encontrado (no revelar en respuesta)
                self.ams_logger.warning(
                    "AUTH_PASSWORD_RESET_USER_NOT_FOUND",
                    "Usuario no encontrado en reset de contraseña",
                    cognito_email=email
                )
                
                # Por seguridad, no revelar si el usuario existe o no
                return {
                    'success': True,
                    'message': 'Si el email existe en nuestro sistema, recibirás una contraseña temporal.'
                }
            else:
                logger.error(f"Error reseteando contraseña: {e}")
                
                # Log estructurado: Error en reset
                self.ams_logger.error(
                    "AUTH_PASSWORD_RESET_FAILED",
                    "Error al resetear contraseña",
                    cognito_email=email,
                    error_type=error_code,
                    error_message=e.response['Error']['Message']
                )
                
                raise ValueError(f'Error al resetear contraseña: {e.response["Error"]["Message"]}')
    
    def _serialize_datetime_fields(self, permissions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convertir campos datetime a strings ISO format
        
        Args:
            permissions: Lista de permisos con posibles datetime
            
        Returns:
            Lista de permisos con datetime convertidos a strings
        """
        serialized = []
        for perm in permissions:
            perm_copy = perm.copy()
            # Convertir granted_at y expires_at si existen
            if 'granted_at' in perm_copy and perm_copy['granted_at']:
                if isinstance(perm_copy['granted_at'], datetime):
                    perm_copy['granted_at'] = perm_copy['granted_at'].isoformat() + 'Z'
            if 'expires_at' in perm_copy and perm_copy['expires_at']:
                if isinstance(perm_copy['expires_at'], datetime):
                    perm_copy['expires_at'] = perm_copy['expires_at'].isoformat() + 'Z'
            serialized.append(perm_copy)
        return serialized
    
    def _validate_app_permission(self, permissions: List[Dict[str, Any]], required_app_id: str, user_id: str) -> bool:
        """
        Validar que el usuario tenga permiso activo para una aplicación específica
        
        Args:
            permissions: Lista de permisos del usuario
            required_app_id: ID de la aplicación requerida
            user_id: ID del usuario (para logging)
            
        Returns:
            True si tiene permiso válido, False en caso contrario
        """
        logger.info(f"Validando permiso para aplicación {required_app_id}")
        
        # Buscar permisos de aplicación activos y no expirados
        app_permissions = [
            perm for perm in permissions
            if perm.get('scope') == 'application'
            and perm.get('resource_id') == required_app_id
            and perm.get('status') == 'active'
            and perm.get('is_active') is True
        ]
        
        if not app_permissions:
            logger.warning(f"No se encontraron permisos activos para la aplicación {required_app_id}")
            return False
        
        # Log del permiso encontrado
        perm = app_permissions[0]
        logger.info(f"Permiso encontrado: {perm.get('permission_type')} (nivel {perm.get('permission_level')})")
        
        return True
    
    def _generate_custom_token(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generar token JWT personalizado
        
        Args:
            payload: Datos a incluir en el token
            
        Returns:
            Dict con token y metadata
        """
        # Convertir datetime a timestamp
        if isinstance(payload.get('iat'), datetime):
            payload['iat'] = int(payload['iat'].timestamp())
        if isinstance(payload.get('exp'), datetime):
            exp_datetime = payload['exp']
            payload['exp'] = int(exp_datetime.timestamp())
        else:
            exp_datetime = datetime.fromtimestamp(payload['exp'])
        
        # Añadir issuer y audience
        payload['iss'] = 'auth-lambda'
        payload['aud'] = ['auth-login']
        
        # Generar token usando el servicio JWT
        import jwt
        secret_key = self.jwt_service._get_secret_key()
        token = jwt.encode(payload, secret_key, algorithm=self.jwt_service.algorithm)
        
        return {
            'jwt': token,
            'issued_at': datetime.utcnow().isoformat() + 'Z',
            'expires_at': exp_datetime.isoformat() + 'Z'
        }