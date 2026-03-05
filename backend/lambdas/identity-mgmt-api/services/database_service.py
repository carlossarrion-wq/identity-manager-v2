"""
Database Service
================
Servicio para interactuar con PostgreSQL RDS
Implementa Connection Pool Singleton optimizado para Lambda
"""

import boto3
import json
import logging
import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

logger = logging.getLogger()


class DatabaseService:
    """
    Servicio para gestión de base de datos PostgreSQL
    Implementa Connection Pool Singleton optimizado para AWS Lambda
    Similar al patrón usado en Gestión Demanda (Node.js con pg)
    """
    
    # Singleton: Pool compartido entre invocaciones del mismo contenedor Lambda
    _pool = None
    _secrets_cache = None
    
    @classmethod
    def _get_db_credentials(cls) -> Dict[str, str]:
        """
        Obtener credenciales de la base de datos desde Secrets Manager (con caché)
        
        Returns:
            Dict con credenciales de BD
        """
        if cls._secrets_cache:
            logger.info("Usando credenciales de BD desde caché")
            return cls._secrets_cache
        
        secret_name = os.environ.get('DB_SECRET_NAME', 'identity-mgmt-dev-db-admin')
        region = os.environ.get('AWS_REGION', 'eu-west-1')
        
        logger.info(f"Obteniendo credenciales de Secrets Manager: {secret_name}")
        
        try:
            client = boto3.client('secretsmanager', region_name=region)
            logger.info("Cliente de Secrets Manager creado, obteniendo secret...")
            response = client.get_secret_value(SecretId=secret_name)
            logger.info("Secret obtenido, parseando JSON...")
            cls._secrets_cache = json.loads(response['SecretString'])
            logger.info("Credenciales de BD obtenidas desde Secrets Manager")
            return cls._secrets_cache
        except Exception as e:
            logger.error(f"Error obteniendo credenciales: {e}")
            raise Exception(f"Error accediendo a Secrets Manager: {str(e)}")
    
    @classmethod
    def get_pool(cls):
        """
        Obtener o crear Connection Pool Singleton
        Optimizado para Lambda: 1 conexión por contenedor
        
        Returns:
            Connection pool de psycopg2
        """
        if cls._pool is None:
            logger.info("Pool no existe, creando nuevo pool...")
            creds = cls._get_db_credentials()
            
            logger.info(f"Conectando a RDS: {creds['host']}:{creds.get('port', 5432)}")
            
            try:
                cls._pool = psycopg2.pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=1,  # Lambda: 1 conexión por contenedor
                    host=creds['host'],
                    port=creds.get('port', 5432),
                    database=creds['dbname'],
                    user=creds['username'],
                    password=creds['password'],
                    sslmode='require',  # Conexión segura obligatoria
                    connect_timeout=10,  # 10 segundos timeout de conexión
                    options='-c statement_timeout=30000'  # 30 segundos timeout de statement
                )
                logger.info("PostgreSQL connection pool created successfully")
            except Exception as e:
                logger.error(f"Error creando connection pool: {e}")
                raise Exception(f"Error conectando a PostgreSQL: {str(e)}")
        else:
            logger.info("Usando pool existente")
        
        return cls._pool
    
    @classmethod
    @contextmanager
    def get_connection(cls):
        """
        Context manager para obtener conexión del pool
        Maneja automáticamente commit/rollback y liberación de conexión
        
        Yields:
            Conexión a PostgreSQL del pool
        """
        pool_instance = cls.get_pool()
        conn = None
        
        try:
            conn = pool_instance.getconn()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error de base de datos: {e}")
            raise Exception(f"Error de base de datos: {str(e)}")
        finally:
            if conn:
                pool_instance.putconn(conn)
    
    @classmethod
    def execute_query(cls, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """
        Ejecutar query SELECT y retornar resultados como lista de diccionarios
        
        Args:
            query: Query SQL
            params: Parámetros de la query
            
        Returns:
            Lista de diccionarios con resultados
        """
        with cls.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params or ())
                results = cursor.fetchall()
                return [dict(row) for row in results]
    
    @classmethod
    def execute_update(cls, query: str, params: tuple = None) -> int:
        """
        Ejecutar query INSERT/UPDATE/DELETE
        
        Args:
            query: Query SQL
            params: Parámetros de la query
            
        Returns:
            Número de filas afectadas
        """
        with cls.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                return cursor.rowcount
    
    def __init__(self):
        """
        Inicializar servicio (mantiene compatibilidad con código existente)
        Nota: Los métodos de instancia usan los métodos de clase internamente
        """
        pass
    
    # ========================================================================
    # OPERACIONES DE TOKENS
    # ========================================================================
    
    def list_tokens(
        self,
        user_id: Optional[str] = None,
        status: str = 'all',
        profile_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Listar tokens JWT
        
        Args:
            user_id: Filtrar por usuario
            status: Filtrar por estado (active, revoked, expired, all)
            profile_id: Filtrar por perfil
            limit: Límite de resultados
            offset: Offset para paginación
            
        Returns:
            Dict con lista de tokens
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Construir query
            query = """
                SELECT 
                    t.id as token_id,
                    t.jti,
                    t.cognito_user_id as user_id,
                    t.cognito_email as email,
                    t.application_profile_id as profile_id,
                    t.issued_at as created_at,
                    t.expires_at,
                    t.last_used_at,
                    t.is_revoked,
                    t.revoked_at,
                    t.revocation_reason,
                    p.profile_name,
                    CASE 
                        WHEN t.is_revoked THEN 'revoked'
                        WHEN t.expires_at < CURRENT_TIMESTAMP THEN 'expired'
                        ELSE 'active'
                    END as status
                FROM "identity-manager-tokens-tbl" t
                LEFT JOIN "identity-manager-profiles-tbl" p ON t.application_profile_id = p.id
                WHERE 1=1
            """
            
            params = []
            
            if user_id:
                query += " AND t.cognito_user_id = %s"
                params.append(user_id)
            
            if profile_id:
                query += " AND t.application_profile_id = %s"
                params.append(profile_id)
            
            if status != 'all':
                if status == 'active':
                    query += " AND t.is_revoked = FALSE AND t.expires_at > CURRENT_TIMESTAMP"
                elif status == 'revoked':
                    query += " AND t.is_revoked = TRUE"
                elif status == 'expired':
                    query += " AND t.is_revoked = FALSE AND t.expires_at <= CURRENT_TIMESTAMP"
            
            query += " ORDER BY t.issued_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            tokens = cursor.fetchall()
            
            # Contar total
            count_query = "SELECT COUNT(*) as total FROM \"identity-manager-tokens-tbl\" t WHERE 1=1"
            count_params = []
            
            if user_id:
                count_query += " AND t.cognito_user_id = %s"
                count_params.append(user_id)
            
            cursor.execute(count_query, count_params)
            total = cursor.fetchone()['total']
            
            return {
                'tokens': [dict(token) for token in tokens],
                'total_count': total
            }
    
    def save_token(
        self,
        user_id: str,
        email: str,
        jti: str,
        token_hash: str,
        profile_id: str,
        expires_at: datetime
    ) -> Dict[str, Any]:
        """
        Guardar token en base de datos
        
        Args:
            user_id: ID del usuario en Cognito
            email: Email del usuario
            jti: JWT ID
            token_hash: Hash del token
            profile_id: ID del perfil de inferencia
            expires_at: Fecha de expiración
            
        Returns:
            Dict con información del token guardado
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                INSERT INTO "identity-manager-tokens-tbl" 
                (cognito_user_id, cognito_email, jti, token_hash, application_profile_id, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, issued_at
            """
            
            cursor.execute(query, (user_id, email, jti, token_hash, profile_id, expires_at))
            result = cursor.fetchone()
            
            return {
                'token_id': str(result['id']),
                'issued_at': result['issued_at'].isoformat()
            }
    
    def get_token(self, token_id: str) -> Dict[str, Any]:
        """
        Obtener información de un token
        
        Args:
            token_id: ID del token
            
        Returns:
            Dict con información del token
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT 
                    id, jti, cognito_user_id, cognito_email,
                    issued_at, expires_at, is_revoked, revoked_at, revocation_reason
                FROM "identity-manager-tokens-tbl"
                WHERE id = %s
            """
            
            cursor.execute(query, (token_id,))
            token = cursor.fetchone()
            
            if not token:
                raise ValueError(f'Token no encontrado: {token_id}')
            
            return dict(token)
    
    def revoke_token(self, token_id: str, reason: str) -> Dict[str, Any]:
        """
        Revocar un token
        
        Args:
            token_id: ID del token
            reason: Razón de la revocación
            
        Returns:
            Dict con información del token revocado
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                UPDATE "identity-manager-tokens-tbl"
                SET is_revoked = TRUE,
                    revoked_at = CURRENT_TIMESTAMP,
                    revocation_reason = %s
                WHERE id = %s
                RETURNING id, jti, revoked_at
            """
            
            cursor.execute(query, (reason, token_id))
            result = cursor.fetchone()
            
            if not result:
                raise ValueError(f'Token no encontrado: {token_id}')
            
            return {
                'token_id': str(result['id']),
                'jti': result['jti'],
                'revoked_at': result['revoked_at'].isoformat(),
                'reason': reason
            }
    
    def restore_token(self, token_id: str) -> Dict[str, Any]:
        """
        Restaurar un token revocado (quitar la revocación)
        
        Args:
            token_id: ID del token
            
        Returns:
            Dict con información del token restaurado
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                UPDATE "identity-manager-tokens-tbl"
                SET is_revoked = FALSE,
                    revoked_at = NULL,
                    revocation_reason = NULL
                WHERE id = %s
                RETURNING id, jti, cognito_user_id, expires_at
            """
            
            cursor.execute(query, (token_id,))
            result = cursor.fetchone()
            
            if not result:
                raise ValueError(f'Token no encontrado: {token_id}')
            
            return {
                'token_id': str(result['id']),
                'jti': result['jti'],
                'user_id': result['cognito_user_id'],
                'expires_at': result['expires_at'].isoformat() if result['expires_at'] else None,
                'message': 'Token restored successfully'
            }
    
    def delete_token(self, token_id: str) -> bool:
        """
        Eliminar token permanentemente
        
        Args:
            token_id: ID del token
            
        Returns:
            True si se eliminó correctamente
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = 'DELETE FROM "identity-manager-tokens-tbl" WHERE id = %s'
            cursor.execute(query, (token_id,))
            
            if cursor.rowcount == 0:
                raise ValueError(f'Token no encontrado: {token_id}')
            
            return True
    
    def count_active_tokens(self, user_id: str) -> int:
        """
        Contar tokens activos de un usuario
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Número de tokens activos
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT COUNT(*) 
                FROM "identity-manager-tokens-tbl"
                WHERE cognito_user_id = %s 
                AND is_revoked = FALSE 
                AND expires_at > CURRENT_TIMESTAMP
            """
            
            cursor.execute(query, (user_id,))
            count = cursor.fetchone()[0]
            
            return count
    
    # ========================================================================
    # OPERACIONES DE PERFILES
    # ========================================================================
    
    def list_profiles(
        self,
        application_id: Optional[str] = None,
        is_active: bool = True
    ) -> Dict[str, Any]:
        """
        Listar perfiles de inferencia
        
        Args:
            application_id: Filtrar por aplicación
            is_active: Filtrar por estado activo
            
        Returns:
            Dict con lista de perfiles
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT 
                    p.id as profile_id,
                    p.profile_name,
                    p.cognito_group_name as cognito_group,
                    p.model_arn,
                    p.is_active,
                    a.name as application,
                    m.model_id,
                    m.model_name
                FROM "identity-manager-profiles-tbl" p
                LEFT JOIN "identity-manager-applications-tbl" a ON p.application_id = a.id
                LEFT JOIN "identity-manager-models-tbl" m ON p.model_id = m.id
                WHERE 1=1
            """
            
            params = []
            
            if application_id:
                query += " AND p.application_id = %s"
                params.append(application_id)
            
            if is_active:
                query += " AND p.is_active = TRUE"
            
            query += " ORDER BY p.profile_name"
            
            cursor.execute(query, params)
            profiles = cursor.fetchall()
            
            return {
                'profiles': [dict(profile) for profile in profiles]
            }
    
    def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtener información de un perfil
        
        Args:
            profile_id: ID del perfil
            
        Returns:
            Dict con información del perfil o None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT 
                    p.id as profile_id,
                    p.profile_name,
                    p.cognito_group_name,
                    p.model_arn,
                    p.is_active,
                    a.name as application_name,
                    m.model_id,
                    m.model_name
                FROM "identity-manager-profiles-tbl" p
                LEFT JOIN "identity-manager-applications-tbl" a ON p.application_id = a.id
                LEFT JOIN "identity-manager-models-tbl" m ON p.model_id = m.id
                WHERE p.id = %s
            """
            
            cursor.execute(query, (profile_id,))
            profile = cursor.fetchone()
            
            return dict(profile) if profile else None
    
    # ========================================================================
    # OPERACIONES DE USUARIOS (LIMPIEZA DE DATOS)
    # ========================================================================
    
    def delete_user_data(self, user_id: str) -> Dict[str, int]:
        """
        Eliminar todos los datos de un usuario en BD
        
        Args:
            user_id: ID del usuario en Cognito
            
        Returns:
            Dict con contadores de registros eliminados
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Eliminar tokens
            cursor.execute(
                'DELETE FROM "identity-manager-tokens-tbl" WHERE cognito_user_id = %s',
                (user_id,)
            )
            tokens_deleted = cursor.rowcount
            
            # Eliminar permisos de aplicación
            cursor.execute(
                'DELETE FROM "identity-manager-app-permissions-tbl" WHERE cognito_user_id = %s',
                (user_id,)
            )
            app_permissions_deleted = cursor.rowcount
            
            # Eliminar permisos de módulos
            cursor.execute(
                'DELETE FROM "identity-manager-module-permissions-tbl" WHERE cognito_user_id = %s',
                (user_id,)
            )
            module_permissions_deleted = cursor.rowcount
            
            return {
                'tokens_deleted': tokens_deleted,
                'app_permissions_deleted': app_permissions_deleted,
                'module_permissions_deleted': module_permissions_deleted
            }
    
    # ========================================================================
    # OPERACIONES DE CONFIGURACIÓN
    # ========================================================================
    
    def get_config(self) -> Dict[str, Any]:
        """
        Obtener toda la configuración del sistema
        
        Returns:
            Dict con configuración
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT config_key, config_value, description, is_sensitive
                FROM "identity-manager-config-tbl"
                ORDER BY config_key
            """
            
            cursor.execute(query)
            configs = cursor.fetchall()
            
            config_dict = {}
            for config in configs:
                # No exponer valores sensibles
                if config['is_sensitive']:
                    config_dict[config['config_key']] = {
                        'value': '***HIDDEN***',
                        'description': config['description']
                    }
                else:
                    config_dict[config['config_key']] = {
                        'value': config['config_value'],
                        'description': config['description']
                    }
            
            return {'config': config_dict}
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Obtener un valor de configuración específico
        
        Args:
            key: Clave de configuración
            default: Valor por defecto si no existe
            
        Returns:
            Valor de configuración
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT config_value 
                FROM "identity-manager-config-tbl"
                WHERE config_key = %s
            """
            
            cursor.execute(query, (key,))
            result = cursor.fetchone()
            
            return result[0] if result else default
    
    # ========================================================================
    # OPERACIONES DE AUDITORÍA
    # ========================================================================
    
    def log_audit(
        self,
        operation_type: str,
        resource_type: str,
        resource_id: str,
        cognito_user_id: Optional[str] = None,
        cognito_email: Optional[str] = None,
        previous_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None,
        request_id: Optional[str] = None
    ) -> bool:
        """
        Registrar operación en auditoría
        
        Args:
            operation_type: Tipo de operación (CREATE, UPDATE, DELETE, etc.)
            resource_type: Tipo de recurso afectado
            resource_id: ID del recurso
            cognito_user_id: ID del usuario que realiza la operación
            cognito_email: Email del usuario que realiza la operación
            previous_value: Valor anterior (para updates/deletes)
            new_value: Valor nuevo (para creates/updates)
            request_id: ID del request (no usado actualmente, para compatibilidad)
            
        Returns:
            True si se registró correctamente
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    INSERT INTO "identity-manager-audit-tbl"
                    (operation_type, resource_type, resource_id, cognito_user_id, cognito_email, previous_value, new_value)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                
                # Convertir datetime a string para serialización JSON
                def serialize_value(value):
                    if value is None:
                        return None
                    # Crear una copia para no modificar el original
                    serialized = {}
                    for key, val in value.items():
                        if isinstance(val, datetime):
                            serialized[key] = val.isoformat()
                        else:
                            serialized[key] = val
                    return json.dumps(serialized)
                
                cursor.execute(query, (
                    operation_type,
                    resource_type,
                    resource_id,
                    cognito_user_id,
                    cognito_email,
                    serialize_value(previous_value),
                    serialize_value(new_value)
                ))
                
                logger.info(f"Audit log registered: {operation_type} on {resource_type}/{resource_id} by {cognito_email or cognito_user_id or 'system'}")
                return True
        except Exception as e:
            logger.error(f"Error registrando auditoría: {e}")
            # No fallar la operación principal si falla la auditoría
            return False
    
    # ========================================================================
    # OPERACIONES DE CUOTAS DE USUARIOS
    # ========================================================================
    
    def get_user_quotas_today(self) -> List[Dict[str, Any]]:
        """
        Obtener cuotas de usuarios para el día actual
        
        Retorna información de cuotas incluyendo:
        - Usuarios con uso en el día actual
        - Peticiones realizadas hoy
        - Límite diario establecido
        - Estado (ACTIVE, BLOCKED, ADMIN_SAFE)
        - Fecha de desbloqueo si aplica
        
        Returns:
            Lista de diccionarios con información de cuotas
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT 
                    cognito_user_id,
                    cognito_email,
                    person,
                    team,
                    requests_today,
                    COALESCE(daily_request_limit, 1000) as daily_limit,
                    is_blocked,
                    administrative_safe,
                    blocked_until,
                    CASE 
                        WHEN administrative_safe = true THEN 'ADMIN_SAFE'
                        WHEN is_blocked = true THEN 'BLOCKED'
                        ELSE 'ACTIVE'
                    END as status
                FROM "bedrock-proxy-user-quotas-tbl"
                WHERE quota_date = CURRENT_DATE
                    AND (
                        is_blocked = true 
                        OR administrative_safe = true 
                        OR requests_today > 0
                    )
                ORDER BY requests_today DESC;
            """
            
            cursor.execute(query)
            quotas = cursor.fetchall()
            
            # Convertir a lista de diccionarios y formatear fechas
            result = []
            for quota in quotas:
                quota_dict = dict(quota)
                # Formatear blocked_until si existe
                if quota_dict.get('blocked_until'):
                    quota_dict['blocked_until'] = quota_dict['blocked_until'].isoformat()
                result.append(quota_dict)
            
            logger.info(f"Retrieved {len(result)} user quotas for today")
            return result
    
    def block_user_quota(
        self,
        cognito_user_id: str,
        blocked_until: str,
        block_reason: str,
        performed_by: str
    ) -> Dict[str, Any]:
        """
        Bloquear manualmente a un usuario hasta una fecha específica
        
        Args:
            cognito_user_id: ID del usuario en Cognito
            blocked_until: Fecha/hora de fin de bloqueo (ISO 8601)
            block_reason: Razón del bloqueo
            performed_by: Email del administrador que realiza el bloqueo
            
        Returns:
            Dict con información del usuario bloqueado
            
        Raises:
            ValueError: Si el usuario no existe, ya está bloqueado o está en Admin-Safe
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Verificar estado actual del usuario
            check_query = """
                SELECT cognito_user_id, cognito_email, person, team,
                       is_blocked, administrative_safe
                FROM "bedrock-proxy-user-quotas-tbl"
                WHERE cognito_user_id = %s
            """
            cursor.execute(check_query, (cognito_user_id,))
            user = cursor.fetchone()
            
            if not user:
                raise ValueError(f"Usuario no encontrado: {cognito_user_id}")
            
            if user['is_blocked']:
                raise ValueError("Usuario ya está bloqueado")
            
            if user['administrative_safe']:
                raise ValueError("No se puede bloquear un usuario en Admin-Safe")
            
            # Bloquear usuario
            update_query = """
                UPDATE "bedrock-proxy-user-quotas-tbl"
                SET is_blocked = true,
                    blocked_at = CURRENT_TIMESTAMP,
                    blocked_until = %s,
                    blocked_by = %s,
                    block_reason = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE cognito_user_id = %s
                RETURNING cognito_user_id, cognito_email, person, team,
                          blocked_at, blocked_until, blocked_by, block_reason
            """
            
            cursor.execute(update_query, (blocked_until, performed_by, block_reason, cognito_user_id))
            result = cursor.fetchone()
            
            if not result:
                raise ValueError("Error al bloquear usuario")
            
            # Registrar en historial
            history_query = """
                INSERT INTO "bedrock-proxy-quota-blocks-history-tbl"
                (cognito_user_id, cognito_email, block_date, blocked_at, 
                 blocked_until, unblock_type, requests_count, daily_limit,
                 unblocked_by, unblock_reason, team, person)
                SELECT 
                    cognito_user_id, cognito_email, CURRENT_DATE, CURRENT_TIMESTAMP,
                    %s, 'MANUAL_BLOCK', requests_today, daily_request_limit,
                    %s, %s, team, person
                FROM "bedrock-proxy-user-quotas-tbl"
                WHERE cognito_user_id = %s
            """
            cursor.execute(history_query, (blocked_until, performed_by, block_reason, cognito_user_id))
            
            # Formatear resultado
            result_dict = dict(result)
            result_dict['status'] = 'BLOCKED'
            result_dict['blocked_at'] = result_dict['blocked_at'].isoformat()
            result_dict['blocked_until'] = result_dict['blocked_until'].isoformat()
            
            logger.info(f"User {cognito_user_id} blocked until {blocked_until} by {performed_by}")
            return result_dict
    
    def unblock_user_quota(
        self,
        cognito_user_id: str,
        unblock_reason: str,
        performed_by: str
    ) -> Dict[str, Any]:
        """
        Desbloquear manualmente a un usuario o quitar Admin-Safe
        
        Comportamiento:
        - Si usuario está BLOCKED: quita el bloqueo
        - Si usuario está ADMIN_SAFE: quita la protección
        
        Args:
            cognito_user_id: ID del usuario en Cognito
            unblock_reason: Razón del desbloqueo
            performed_by: Email del administrador que realiza el desbloqueo
            
        Returns:
            Dict con información del usuario desbloqueado
            
        Raises:
            ValueError: Si el usuario no existe o no está bloqueado/admin-safe
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Verificar estado actual del usuario
            check_query = """
                SELECT cognito_user_id, cognito_email, person, team,
                       is_blocked, administrative_safe, blocked_until, block_reason
                FROM "bedrock-proxy-user-quotas-tbl"
                WHERE cognito_user_id = %s
            """
            cursor.execute(check_query, (cognito_user_id,))
            user = cursor.fetchone()
            
            if not user:
                raise ValueError(f"Usuario no encontrado: {cognito_user_id}")
            
            if not user['is_blocked'] and not user['administrative_safe']:
                raise ValueError("Usuario no está bloqueado ni en Admin-Safe")
            
            previous_state = 'ADMIN_SAFE' if user['administrative_safe'] else 'BLOCKED'
            
            # Desbloquear usuario o quitar Admin-Safe
            if user['is_blocked']:
                # Desbloquear usuario BLOCKED
                update_query = """
                    UPDATE "bedrock-proxy-user-quotas-tbl"
                    SET is_blocked = false,
                        blocked_until = NULL,
                        unblocked_at = CURRENT_TIMESTAMP,
                        unblocked_by = %s,
                        unblock_reason = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE cognito_user_id = %s
                    RETURNING cognito_user_id, cognito_email, person, team, unblocked_at
                """
                cursor.execute(update_query, (performed_by, unblock_reason, cognito_user_id))
            else:
                # Quitar Admin-Safe
                update_query = """
                    UPDATE "bedrock-proxy-user-quotas-tbl"
                    SET administrative_safe = false,
                        administrative_safe_set_by = NULL,
                        administrative_safe_set_at = NULL,
                        administrative_safe_reason = NULL,
                        unblocked_at = CURRENT_TIMESTAMP,
                        unblocked_by = %s,
                        unblock_reason = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE cognito_user_id = %s
                    RETURNING cognito_user_id, cognito_email, person, team, unblocked_at
                """
                cursor.execute(update_query, (performed_by, unblock_reason, cognito_user_id))
            
            result = cursor.fetchone()
            
            if not result:
                raise ValueError("Error al desbloquear usuario")
            
            # Registrar en historial
            history_query = """
                INSERT INTO "bedrock-proxy-quota-blocks-history-tbl"
                (cognito_user_id, cognito_email, block_date, unblocked_at,
                 unblock_type, requests_count, daily_limit,
                 unblocked_by, unblock_reason, team, person)
                SELECT 
                    cognito_user_id, cognito_email, CURRENT_DATE, CURRENT_TIMESTAMP,
                    %s, requests_today, daily_request_limit,
                    %s, %s, team, person
                FROM "bedrock-proxy-user-quotas-tbl"
                WHERE cognito_user_id = %s
            """
            unblock_type = 'REMOVE_ADMIN_SAFE' if previous_state == 'ADMIN_SAFE' else 'MANUAL_UNBLOCK'
            cursor.execute(history_query, (unblock_type, performed_by, unblock_reason, cognito_user_id))
            
            # Formatear resultado
            result_dict = dict(result)
            result_dict['status'] = 'ACTIVE'
            result_dict['previous_state'] = previous_state
            result_dict['unblocked_at'] = result_dict['unblocked_at'].isoformat()
            result_dict['unblocked_by'] = performed_by
            result_dict['unblock_reason'] = unblock_reason
            
            logger.info(f"User {cognito_user_id} unblocked (from {previous_state}) by {performed_by}")
            return result_dict
    
    def set_admin_safe_quota(
        self,
        cognito_user_id: str,
        admin_safe_reason: str,
        performed_by: str
    ) -> Dict[str, Any]:
        """
        Establecer protección Admin-Safe para un usuario
        
        Puede aplicarse a usuarios ACTIVE (protección preventiva) o BLOCKED (protección y desbloqueo).
        Si el usuario está bloqueado, se desbloquea automáticamente al establecer Admin-Safe.
        
        Args:
            cognito_user_id: ID del usuario en Cognito
            admin_safe_reason: Razón para establecer Admin-Safe
            performed_by: Email del administrador que realiza la operación
            
        Returns:
            Dict con información del usuario protegido
            
        Raises:
            ValueError: Si el usuario no existe o ya está en Admin-Safe
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Verificar estado actual del usuario
            check_query = """
                SELECT cognito_user_id, cognito_email, person, team,
                       is_blocked, administrative_safe
                FROM "bedrock-proxy-user-quotas-tbl"
                WHERE cognito_user_id = %s
            """
            cursor.execute(check_query, (cognito_user_id,))
            user = cursor.fetchone()
            
            if not user:
                raise ValueError(f"Usuario no encontrado: {cognito_user_id}")
            
            if user['administrative_safe']:
                raise ValueError("Usuario ya está en Admin-Safe")
            
            previous_state = 'BLOCKED' if user['is_blocked'] else 'ACTIVE'
            
            # Establecer Admin-Safe (y desbloquear si estaba bloqueado)
            update_query = """
                UPDATE "bedrock-proxy-user-quotas-tbl"
                SET administrative_safe = true,
                    administrative_safe_set_by = %s,
                    administrative_safe_set_at = CURRENT_TIMESTAMP,
                    administrative_safe_reason = %s,
                    is_blocked = false,
                    blocked_until = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE cognito_user_id = %s
                RETURNING cognito_user_id, cognito_email, person, team,
                          administrative_safe_set_at, administrative_safe_set_by,
                          administrative_safe_reason
            """
            
            cursor.execute(update_query, (performed_by, admin_safe_reason, cognito_user_id))
            result = cursor.fetchone()
            
            if not result:
                raise ValueError("Error al establecer Admin-Safe")
            
            # Registrar en historial
            history_query = """
                INSERT INTO "bedrock-proxy-quota-blocks-history-tbl"
                (cognito_user_id, cognito_email, block_date, unblocked_at,
                 unblock_type, requests_count, daily_limit,
                 unblocked_by, unblock_reason, team, person)
                SELECT 
                    cognito_user_id, cognito_email, CURRENT_DATE, CURRENT_TIMESTAMP,
                    'SET_ADMIN_SAFE', requests_today, daily_request_limit,
                    %s, %s, team, person
                FROM "bedrock-proxy-user-quotas-tbl"
                WHERE cognito_user_id = %s
            """
            cursor.execute(history_query, (performed_by, admin_safe_reason, cognito_user_id))
            
            # Formatear resultado
            result_dict = dict(result)
            result_dict['status'] = 'ADMIN_SAFE'
            result_dict['previous_state'] = previous_state
            result_dict['administrative_safe'] = True
            result_dict['administrative_safe_set_at'] = result_dict['administrative_safe_set_at'].isoformat()
            
            logger.info(f"User {cognito_user_id} set to Admin-Safe (from {previous_state}) by {performed_by}")
            return result_dict
