"""
JWT Service
===========
Servicio para generación y validación de tokens JWT
"""

import boto3
import hashlib
import json
import jwt
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any

logger = logging.getLogger()


class JWTService:
    """Servicio para gestión de tokens JWT"""
    
    # Mapeo de períodos de validez a horas
    VALIDITY_PERIODS = {
        '1_minute': 1/60,  # Para testing de regeneración automática
        '1_day': 24,
        '7_days': 168,
        '30_days': 720,
        '60_days': 1440,
        '90_days': 2160
    }
    
    def __init__(self):
        """Inicializar servicio JWT"""
        self.secret_key = None
        self.algorithm = 'HS256'
    
    def _get_secret_key(self) -> str:
        """
        Obtener clave secreta para firmar JWT desde Secrets Manager
        
        Returns:
            Clave secreta
        """
        if self.secret_key:
            return self.secret_key
        
        secret_name = os.environ.get('JWT_SECRET_NAME', 'identity-mgmt-dev-jwt-secret')
        region = os.environ.get('AWS_REGION', 'eu-west-1')
        
        try:
            client = boto3.client('secretsmanager', region_name=region)
            response = client.get_secret_value(SecretId=secret_name)
            secret_data = json.loads(response['SecretString'])
            self.secret_key = secret_data.get('jwt_secret_key')
            
            if not self.secret_key:
                raise ValueError('jwt_secret_key no encontrado en el secreto')
            
            return self.secret_key
        except Exception as e:
            logger.error(f"Error obteniendo clave JWT: {e}")
            # Fallback a variable de entorno (solo para desarrollo)
            self.secret_key = os.environ.get('JWT_SECRET_KEY')
            if not self.secret_key:
                raise Exception(f"Error accediendo a JWT secret: {str(e)}")
            return self.secret_key
    
    def generate_token(
        self,
        user_info: Dict[str, Any],
        profile_info: Dict[str, Any],
        validity_period: str = '90_days',
        audiences: list = None
    ) -> Dict[str, Any]:
        """
        Generar token JWT con la estructura especificada
        
        Args:
            user_info: Información del usuario de Cognito
            profile_info: Información del perfil de inferencia
            validity_period: Período de validez del token
            audiences: Lista de aplicaciones destino (opcional, se obtiene de config si no se proporciona)
            
        Returns:
            Dict con JWT y metadata
        """
        # Validar período de validez
        if validity_period not in self.VALIDITY_PERIODS:
            raise ValueError(f'Período de validez inválido: {validity_period}')
        
        hours = self.VALIDITY_PERIODS[validity_period]
        
        # Calcular timestamps
        now = datetime.utcnow()
        iat = int(now.timestamp())
        exp = int((now + timedelta(hours=hours)).timestamp())
        
        # Generar JTI único
        jti = str(uuid.uuid4())
        
        # Obtener primer grupo del usuario (team)
        team = user_info.get('groups', ['unknown'])[0] if user_info.get('groups') else 'unknown'
        
        # Si no se proporcionan audiences, usar solo 'bedrock-proxy' por defecto
        if audiences is None:
            audiences = ['bedrock-proxy']
        
        # Construir payload del JWT según especificación
        payload = {
            'user_id': user_info['user_id'],
            'email': user_info['email'],
            'default_inference_profile': str(profile_info['profile_id']),
            'team': team,
            'person': user_info.get('person', ''),
            'iss': 'identity-manager',
            'sub': user_info['user_id'],
            'aud': audiences,
            'exp': exp,
            'iat': iat,
            'jti': jti
        }
        
        # Firmar JWT
        secret_key = self._get_secret_key()
        token = jwt.encode(payload, secret_key, algorithm=self.algorithm)
        
        # Calcular hash del token para almacenamiento
        token_hash = self._calculate_hash(token)
        
        # Calcular fecha de expiración
        expires_at = now + timedelta(hours=hours)
        
        return {
            'jwt': token,
            'jti': jti,
            'token_hash': token_hash,
            'issued_at': now.isoformat() + 'Z',
            'expires_at': expires_at.isoformat() + 'Z',
            'validity_days': hours // 24,
            'payload': payload
        }
    
    def validate_token(self, token: str, audiences: list = None) -> Dict[str, Any]:
        """
        Validar y decodificar un token JWT
        
        Args:
            token: Token JWT a validar
            audiences: Lista de audiences aceptadas (opcional, por defecto acepta bedrock-proxy)
            
        Returns:
            Dict con payload decodificado
            
        Raises:
            jwt.ExpiredSignatureError: Si el token ha expirado
            jwt.InvalidTokenError: Si el token es inválido
        """
        secret_key = self._get_secret_key()
        
        # Si no se proporcionan audiences, usar bedrock-proxy por defecto
        if audiences is None:
            audiences = ['bedrock-proxy']
        
        try:
            payload = jwt.decode(
                token,
                secret_key,
                algorithms=[self.algorithm],
                audience=audiences,
                issuer='identity-manager'
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expirado")
            raise
        except jwt.InvalidTokenError as e:
            logger.error(f"Token inválido: {e}")
            raise
    
    def decode_token_without_validation(self, token: str) -> Dict[str, Any]:
        """
        Decodificar token sin validar (útil para inspección)
        
        Args:
            token: Token JWT
            
        Returns:
            Dict con payload decodificado
        """
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload
        except Exception as e:
            logger.error(f"Error decodificando token: {e}")
            raise ValueError(f"Token malformado: {str(e)}")
    
    def _calculate_hash(self, token: str) -> str:
        """
        Calcular hash SHA-256 del token
        
        Args:
            token: Token JWT
            
        Returns:
            Hash hexadecimal del token
        """
        return hashlib.sha256(token.encode()).hexdigest()
    
    def verify_token_hash(self, token: str, stored_hash: str) -> bool:
        """
        Verificar que el hash de un token coincide con el almacenado
        
        Args:
            token: Token JWT
            stored_hash: Hash almacenado en BD
            
        Returns:
            True si coinciden
        """
        calculated_hash = self._calculate_hash(token)
        return calculated_hash == stored_hash
    
    @staticmethod
    def get_validity_period_hours(period: str) -> int:
        """
        Obtener horas para un período de validez
        
        Args:
            period: Período de validez
            
        Returns:
            Número de horas
        """
        return JWTService.VALIDITY_PERIODS.get(period, 2160)
    
    @staticmethod
    def get_available_validity_periods() -> Dict[str, Dict[str, Any]]:
        """
        Obtener lista de períodos de validez disponibles
        
        Returns:
            Dict con períodos disponibles y sus descripciones
        """
        return {
            '1_day': {'hours': 24, 'days': 1, 'description': '1 día'},
            '7_days': {'hours': 168, 'days': 7, 'description': '7 días'},
            '30_days': {'hours': 720, 'days': 30, 'description': '30 días'},
            '60_days': {'hours': 1440, 'days': 60, 'description': '60 días'},
            '90_days': {'hours': 2160, 'days': 90, 'description': '90 días (por defecto)'}
        }
