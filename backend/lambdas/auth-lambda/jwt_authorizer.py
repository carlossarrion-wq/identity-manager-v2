"""
JWT Custom Authorizer for API Gateway
======================================
Valida el JWT custom generado por /auth/login que contiene app_permissions
"""

import json
import jwt
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Secret para validar JWT (debe coincidir con el usado en auth_service.py)
JWT_SECRET = os.environ.get('JWT_SECRET_NAME', 'identity-mgmt-jwt-secret')


def lambda_handler(event, context):
    """
    Lambda Authorizer para validar JWT custom
    
    Args:
        event: Evento de API Gateway con authorizationToken
        context: Contexto de Lambda
        
    Returns:
        Política IAM con contexto de permisos
    """
    try:
        logger.info(f"Authorizer invoked for: {event.get('methodArn')}")
        
        # Extraer token del header Authorization
        token = event.get('authorizationToken', '')
        if token.startswith('Bearer '):
            token = token[7:]
        
        if not token:
            logger.error("No token provided")
            raise Exception('Unauthorized')
        
        # Decodificar JWT sin verificar (para obtener el secret de Secrets Manager)
        # En producción, deberías obtener el secret de AWS Secrets Manager
        try:
            # Por ahora, validamos con una clave hardcodeada
            # TODO: Obtener de Secrets Manager
            decoded = jwt.decode(
                token,
                options={"verify_signature": False}  # Temporal - validar firma en producción
            )
            
            logger.info(f"Token decoded for user: {decoded.get('email', decoded.get('sub'))}")
            
            # Verificar que el token tenga los campos necesarios
            if 'sub' not in decoded or 'email' not in decoded:
                logger.error("Invalid token structure")
                raise Exception('Unauthorized: Invalid token structure')
            
            # Verificar expiración
            import time
            if 'exp' in decoded and decoded['exp'] < time.time():
                logger.error("Token expired")
                raise Exception('Unauthorized: Token expired')
            
            # Extraer información del usuario y permisos
            user_email = decoded.get('email', '')
            user_sub = decoded.get('sub', '')
            app_permissions = decoded.get('app_permissions', [])
            module_permissions = decoded.get('module_permissions', [])
            
            # DEBUG: Log de permisos extraídos
            logger.info(f"Extracted app_permissions: {app_permissions}")
            logger.info(f"Extracted module_permissions: {module_permissions}")
            logger.info(f"app_permissions type: {type(app_permissions)}")
            
            # Convertir a JSON string para el contexto
            app_permissions_json = json.dumps(app_permissions)
            module_permissions_json = json.dumps(module_permissions)
            
            logger.info(f"app_permissions_json: {app_permissions_json}")
            logger.info(f"module_permissions_json: {module_permissions_json}")
            
            # Generar política Allow con contexto
            policy = generate_policy(
                principal_id=user_sub,
                effect='Allow',
                resource=event['methodArn'],
                context={
                    'email': user_email,
                    'sub': user_sub,
                    'app_permissions': app_permissions_json,
                    'module_permissions': module_permissions_json
                }
            )
            
            logger.info(f"Policy context: {policy.get('context')}")
            logger.info("Authorization successful")
            return policy
            
        except jwt.ExpiredSignatureError:
            logger.error("Token expired")
            raise Exception('Unauthorized: Token expired')
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {str(e)}")
            raise Exception('Unauthorized: Invalid token')
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            raise Exception('Unauthorized')
            
    except Exception as e:
        logger.error(f"Authorization failed: {str(e)}")
        raise Exception('Unauthorized')


def generate_policy(principal_id, effect, resource, context=None):
    """
    Genera una política IAM para API Gateway
    
    Args:
        principal_id: ID del usuario (sub del token)
        effect: 'Allow' o 'Deny'
        resource: ARN del recurso (methodArn)
        context: Contexto adicional para pasar a la Lambda
    
    Returns:
        dict: Política IAM
    """
    # Construir la política base
    auth_response = {
        'principalId': principal_id
    }
    
    if effect and resource:
        # Permitir acceso a todos los recursos de la API
        # Cambiar resource por un wildcard para permitir todos los métodos
        resource_parts = resource.split('/')
        resource_arn = '/'.join(resource_parts[:2]) + '/*'
        
        policy_document = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': resource_arn
                }
            ]
        }
        auth_response['policyDocument'] = policy_document
    
    # Añadir contexto si se proporciona
    if context:
        auth_response['context'] = context
    
    return auth_response