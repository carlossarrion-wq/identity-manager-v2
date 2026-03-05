"""
Token Regeneration Service
==========================
Service for automatic regeneration of expired JWT tokens
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import pytz

from services.database_service import DatabaseService
from services.cognito_service import CognitoService
from services.email_service import EmailService
from services.jwt_service import JWTService

logger = logging.getLogger()


class TokenRegenerationService:
    """Service for handling automatic token regeneration"""
    
    def __init__(self, db_service: DatabaseService, cognito_service: CognitoService, email_service: EmailService):
        """
        Initialize the token regeneration service
        
        Args:
            db_service: Database service instance
            cognito_service: Cognito service instance
            email_service: Email service instance
        """
        self.db = db_service
        self.cognito = cognito_service
        self.email = email_service
        self.jwt_service = JWTService()
    
    def check_auto_regen_enabled(self, user_id: str) -> bool:
        """
        Check if user has auto-regeneration enabled in Cognito
        
        Args:
            user_id: User's Cognito ID
            
        Returns:
            True if auto-regeneration is enabled, False otherwise
        """
        try:
            # Get user attributes from Cognito
            user_attributes = self.cognito.get_user_attributes(user_id)
            
            # Check custom:auto_regen_tokens attribute
            auto_regen = user_attributes.get('custom:auto_regen_tokens', 'false')
            
            return auto_regen.lower() == 'true'
            
        except Exception as e:
            logger.error(f"Error checking auto-regen status for user {user_id}: {e}")
            return False
    
    def check_active_tokens_limit(self, user_id: str) -> Dict[str, Any]:
        """
        Check if user has reached the maximum number of active tokens
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with:
                - can_create: bool - Whether user can create a new token
                - active_count: int - Current number of active tokens
                - max_allowed: int - Maximum tokens allowed
        """
        try:
            # Count active tokens (not revoked, not expired)
            query = """
                SELECT COUNT(*) as active_count
                FROM "identity-manager-tokens-tbl"
                WHERE cognito_user_id = %s
                AND is_revoked = FALSE
                AND expires_at > NOW()
            """
            
            result = self.db.execute_query(query, (user_id,))
            active_count = result[0]['active_count'] if result else 0
            
            # Get max tokens allowed (default: 5)
            # TODO: This could be configurable per user in the future
            max_allowed = 5
            
            return {
                'can_create': active_count < max_allowed,
                'active_count': active_count,
                'max_allowed': max_allowed
            }
            
        except Exception as e:
            logger.error(f"Error checking active tokens limit for user {user_id}: {e}")
            return {
                'can_create': False,
                'active_count': 0,
                'max_allowed': 5,
                'error': str(e)
            }
    
    def get_expired_token_info(self, token_jti: str) -> Optional[Dict[str, Any]]:
        """
        Get information about an expired token
        
        Args:
            token_jti: JTI of the expired token
            
        Returns:
            Token information or None if not found
        """
        try:
            query = """
                SELECT 
                    t.jti,
                    t.cognito_user_id as user_id,
                    t.application_profile_id as profile_id,
                    t.expires_at,
                    t.issued_at,
                    t.is_revoked as revoked_at,
                    t.regenerated_at,
                    t.cognito_user_id,
                    t.cognito_email as email,
                    q.person,
                    p.profile_name,
                    p.model_id,
                    p.application_id
                FROM "identity-manager-tokens-tbl" t
                JOIN "identity-manager-profiles-tbl" p ON t.application_profile_id = p.id
                LEFT JOIN "bedrock-proxy-user-quotas-tbl" q ON t.cognito_user_id = q.cognito_user_id
                WHERE t.jti = %s
            """
            
            result = self.db.execute_query(query, (token_jti,))
            
            if not result:
                logger.warning(f"Token not found: {token_jti}")
                return None
            
            return result[0]
            
        except Exception as e:
            logger.error(f"Error getting expired token info: {e}")
            return None
    
    def regenerate_expired_token(
        self,
        expired_token_jti: str,
        user_id: str,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Regenerate an expired token with the same characteristics
        
        Args:
            expired_token_jti: JTI of the expired token
            user_id: User ID (for validation)
            client_ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            Dictionary with regeneration result
        """
        try:
            # 1. Get expired token information
            token_info = self.get_expired_token_info(expired_token_jti)
            
            if not token_info:
                return {
                    'success': False,
                    'error': 'token_not_found',
                    'message': 'Expired token not found in database'
                }
            
            # 2. Validate token belongs to user
            if str(token_info['user_id']) != str(user_id):
                return {
                    'success': False,
                    'error': 'user_mismatch',
                    'message': 'Token does not belong to this user'
                }
            
            # 3. Check if token is revoked
            if token_info['revoked_at']:
                return {
                    'success': False,
                    'error': 'token_revoked',
                    'message': 'Cannot regenerate a revoked token'
                }
            
            # 4. Check if token was already regenerated
            if token_info['regenerated_at']:
                return {
                    'success': False,
                    'error': 'already_regenerated',
                    'message': 'This token has already been regenerated'
                }
            
            # 5. Check if user has auto-regen enabled
            if not self.check_auto_regen_enabled(token_info['cognito_user_id']):
                return {
                    'success': False,
                    'error': 'auto_regen_disabled',
                    'message': 'Auto-regeneration is not enabled for this user'
                }
            
            # 6. Check active tokens limit
            tokens_check = self.check_active_tokens_limit(user_id)
            
            if not tokens_check['can_create']:
                return {
                    'success': False,
                    'error': 'max_tokens_reached',
                    'message': 'Maximum number of active tokens reached',
                    'active_tokens_count': tokens_check['active_count'],
                    'max_tokens_allowed': tokens_check['max_allowed']
                }
            
            # 7. Calculate validity period from old token dates
            issued_at = token_info['issued_at']
            expires_at_old = token_info['expires_at']
            
            # Calculate total seconds between issued and expiration
            validity_seconds = (expires_at_old - issued_at).total_seconds()
            validity_minutes = validity_seconds / 60
            validity_days = validity_seconds / (24 * 3600)
            
            # Map to validity_period based on actual duration
            if validity_minutes <= 1:
                validity_period = '1_minute'
            elif validity_minutes <= 5:
                validity_period = '5_minutes'
            elif validity_minutes <= 15:
                validity_period = '15_minutes'
            elif validity_minutes <= 30:
                validity_period = '30_minutes'
            elif validity_minutes <= 60:
                validity_period = '1_hour'
            elif validity_days <= 1:
                validity_period = '1_day'
            elif validity_days <= 7:
                validity_period = '7_days'
            elif validity_days <= 30:
                validity_period = '30_days'
            elif validity_days <= 60:
                validity_period = '60_days'
            else:
                validity_period = '90_days'
            
            # Prepare user and profile info for JWT generation
            user_info = {
                'user_id': str(user_id),
                'email': token_info['email'],
                'groups': [],  # Will be populated if needed
                'person': ''
            }
            
            profile_info = {
                'profile_id': str(token_info['profile_id']),
                'profile_name': token_info['profile_name'],
                'model_id': token_info['model_id']
            }
            
            # Generate JWT token using JWTService
            token_data = self.jwt_service.generate_token(
                user_info=user_info,
                profile_info=profile_info,
                validity_period=validity_period,
                audiences=['bedrock-proxy']
            )
            
            new_token = token_data['jwt']
            new_jti = token_data['jti']
            
            # Parse expires_at from token_data
            madrid_tz = pytz.timezone('Europe/Madrid')
            now = datetime.now(madrid_tz)
            expires_at = datetime.fromisoformat(token_data['expires_at'].replace('Z', '+00:00')).astimezone(madrid_tz)
            
            # 8. Insert new token in database
            insert_query = """
                INSERT INTO "identity-manager-tokens-tbl" (
                    jti, cognito_user_id, cognito_email, token_hash,
                    application_profile_id, expires_at, issued_at,
                    regenerated_from_jti, regeneration_reason,
                    regeneration_client_ip, regeneration_user_agent
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # Generate token hash
            import hashlib
            token_hash = hashlib.sha256(new_token.encode()).hexdigest()
            
            self.db.execute_update(
                insert_query,
                (
                    new_jti,
                    token_info['cognito_user_id'],
                    token_info['email'],
                    token_hash,
                    token_info['profile_id'],
                    expires_at,
                    now,
                    expired_token_jti,
                    'auto_regeneration',
                    client_ip,
                    user_agent
                )
            )
            
            # 9. Mark old token as regenerated
            update_query = """
                UPDATE "identity-manager-tokens-tbl"
                SET regenerated_at = %s,
                    regenerated_to_jti = %s
                WHERE jti = %s
            """
            
            self.db.execute_update(
                update_query,
                (now, new_jti, expired_token_jti)
            )
            
            # 10. Send email with new token
            email_sent = False
            try:
                # Use person field if available, otherwise fallback to email
                recipient_name = token_info.get('person') or token_info['email'].split('@')[0]
                
                email_sent = self.email.send_token_email(
                    recipient_email=token_info['email'],
                    recipient_name=recipient_name,
                    token=new_token,
                    token_info={
                        'profile': {
                            'profile_name': token_info['profile_name'],
                            'model': token_info['model_id'],
                            'application': token_info['application_id']
                        },
                        'expires_at': expires_at.strftime('%Y-%m-%d %H:%M:%S %Z'),
                        'validity_days': validity_days,
                        'regenerated': True,
                        'old_token_expired_at': token_info['expires_at'].strftime('%Y-%m-%d %H:%M:%S')
                    }
                )
                
                # Update email sent status
                if email_sent:
                    update_email_query = """
                        UPDATE "identity-manager-tokens-tbl"
                        SET regeneration_email_sent = TRUE
                        WHERE jti = %s
                    """
                    self.db.execute_update(update_email_query, (new_jti,))
                    
            except Exception as e:
                logger.error(f"Error sending regeneration email: {e}")
            
            # 11. Return success
            return {
                'success': True,
                'new_token_jti': new_jti,
                'new_token': new_token,
                'email_sent': email_sent,
                'expires_at': expires_at.isoformat(),
                'message': 'Token regenerated successfully'
            }
            
        except Exception as e:
            logger.error(f"Error regenerating token: {e}", exc_info=True)
            return {
                'success': False,
                'error': 'regeneration_failed',
                'message': f'Failed to regenerate token: {str(e)}'
            }
    
    def get_user_regeneration_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> list:
        """
        Get regeneration history for a user
        
        Args:
            user_id: User ID
            limit: Maximum number of records to return
            
        Returns:
            List of regeneration events
        """
        try:
            query = """
                SELECT 
                    jti,
                    regenerated_from_jti,
                    regeneration_reason,
                    regeneration_client_ip,
                    regeneration_email_sent,
                    created_at,
                    expires_at
                FROM "identity-manager-tokens-tbl"
                WHERE user_id = %s
                AND regenerated_from_jti IS NOT NULL
                ORDER BY created_at DESC
                LIMIT %s
            """
            
            result = self.db.execute_query(query, (user_id, limit))
            return result if result else []
            
        except Exception as e:
            logger.error(f"Error getting regeneration history: {e}")
            return []