"""
MCP Token Service
=================
Servicio para la gestión del ciclo de vida de los tokens del servidor MCP de
Remedy F1: creación, listado, revocación y regeneración automática.

Es un flujo SEPARADO del de tokens del proxy Bedrock (token_regeneration_service
y database_service.*_token). Opera exclusivamente sobre la tabla
"identity-manager-mcp-tokens-tbl" para no impactar lo productivo.
"""

import hashlib
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from psycopg2.extras import RealDictCursor

from services.database_service import DatabaseService
from services.cognito_service import CognitoService
from services.email_service import EmailService
from services.mcp_jwt_service import MCPJWTService

logger = logging.getLogger()

TABLE = '"identity-manager-mcp-tokens-tbl"'

# Máximo de tokens MCP activos por usuario (lo más básico: una constante).
MAX_ACTIVE_MCP_TOKENS = 2


class MCPTokenService:
    """Gestión de tokens JWT del servidor MCP"""

    def __init__(
        self,
        db_service: DatabaseService,
        cognito_service: CognitoService,
        email_service: EmailService
    ):
        self.db = db_service
        self.cognito = cognito_service
        self.email = email_service
        self.jwt_service = MCPJWTService()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def count_active_tokens(self, user_id: str) -> int:
        query = f"""
            SELECT COUNT(*) AS active_count
            FROM {TABLE}
            WHERE cognito_user_id = %s
              AND is_revoked = FALSE
              AND expires_at > NOW()
        """
        result = self.db.execute_query(query, (user_id,))
        return result[0]['active_count'] if result else 0

    def _check_auto_regen_enabled(self, user_id: str) -> bool:
        """Reutiliza el mismo flag Cognito que el proxy (custom:auto_regen_tokens)."""
        try:
            attrs = self.cognito.get_user_attributes(user_id)
            return attrs.get('custom:auto_regen_tokens', 'false').lower() == 'true'
        except Exception as e:
            logger.error(f"Error comprobando auto-regen MCP para {user_id}: {e}")
            return False

    # ------------------------------------------------------------------
    # Crear
    # ------------------------------------------------------------------
    def create_token(
        self,
        user_id: str,
        naturgy_user_900: Optional[str] = None,
        allowed_groups: Optional[list] = None,
        validity_period: str = '90_days',
        send_email: bool = False
    ) -> Dict[str, Any]:
        """Crear un token MCP para un usuario."""
        user_info = self.cognito.get_user(user_id)
        allowed_groups = allowed_groups or []

        active = self.count_active_tokens(user_id)
        if active >= MAX_ACTIVE_MCP_TOKENS:
            raise ValueError(
                f'Usuario ha alcanzado el límite de {MAX_ACTIVE_MCP_TOKENS} tokens MCP activos'
            )

        token_data = self.jwt_service.generate_token(
            user_info=user_info,
            naturgy_user_900=naturgy_user_900,
            allowed_groups=allowed_groups,
            validity_period=validity_period
        )

        insert = f"""
            INSERT INTO {TABLE}
                (cognito_user_id, cognito_email, person, naturgy_user_900,
                 allowed_groups, jti, token_hash, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, issued_at
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(insert, (
                user_id,
                user_info['email'],
                user_info.get('person', ''),
                naturgy_user_900 or None,
                allowed_groups,
                token_data['jti'],
                token_data['token_hash'],
                token_data['expires_at']
            ))
            row = cursor.fetchone()

        result = {
            'success': True,
            'token': {
                'jwt': token_data['jwt'],
                'token_id': str(row['id']),
                'jti': token_data['jti'],
                'issued_at': token_data['issued_at'],
                'expires_at': token_data['expires_at'],
                'validity_days': token_data['validity_days'],
                'naturgy_user_900': naturgy_user_900 or '',
                'allowed_groups': allowed_groups,
                'email': user_info['email'],
                'person': user_info.get('person', '')
            },
            'message': 'Token MCP creado correctamente'
        }

        if send_email:
            try:
                self.email.send_token_email(
                    recipient_email=user_info['email'],
                    recipient_name=user_info.get('person', user_info['email']),
                    token=token_data['jwt'],
                    token_info=result['token']
                )
                result['email_sent'] = True
            except Exception as e:
                logger.warning(f"No se pudo enviar email del token MCP: {e}")
                result['email_sent'] = False
        else:
            result['email_sent'] = False

        return result

    # ------------------------------------------------------------------
    # Listar
    # ------------------------------------------------------------------
    def list_tokens(
        self,
        user_id: Optional[str] = None,
        status: str = 'all',
        limit: Optional[int] = None,
        offset: int = 0
    ) -> Dict[str, Any]:
        query = f"""
            SELECT
                id AS token_id,
                jti,
                cognito_user_id AS user_id,
                cognito_email AS email,
                person,
                naturgy_user_900,
                allowed_groups,
                issued_at AS created_at,
                expires_at,
                last_used_at,
                is_revoked,
                revoked_at,
                revocation_reason,
                regenerated_at,
                regenerated_from_jti,
                CASE
                    WHEN is_revoked THEN 'revoked'
                    WHEN expires_at < CURRENT_TIMESTAMP THEN 'expired'
                    ELSE 'active'
                END AS status
            FROM {TABLE}
            WHERE 1=1
        """
        params = []
        if user_id:
            query += " AND cognito_user_id = %s"
            params.append(user_id)
        if status != 'all':
            if status == 'active':
                query += " AND is_revoked = FALSE AND expires_at > CURRENT_TIMESTAMP"
            elif status == 'revoked':
                query += " AND is_revoked = TRUE"
            elif status == 'expired':
                query += " AND is_revoked = FALSE AND expires_at <= CURRENT_TIMESTAMP"

        query += " ORDER BY issued_at DESC"
        if limit is not None:
            query += " LIMIT %s OFFSET %s"
            params.extend([limit, offset])

        tokens = self.db.execute_query(query, tuple(params))

        # Serializar timestamps a ISO para el frontend
        for t in tokens:
            for k in ('created_at', 'expires_at', 'last_used_at', 'revoked_at', 'regenerated_at'):
                if t.get(k) is not None and hasattr(t[k], 'isoformat'):
                    t[k] = t[k].isoformat()

        return {'tokens': tokens, 'total_count': len(tokens)}

    # ------------------------------------------------------------------
    # Revocar
    # ------------------------------------------------------------------
    def revoke_token(self, token_id: str, reason: str = 'Revocado manualmente') -> Dict[str, Any]:
        query = f"""
            UPDATE {TABLE}
            SET is_revoked = TRUE,
                revoked_at = CURRENT_TIMESTAMP,
                revocation_reason = %s
            WHERE id = %s AND is_revoked = FALSE
        """
        affected = self.db.execute_update(query, (reason, token_id))
        if affected == 0:
            raise ValueError('Token MCP no encontrado o ya revocado')
        return {'success': True, 'message': 'Token MCP revocado correctamente'}

    # ------------------------------------------------------------------
    # Regenerar (auto-renovación)
    # ------------------------------------------------------------------
    def regenerate_expired_token(
        self,
        expired_jti: str,
        user_id: str,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Regenerar un token MCP expirado conservando sus características."""
        rows = self.db.execute_query(
            f"SELECT * FROM {TABLE} WHERE jti = %s", (expired_jti,)
        )
        if not rows:
            return {'success': False, 'error': 'token_not_found',
                    'message': 'Token MCP no encontrado'}
        token = rows[0]

        if str(token['cognito_user_id']) != str(user_id):
            return {'success': False, 'error': 'user_mismatch',
                    'message': 'El token no pertenece a este usuario'}
        if token['is_revoked']:
            return {'success': False, 'error': 'token_revoked',
                    'message': 'No se puede regenerar un token revocado'}
        if token['regenerated_at']:
            return {'success': False, 'error': 'already_regenerated',
                    'message': 'Este token ya fue regenerado'}
        if not self._check_auto_regen_enabled(token['cognito_user_id']):
            return {'success': False, 'error': 'auto_regen_disabled',
                    'message': 'La auto-regeneración no está activada para este usuario'}
        if self.count_active_tokens(user_id) >= MAX_ACTIVE_MCP_TOKENS:
            return {'success': False, 'error': 'max_tokens_reached',
                    'message': 'Máximo de tokens MCP activos alcanzado'}

        # Calcular período a partir de la duración original
        validity_seconds = (token['expires_at'] - token['issued_at']).total_seconds()
        validity_days = validity_seconds / (24 * 3600)
        if validity_days <= 1:
            validity_period = '1_day'
        elif validity_days <= 7:
            validity_period = '7_days'
        elif validity_days <= 30:
            validity_period = '30_days'
        elif validity_days <= 60:
            validity_period = '60_days'
        else:
            validity_period = '90_days'

        user_info = self.cognito.get_user(str(user_id))
        if not user_info.get('email'):
            user_info['email'] = token['cognito_email']

        token_data = self.jwt_service.generate_token(
            user_info=user_info,
            naturgy_user_900=token.get('naturgy_user_900'),
            allowed_groups=token.get('allowed_groups') or [],
            validity_period=validity_period
        )
        new_jti = token_data['jti']

        insert = f"""
            INSERT INTO {TABLE}
                (cognito_user_id, cognito_email, person, naturgy_user_900,
                 allowed_groups, jti, token_hash, expires_at, issued_at,
                 regenerated_from_jti, regeneration_reason,
                 regeneration_client_ip, regeneration_user_agent)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s, %s, %s)
        """
        self.db.execute_update(insert, (
            token['cognito_user_id'],
            token['cognito_email'],
            token.get('person'),
            token.get('naturgy_user_900'),
            token.get('allowed_groups') or [],
            new_jti,
            token_data['token_hash'],
            token_data['expires_at'],
            expired_jti,
            'auto_regeneration',
            client_ip,
            user_agent
        ))

        self.db.execute_update(
            f"UPDATE {TABLE} SET regenerated_at = NOW(), regenerated_to_jti = %s WHERE jti = %s",
            (new_jti, expired_jti)
        )

        email_sent = False
        try:
            recipient_name = token.get('person') or token['cognito_email'].split('@')[0]
            email_sent = self.email.send_token_email(
                recipient_email=token['cognito_email'],
                recipient_name=recipient_name,
                token=token_data['jwt'],
                token_info={
                    'expires_at': token_data['expires_at'],
                    'validity_days': token_data['validity_days'],
                    'naturgy_user_900': token.get('naturgy_user_900') or '',
                    'regenerated': True
                }
            )
            if email_sent:
                self.db.execute_update(
                    f"UPDATE {TABLE} SET regeneration_email_sent = TRUE WHERE jti = %s",
                    (new_jti,)
                )
        except Exception as e:
            logger.error(f"Error enviando email de regeneración MCP: {e}")

        return {
            'success': True,
            'new_token_jti': new_jti,
            'new_token': token_data['jwt'],
            'email_sent': email_sent,
            'expires_at': token_data['expires_at'],
            'message': 'Token MCP regenerado correctamente'
        }
