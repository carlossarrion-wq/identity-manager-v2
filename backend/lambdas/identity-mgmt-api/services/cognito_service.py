"""
Cognito Service
===============
Servicio para interactuar con AWS Cognito User Pool
"""

import boto3
import logging
import os
from typing import Dict, List, Optional, Any
from botocore.exceptions import ClientError

logger = logging.getLogger()


class CognitoService:
    """Servicio para gestión de usuarios en AWS Cognito"""
    
    def __init__(self):
        """Inicializar cliente de Cognito"""
        self.client = boto3.client('cognito-idp', region_name=os.environ.get('AWS_REGION', 'eu-west-1'))
        self.user_pool_id = os.environ.get('COGNITO_USER_POOL_ID')
        
        if not self.user_pool_id:
            raise ValueError('COGNITO_USER_POOL_ID no está configurado')
    
    def list_users(
        self,
        group: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 60,
        pagination_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Listar usuarios del User Pool
        
        Args:
            group: Filtrar por grupo (opcional)
            status: Filtrar por estado (opcional)
            limit: Número máximo de resultados
            pagination_token: Token para paginación
            
        Returns:
            Dict con lista de usuarios y token de paginación
        """
        try:
            if group:
                # Listar usuarios de un grupo específico
                params = {
                    'UserPoolId': self.user_pool_id,
                    'GroupName': group,
                    'Limit': limit
                }
                if pagination_token:
                    params['NextToken'] = pagination_token
                
                response = self.client.list_users_in_group(**params)
                users_data = response.get('Users', [])
                next_token = response.get('NextToken')
            else:
                # Listar todos los usuarios
                params = {
                    'UserPoolId': self.user_pool_id,
                    'Limit': limit
                }
                if pagination_token:
                    params['PaginationToken'] = pagination_token
                
                response = self.client.list_users(**params)
                users_data = response.get('Users', [])
                next_token = response.get('PaginationToken')
            
            # Formatear usuarios
            users = []
            for user_data in users_data:
                user = self._format_user(user_data)
                
                # Filtrar por estado si se especifica
                if status and user['status'] != status:
                    continue
                
                # Obtener grupos del usuario
                user['groups'] = self._get_user_groups(user['user_id'])
                
                users.append(user)
            
            return {
                'users': users,
                'pagination_token': next_token,
                'total_count': len(users)
            }
            
        except ClientError as e:
            logger.error(f"Error listando usuarios: {e}")
            raise Exception(f"Error de Cognito: {e.response['Error']['Message']}")
    
    def get_user(self, username: str) -> Dict[str, Any]:
        """
        Obtener información de un usuario
        
        Args:
            username: Username o email del usuario
            
        Returns:
            Dict con información del usuario
        """
        try:
            response = self.client.admin_get_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )
            
            user = self._format_user(response)
            user['groups'] = self._get_user_groups(username)
            
            return user
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'UserNotFoundException':
                raise ValueError(f'Usuario no encontrado: {username}')
            logger.error(f"Error obteniendo usuario: {e}")
            raise Exception(f"Error de Cognito: {e.response['Error']['Message']}")
    
    def create_user(
        self,
        email: str,
        person: str,
        group: str,
        temporary_password: Optional[str] = None,
        send_email: bool = True,
        auto_regenerate_tokens: bool = True
    ) -> Dict[str, Any]:
        """
        Crear nuevo usuario en Cognito
        
        Args:
            email: Email del usuario (será el username)
            person: Nombre completo de la persona
            group: Grupo al que pertenecerá
            temporary_password: Contraseña temporal (opcional)
            send_email: Enviar email de bienvenida
            auto_regenerate_tokens: Permitir auto-regeneración de tokens
            
        Returns:
            Dict con información del usuario creado
        """
        try:
            # Preparar atributos
            # IMPORTANTE: Cuando UsernameAttributes incluye 'email', NO se debe incluir 'email' en UserAttributes
            # Cognito lo toma automáticamente del Username
            user_attributes = [
                {'Name': 'email_verified', 'Value': 'true'},
                {'Name': 'name', 'Value': person},
                {'Name': 'custom:auto_regen_tokens', 'Value': 'true' if auto_regenerate_tokens else 'false'}
            ]
            
            # Crear usuario
            params = {
                'UserPoolId': self.user_pool_id,
                'Username': email,  # El email será el username
                'UserAttributes': user_attributes,
                'DesiredDeliveryMediums': ['EMAIL'] if send_email else []
            }
            
            if temporary_password:
                params['TemporaryPassword'] = temporary_password
                # Solo usar SUPPRESS si no queremos enviar email
                # Si queremos enviar email, NO especificar MessageAction (Cognito enviará automáticamente)
                if not send_email:
                    params['MessageAction'] = 'SUPPRESS'
            
            # Log de depuración
            logger.info(f"Intentando crear usuario con params: {params}")
            
            response = self.client.admin_create_user(**params)
            
            logger.info(f"Usuario creado exitosamente: {response['User']['Username']}")
            
            # Añadir usuario al grupo
            self.client.admin_add_user_to_group(
                UserPoolId=self.user_pool_id,
                Username=email,
                GroupName=group
            )
            
            user = self._format_user(response['User'])
            user['groups'] = [group]
            
            return {
                'success': True,
                'user': user,
                'message': 'Usuario creado correctamente' + (' Email de bienvenida enviado.' if send_email else '')
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'UsernameExistsException':
                raise ValueError(f'El usuario {email} ya existe')
            elif error_code == 'InvalidParameterException':
                raise ValueError(f'Parámetros inválidos: {e.response["Error"]["Message"]}')
            logger.error(f"Error creando usuario: {e}")
            raise Exception(f"Error de Cognito: {e.response['Error']['Message']}")
    
    def delete_user(self, username: str) -> bool:
        """
        Eliminar usuario de Cognito
        
        Args:
            username: Username del usuario
            
        Returns:
            True si se eliminó correctamente
        """
        try:
            self.client.admin_delete_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'UserNotFoundException':
                raise ValueError(f'Usuario no encontrado: {username}')
            logger.error(f"Error eliminando usuario: {e}")
            raise Exception(f"Error de Cognito: {e.response['Error']['Message']}")
    
    def list_groups(self) -> Dict[str, Any]:
        """
        Listar todos los grupos del User Pool
        
        Returns:
            Dict con lista de grupos
        """
        try:
            response = self.client.list_groups(
                UserPoolId=self.user_pool_id,
                Limit=60
            )
            
            groups = []
            for group_data in response.get('Groups', []):
                # Contar usuarios en el grupo - necesitamos paginar para obtener el conteo real
                user_count = 0
                next_token = None
                
                while True:
                    params = {
                        'UserPoolId': self.user_pool_id,
                        'GroupName': group_data['GroupName'],
                        'Limit': 60
                    }
                    if next_token:
                        params['NextToken'] = next_token
                    
                    users_response = self.client.list_users_in_group(**params)
                    user_count += len(users_response.get('Users', []))
                    next_token = users_response.get('NextToken')
                    
                    if not next_token:
                        break
                
                groups.append({
                    'group_name': group_data['GroupName'],
                    'description': group_data.get('Description', ''),
                    'precedence': group_data.get('Precedence', 0),
                    'user_count': user_count
                })
            
            return {'groups': groups}
            
        except ClientError as e:
            logger.error(f"Error listando grupos: {e}")
            raise Exception(f"Error de Cognito: {e.response['Error']['Message']}")
    
    def _format_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formatear datos de usuario de Cognito
        
        Args:
            user_data: Datos raw de Cognito
            
        Returns:
            Dict con datos formateados
        """
        # Manejar tanto UserAttributes (de admin_get_user) como Attributes (de list_users)
        attributes_list = user_data.get('UserAttributes', user_data.get('Attributes', []))
        attributes = {attr['Name']: attr['Value'] for attr in attributes_list}
        
        # Leer el atributo de auto-regeneración (por defecto true si no existe)
        auto_regenerate = attributes.get('custom:auto_regen_tokens', 'true').lower() == 'true'
        
        return {
            'user_id': user_data.get('Username'),
            'email': attributes.get('email', ''),
            'person': attributes.get('custom:person', attributes.get('name', '')),
            'status': user_data.get('UserStatus', 'UNKNOWN'),
            'created_date': user_data.get('UserCreateDate', '').isoformat() if user_data.get('UserCreateDate') else None,
            'enabled': user_data.get('Enabled', True),
            'auto_regenerate_tokens': auto_regenerate
        }
    
    def get_user_attributes(self, username: str) -> Dict[str, str]:
        """
        Obtener atributos de un usuario
        
        Args:
            username: Username o Cognito User ID del usuario
            
        Returns:
            Dict con atributos del usuario
        """
        try:
            response = self.client.admin_get_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )
            
            # Convertir lista de atributos a diccionario
            attributes = {}
            for attr in response.get('UserAttributes', []):
                attributes[attr['Name']] = attr['Value']
            
            return attributes
            
        except ClientError as e:
            logger.error(f"Error obteniendo atributos de usuario {username}: {e}")
            return {}
    
    def _get_user_groups(self, username: str) -> List[str]:
        """
        Obtener grupos de un usuario
        
        Args:
            username: Username del usuario
            
        Returns:
            Lista de nombres de grupos
        """
        try:
            response = self.client.admin_list_groups_for_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )
            return [group['GroupName'] for group in response.get('Groups', [])]
        except ClientError:
            return []
