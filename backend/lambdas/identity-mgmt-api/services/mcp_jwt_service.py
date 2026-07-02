"""
MCP JWT Service
===============
Servicio para generación y validación de tokens JWT del servidor MCP de Remedy F1.

Es un servicio SEPARADO de jwt_service.py (proxy Bedrock) para no impactar el
flujo productivo. Reutiliza el MISMO secreto HS256 (Secrets Manager) para que el
servidor MCP pueda validar la firma sin gestionar credenciales adicionales, pero
emite tokens con audience propia ('remedy-mcp') y claims específicos del MCP:
email, person (nombre) y naturgy_user_900.
"""

import boto3
import hashlib
import json
import jwt
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger()


class MCPJWTService:
    """Servicio para gestión de tokens JWT del servidor MCP"""

    # Audience de los tokens MCP. El servidor MCP valida exactamente este valor.
    AUDIENCE = 'remedy-mcp'
    ISSUER = 'identity-manager'

    # Mapeo de períodos de validez a horas (mismo set que el proxy)
    VALIDITY_PERIODS = {
        '1_minute': 1 / 60,  # Para testing de regeneración automática
        '1_day': 24,
        '7_days': 168,
        '30_days': 720,
        '60_days': 1440,
        '90_days': 2160
    }

    def __init__(self):
        """Inicializar servicio JWT MCP"""
        self.secret_key = None
        self.algorithm = 'HS256'

    def _get_secret_key(self) -> str:
        """
        Obtener clave secreta para firmar JWT desde Secrets Manager.

        Reutiliza el MISMO secreto que el proxy (JWT_SECRET_NAME) para que el
        servidor MCP solo necesite ese único secreto compartido.
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
            logger.error(f"Error obteniendo clave JWT MCP: {e}")
            self.secret_key = os.environ.get('JWT_SECRET_KEY')
            if not self.secret_key:
                raise Exception(f"Error accediendo a JWT secret: {str(e)}")
            return self.secret_key

    def generate_token(
        self,
        user_info: Dict[str, Any],
        naturgy_user_900: Optional[str] = None,
        allowed_groups: Optional[list] = None,
        validity_period: str = '90_days'
    ) -> Dict[str, Any]:
        """
        Generar token JWT para el servidor MCP.

        Args:
            user_info: Información del usuario (user_id, email, person, groups)
            naturgy_user_900: Usuario 900 de Naturgy (opcional hasta tener Cognito).
                              Hoy es enchufable: se pasa a mano o desde la BD; el
                              día que exista el atributo Cognito, el origen cambia
                              sin tocar este servicio.
            allowed_groups: Grupos de Remedy a los que el usuario tiene acceso.
                            Viajan en el claim allowed_groups; el MCP los lee de
                            ahí para autorizar consultas por grupo (no consulta
                            ninguna fuente externa).
            validity_period: Período de validez del token

        Returns:
            Dict con JWT y metadata
        """
        if validity_period not in self.VALIDITY_PERIODS:
            raise ValueError(f'Período de validez inválido: {validity_period}')

        hours = self.VALIDITY_PERIODS[validity_period]

        now = datetime.utcnow()
        iat = int(now.timestamp())
        exp = int((now + timedelta(hours=hours)).timestamp())
        jti = str(uuid.uuid4())

        team = user_info.get('groups', ['unknown'])[0] if user_info.get('groups') else 'unknown'

        # Claims del token MCP. El servidor MCP lee email, person y
        # naturgy_user_900 directamente de aquí (no llama de vuelta a la Lambda).
        payload = {
            'user_id': user_info['user_id'],
            'email': user_info['email'],
            'person': user_info.get('person', ''),
            'naturgy_user_900': naturgy_user_900 or '',
            'allowed_groups': allowed_groups or [],
            'team': team,
            'iss': self.ISSUER,
            'sub': user_info['user_id'],
            'aud': self.AUDIENCE,
            'exp': exp,
            'iat': iat,
            'jti': jti
        }

        secret_key = self._get_secret_key()
        token = jwt.encode(payload, secret_key, algorithm=self.algorithm)
        token_hash = self._calculate_hash(token)
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

    def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validar y decodificar un token JWT MCP.

        Raises:
            jwt.ExpiredSignatureError: Si el token ha expirado
            jwt.InvalidTokenError: Si el token es inválido
        """
        secret_key = self._get_secret_key()
        return jwt.decode(
            token,
            secret_key,
            algorithms=[self.algorithm],
            audience=self.AUDIENCE,
            issuer=self.ISSUER
        )

    def _calculate_hash(self, token: str) -> str:
        """Calcular hash SHA-256 del token"""
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def get_validity_period_hours(period: str) -> int:
        return MCPJWTService.VALIDITY_PERIODS.get(period, 2160)
