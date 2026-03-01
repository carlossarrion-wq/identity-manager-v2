"""
Permissions Service
===================
Servicio para gestión de permisos de acceso a aplicaciones y módulos
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from psycopg2.extras import RealDictCursor

from services.database_service import DatabaseService

logger = logging.getLogger()


class PermissionsService:
    """
    Servicio para gestión de permisos de usuarios sobre aplicaciones y módulos
    """
    
    def __init__(self):
        """Inicializar servicio"""
        self.db = DatabaseService()
    
    # ========================================================================
    # ASIGNACIÓN DE PERMISOS
    # ========================================================================
    
    def assign_app_permission(
        self,
        user_id: str,
        user_email: str,
        app_id: str,
        permission_type_id: str,
        duration_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Asignar permiso de aplicación a un usuario
        
        Args:
            user_id: ID del usuario en Cognito
            user_email: Email del usuario
            app_id: ID de la aplicación
            permission_type_id: ID del tipo de permiso
            duration_days: Duración en días (None = indefinido)
            
        Returns:
            Dict con información del permiso asignado
        """
        logger.info(f"Asignando permiso de aplicación: user={user_id}, app={app_id}")
        
        # Calcular fecha de expiración
        expires_at = None
        if duration_days:
            expires_at = datetime.now() + timedelta(days=duration_days)
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Verificar si ya existe el permiso
            check_query = """
                SELECT id, is_active 
                FROM "identity-manager-app-permissions-tbl"
                WHERE cognito_user_id = %s AND application_id = %s
            """
            cursor.execute(check_query, (user_id, app_id))
            existing = cursor.fetchone()
            
            if existing:
                # Actualizar permiso existente
                update_query = """
                    UPDATE "identity-manager-app-permissions-tbl"
                    SET permission_type_id = %s,
                        expires_at = %s,
                        is_active = TRUE,
                        granted_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING id, granted_at
                """
                cursor.execute(update_query, (permission_type_id, expires_at, existing['id']))
                result = cursor.fetchone()
                action = 'updated'
            else:
                # Crear nuevo permiso
                insert_query = """
                    INSERT INTO "identity-manager-app-permissions-tbl"
                    (cognito_user_id, cognito_email, application_id, permission_type_id, expires_at)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, granted_at
                """
                cursor.execute(insert_query, (user_id, user_email, app_id, permission_type_id, expires_at))
                result = cursor.fetchone()
                action = 'created'
            
            # Obtener información completa del permiso
            permission_info = self._get_app_permission_info(cursor, result['id'])
            
            return {
                'success': True,
                'action': action,
                'permission': permission_info,
                'message': f'Permiso de aplicación {action} correctamente'
            }
    
    def assign_module_permission(
        self,
        user_id: str,
        user_email: str,
        module_id: str,
        permission_type_id: str,
        duration_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Asignar permiso de módulo a un usuario
        
        Args:
            user_id: ID del usuario en Cognito
            user_email: Email del usuario
            module_id: ID del módulo
            permission_type_id: ID del tipo de permiso
            duration_days: Duración en días (None = indefinido)
            
        Returns:
            Dict con información del permiso asignado
        """
        logger.info(f"Asignando permiso de módulo: user={user_id}, module={module_id}")
        
        # Calcular fecha de expiración
        expires_at = None
        if duration_days:
            expires_at = datetime.now() + timedelta(days=duration_days)
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Verificar si ya existe el permiso
            check_query = """
                SELECT id, is_active 
                FROM "identity-manager-module-permissions-tbl"
                WHERE cognito_user_id = %s AND application_module_id = %s
            """
            cursor.execute(check_query, (user_id, module_id))
            existing = cursor.fetchone()
            
            if existing:
                # Actualizar permiso existente
                update_query = """
                    UPDATE "identity-manager-module-permissions-tbl"
                    SET permission_type_id = %s,
                        expires_at = %s,
                        is_active = TRUE,
                        granted_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING id, granted_at
                """
                cursor.execute(update_query, (permission_type_id, expires_at, existing['id']))
                result = cursor.fetchone()
                action = 'updated'
            else:
                # Crear nuevo permiso
                insert_query = """
                    INSERT INTO "identity-manager-module-permissions-tbl"
                    (cognito_user_id, cognito_email, application_module_id, permission_type_id, expires_at)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, granted_at
                """
                cursor.execute(insert_query, (user_id, user_email, module_id, permission_type_id, expires_at))
                result = cursor.fetchone()
                action = 'created'
            
            # Obtener información completa del permiso
            permission_info = self._get_module_permission_info(cursor, result['id'])
            
            return {
                'success': True,
                'action': action,
                'permission': permission_info,
                'message': f'Permiso de módulo {action} correctamente'
            }
    
    # ========================================================================
    # REVOCACIÓN DE PERMISOS
    # ========================================================================
    
    def revoke_app_permission(self, user_id: str, app_id: str) -> Dict[str, Any]:
        """
        Revocar permiso de aplicación
        
        Args:
            user_id: ID del usuario
            app_id: ID de la aplicación
            
        Returns:
            Dict con resultado de la operación
        """
        logger.info(f"Revocando permiso de aplicación: user={user_id}, app={app_id}")
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                UPDATE "identity-manager-app-permissions-tbl"
                SET is_active = FALSE
                WHERE cognito_user_id = %s AND application_id = %s
                RETURNING id
            """
            
            cursor.execute(query, (user_id, app_id))
            result = cursor.fetchone()
            
            if not result:
                raise ValueError('Permiso no encontrado')
            
            return {
                'success': True,
                'permission_id': str(result['id']),
                'message': 'Permiso de aplicación revocado correctamente'
            }
    
    def revoke_module_permission(self, user_id: str, module_id: str) -> Dict[str, Any]:
        """
        Revocar permiso de módulo
        
        Args:
            user_id: ID del usuario
            module_id: ID del módulo
            
        Returns:
            Dict con resultado de la operación
        """
        logger.info(f"Revocando permiso de módulo: user={user_id}, module={module_id}")
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                UPDATE "identity-manager-module-permissions-tbl"
                SET is_active = FALSE
                WHERE cognito_user_id = %s AND application_module_id = %s
                RETURNING id
            """
            
            cursor.execute(query, (user_id, module_id))
            result = cursor.fetchone()
            
            if not result:
                raise ValueError('Permiso no encontrado')
            
            return {
                'success': True,
                'permission_id': str(result['id']),
                'message': 'Permiso de módulo revocado correctamente'
            }
    
    # ========================================================================
    # CONSULTA DE PERMISOS
    # ========================================================================
    
    def get_user_permissions(self, user_id: str) -> Dict[str, Any]:
        """
        Obtener todos los permisos de un usuario
        
        Args:
            user_id: ID del usuario o email
            
        Returns:
            Dict con permisos del usuario
        """
        logger.info(f"Obteniendo permisos del usuario: {user_id}")
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Permisos de aplicaciones - buscar por user_id o email
            app_query = """
                SELECT 
                    p.id as permission_id,
                    'application' as scope,
                    p.cognito_user_id as user_id,
                    p.cognito_email as email,
                    a.id as resource_id,
                    a.name as resource_name,
                    NULL as parent_application_id,
                    NULL as parent_application_name,
                    pt.name as permission_type,
                    pt.level as permission_level,
                    p.is_active,
                    p.granted_at,
                    p.expires_at,
                    CASE 
                        WHEN NOT p.is_active THEN 'revoked'
                        WHEN p.expires_at IS NOT NULL AND p.expires_at < CURRENT_TIMESTAMP THEN 'expired'
                        ELSE 'active'
                    END as status
                FROM "identity-manager-app-permissions-tbl" p
                JOIN "identity-manager-applications-tbl" a ON p.application_id = a.id
                JOIN "identity-manager-permission-types-tbl" pt ON p.permission_type_id = pt.id
                WHERE p.cognito_user_id = %s OR p.cognito_email = %s
            """
            
            cursor.execute(app_query, (user_id, user_id))
            app_permissions = [dict(row) for row in cursor.fetchall()]
            
            # Permisos de módulos - buscar por user_id o email
            module_query = """
                SELECT 
                    p.id as permission_id,
                    'module' as scope,
                    p.cognito_user_id as user_id,
                    p.cognito_email as email,
                    m.id as resource_id,
                    m.name as resource_name,
                    a.id as parent_application_id,
                    a.name as parent_application_name,
                    pt.name as permission_type,
                    pt.level as permission_level,
                    p.is_active,
                    p.granted_at,
                    p.expires_at,
                    CASE 
                        WHEN NOT p.is_active THEN 'revoked'
                        WHEN p.expires_at IS NOT NULL AND p.expires_at < CURRENT_TIMESTAMP THEN 'expired'
                        ELSE 'active'
                    END as status
                FROM "identity-manager-module-permissions-tbl" p
                JOIN "identity-manager-modules-tbl" m ON p.application_module_id = m.id
                JOIN "identity-manager-applications-tbl" a ON m.application_id = a.id
                JOIN "identity-manager-permission-types-tbl" pt ON p.permission_type_id = pt.id
                WHERE p.cognito_user_id = %s OR p.cognito_email = %s
            """
            
            cursor.execute(module_query, (user_id, user_id))
            module_permissions = [dict(row) for row in cursor.fetchall()]
            
            all_permissions = app_permissions + module_permissions
            
            return {
                'user_id': user_id,
                'permissions': all_permissions,
                'total_count': len(all_permissions),
                'app_permissions_count': len(app_permissions),
                'module_permissions_count': len(module_permissions)
            }
    
    def list_all_permissions(self) -> Dict[str, Any]:
        """
        Listar todos los permisos del sistema
        
        Returns:
            Dict con todos los permisos
        """
        logger.info("Listando todos los permisos del sistema")
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Usar la vista consolidada
            query = """
                SELECT 
                    cognito_user_id as user_id,
                    cognito_email as email,
                    permission_scope as scope,
                    resource_name,
                    resource_id,
                    parent_application_id,
                    permission_type,
                    permission_level,
                    is_active,
                    granted_at,
                    expires_at,
                    CASE 
                        WHEN NOT is_active THEN 'revoked'
                        WHEN expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP THEN 'expired'
                        ELSE 'active'
                    END as status
                FROM "v_user_permissions"
                ORDER BY cognito_email, permission_scope, resource_name
            """
            
            cursor.execute(query)
            permissions = [dict(row) for row in cursor.fetchall()]
            
            return {
                'permissions': permissions,
                'total_count': len(permissions)
            }
    
    # ========================================================================
    # CATÁLOGOS
    # ========================================================================
    
    def list_permission_types(self) -> Dict[str, Any]:
        """
        Listar tipos de permisos disponibles
        
        Returns:
            Dict con tipos de permisos
        """
        logger.info("Listando tipos de permisos")
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT id, name, description, level
                FROM "identity-manager-permission-types-tbl"
                ORDER BY level
            """
            
            cursor.execute(query)
            permission_types = [dict(row) for row in cursor.fetchall()]
            
            return {
                'permission_types': permission_types
            }
    
    def list_applications(self) -> Dict[str, Any]:
        """
        Listar todas las aplicaciones disponibles
        
        Returns:
            Dict con aplicaciones
        """
        logger.info("Listando aplicaciones")
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT 
                    id as application_id,
                    name as application_name,
                    description,
                    display_order,
                    is_active
                FROM "identity-manager-applications-tbl"
                WHERE is_active = TRUE
                ORDER BY display_order, name
            """
            
            cursor.execute(query)
            applications = [dict(row) for row in cursor.fetchall()]
            
            return {
                'applications': applications
            }
    
    def list_modules(self, app_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Listar módulos (opcionalmente filtrados por aplicación)
        
        Args:
            app_id: ID de la aplicación (opcional)
            
        Returns:
            Dict con módulos
        """
        logger.info(f"Listando módulos{f' de aplicación {app_id}' if app_id else ''}")
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT 
                    m.id as module_id,
                    m.name as module_name,
                    m.description,
                    m.is_active,
                    m.application_id,
                    a.name as application_name
                FROM "identity-manager-modules-tbl" m
                JOIN "identity-manager-applications-tbl" a ON m.application_id = a.id
                WHERE m.is_active = TRUE
            """
            
            params = []
            if app_id:
                query += " AND m.application_id = %s"
                params.append(app_id)
            
            query += " ORDER BY a.name, m.display_order, m.name"
            
            cursor.execute(query, params)
            modules = [dict(row) for row in cursor.fetchall()]
            
            return {
                'modules': modules
            }
    
    # ========================================================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ========================================================================
    
    def _get_app_permission_info(self, cursor, permission_id: str) -> Dict[str, Any]:
        """
        Obtener información completa de un permiso de aplicación
        
        Args:
            cursor: Cursor de BD
            permission_id: ID del permiso
            
        Returns:
            Dict con información del permiso
        """
        query = """
            SELECT 
                p.id as permission_id,
                p.cognito_user_id as user_id,
                p.cognito_email as email,
                a.id as application_id,
                a.name as application_name,
                pt.name as permission_type,
                pt.level as permission_level,
                p.granted_at,
                p.expires_at,
                p.is_active
            FROM "identity-manager-app-permissions-tbl" p
            JOIN "identity-manager-applications-tbl" a ON p.application_id = a.id
            JOIN "identity-manager-permission-types-tbl" pt ON p.permission_type_id = pt.id
            WHERE p.id = %s
        """
        
        cursor.execute(query, (permission_id,))
        result = cursor.fetchone()
        
        return dict(result) if result else {}
    
    def _get_module_permission_info(self, cursor, permission_id: str) -> Dict[str, Any]:
        """
        Obtener información completa de un permiso de módulo
        
        Args:
            cursor: Cursor de BD
            permission_id: ID del permiso
            
        Returns:
            Dict con información del permiso
        """
        query = """
            SELECT 
                p.id as permission_id,
                p.cognito_user_id as user_id,
                p.cognito_email as email,
                m.id as module_id,
                m.name as module_name,
                a.id as application_id,
                a.name as application_name,
                pt.name as permission_type,
                pt.level as permission_level,
                p.granted_at,
                p.expires_at,
                p.is_active
            FROM "identity-manager-module-permissions-tbl" p
            JOIN "identity-manager-modules-tbl" m ON p.application_module_id = m.id
            JOIN "identity-manager-applications-tbl" a ON m.application_id = a.id
            JOIN "identity-manager-permission-types-tbl" pt ON p.permission_type_id = pt.id
            WHERE p.id = %s
        """
        
        cursor.execute(query, (permission_id,))
        result = cursor.fetchone()
        
        return dict(result) if result else {}
