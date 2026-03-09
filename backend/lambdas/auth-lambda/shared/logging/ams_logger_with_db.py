"""
AMS Logger con Persistencia en Base de Datos
=============================================
Extiende AMSLogger para persistir eventos importantes en PostgreSQL.
IMPORTANTE: Solo hace INSERT, nunca modifica ni borra registros.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from shared.ams_logging import AMSLogger
from shared.services.database_service import DatabaseService


class AMSLoggerWithDB(AMSLogger):
    """
    Logger AMS que además persiste eventos en base de datos.
    Hereda toda la funcionalidad de AMSLogger y agrega persistencia.
    """
    
    def __init__(self, config, persist_to_db: bool = True):
        """
        Inicializar logger con persistencia opcional en BD.
        
        Args:
            config: Configuración del logger (LogConfig)
            persist_to_db: Si debe persistir en BD (default: True)
        """
        super().__init__(config)
        self.persist_to_db = persist_to_db
        self.db = DatabaseService() if persist_to_db else None
        
        # Eventos que deben persistirse en BD
        self.events_to_persist = {
            'AUTH_REQUEST_RECEIVED',
            'AUTH_REQUEST_COMPLETED',
            'AUTH_VALIDATION_ERROR',
            'AUTH_SYSTEM_ERROR',
            'LOGIN_SUCCESS',
            'LOGIN_FAILED',
            'PASSWORD_CHANGE',
            'TOKEN_VERIFY',
            'LOGOUT'
        }
    
    def _persist_to_database(
        self,
        event_name: str,
        log_level: str,
        message: str,
        **kwargs
    ):
        """
        Persiste el evento en la base de datos (solo INSERT).
        
        Args:
            event_name: Nombre del evento
            log_level: Nivel de log
            message: Mensaje del evento
            **kwargs: Campos adicionales del evento
        """
        if not self.persist_to_db or not self.db:
            return
        
        # Persistir todos los eventos que empiecen con AUTH_ o sean de la lista específica
        # Esto captura todos los eventos de autenticación automáticamente
        should_persist = (
            event_name.startswith('AUTH_') or 
            event_name in self.events_to_persist
        )
        
        if not should_persist:
            return
        
        try:
            # Extraer información del evento
            cognito_user_id = kwargs.get('cognito_user_id')
            cognito_email = kwargs.get('email') or kwargs.get('cognito_email')
            ip_address = kwargs.get('ip_address')
            user_agent = kwargs.get('user_agent')
            
            # Determinar operation_type basado en event_name
            operation_type = self._map_event_to_operation(event_name, log_level)
            
            # Preparar new_value con toda la información del evento
            new_value = {
                'event_name': event_name,
                'log_level': log_level,
                'message': message,
                'trace_id': self.context.trace_id if hasattr(self, 'context') and self.context else None,
                'request_id': self.context.request_id if hasattr(self, 'context') and self.context else None,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Agregar campos adicionales (excepto los sensibles)
            for key, value in kwargs.items():
                if key not in ['password', 'token', 'secret', 'api_key']:
                    new_value[key] = value
            
            # INSERT en la tabla de auditoría
            query = """
                INSERT INTO "identity-manager-audit-tbl" (
                    id,
                    cognito_user_id,
                    cognito_email,
                    performed_by_cognito_user_id,
                    performed_by_email,
                    operation_type,
                    resource_type,
                    resource_id,
                    previous_value,
                    new_value,
                    ip_address,
                    user_agent,
                    operation_timestamp
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s
                )
            """
            
            params = (
                str(uuid.uuid4()),  # id
                cognito_user_id,  # cognito_user_id
                cognito_email,  # cognito_email
                cognito_user_id,  # performed_by_cognito_user_id
                cognito_email,  # performed_by_email
                operation_type,  # operation_type
                'AUTHENTICATION',  # resource_type
                None,  # resource_id
                None,  # previous_value
                json.dumps(new_value),  # new_value
                ip_address,  # ip_address
                user_agent,  # user_agent
                datetime.utcnow()  # operation_timestamp
            )
            
            # Usar execute_update para INSERT (no devuelve resultados)
            self.db.execute_update(query, params)
            
        except Exception as e:
            # No fallar si hay error en persistencia, solo logear
            print(f"[AMS Logger] Error al persistir en BD: {e}")
    
    def _map_event_to_operation(self, event_name: str, log_level: str) -> str:
        """
        Mapea el nombre del evento a un operation_type para la BD.
        
        Args:
            event_name: Nombre del evento AMS
            log_level: Nivel de log
            
        Returns:
            operation_type para la tabla de auditoría
        """
        # Mapeo de eventos a operation_type
        mapping = {
            # Eventos de Lambda Handler
            'AUTH_REQUEST_RECEIVED': 'AUTH_REQUEST',
            'AUTH_REQUEST_COMPLETED': 'AUTH_SUCCESS',
            'AUTH_VALIDATION_ERROR': 'AUTH_VALIDATION_ERROR',
            'AUTH_SYSTEM_ERROR': 'AUTH_SYSTEM_ERROR',
            'AUTH_ENDPOINT_NOT_FOUND': 'AUTH_ENDPOINT_NOT_FOUND',
            # Eventos de Auth Service - Login
            'AUTH_LOGIN_ATTEMPT': 'LOGIN_ATTEMPT',
            'AUTH_LOGIN_SUCCESS': 'LOGIN_SUCCESS',
            'AUTH_LOGIN_FAILED': 'LOGIN_FAILED',
            'AUTH_COGNITO_SUCCESS': 'COGNITO_AUTH_SUCCESS',
            'AUTH_PERMISSIONS_LOADED': 'PERMISSIONS_LOADED',
            # Eventos de Auth Service - Token
            'AUTH_TOKEN_VERIFY_ATTEMPT': 'TOKEN_VERIFY_ATTEMPT',
            'AUTH_TOKEN_VERIFY_SUCCESS': 'TOKEN_VERIFY_SUCCESS',
            'AUTH_TOKEN_VERIFY_FAILED': 'TOKEN_VERIFY_FAILED',
            # Eventos de Auth Service - Password Reset (para funcionalidad futura)
            'AUTH_PASSWORD_RESET_ATTEMPT': 'PASSWORD_RESET_ATTEMPT',
            'AUTH_PASSWORD_RESET_SUCCESS': 'PASSWORD_RESET_SUCCESS',
            'AUTH_PASSWORD_RESET_FAILED': 'PASSWORD_RESET_FAILED',
            'AUTH_PASSWORD_RESET_USER_NOT_FOUND': 'PASSWORD_RESET_USER_NOT_FOUND',
            # Eventos de Auth Service - Cambio de Contraseña Temporal a Definitiva
            'AUTH_CHANGE_TEMPORAL_PASSWORD_TO_DEFINITIVE_ATTEMPT': 'CHANGE_TEMPORAL_PASSWORD_ATTEMPT',
            'AUTH_CHANGE_TEMPORAL_PASSWORD_TO_DEFINITIVE_SUCCESS': 'CHANGE_TEMPORAL_PASSWORD_SUCCESS',
            'AUTH_CHANGE_TEMPORAL_PASSWORD_TO_DEFINITIVE_FAILED': 'CHANGE_TEMPORAL_PASSWORD_FAILED',
            # Eventos genéricos
            'LOGIN_SUCCESS': 'LOGIN_SUCCESS',
            'LOGIN_FAILED': 'LOGIN_FAILED',
            'PASSWORD_CHANGE': 'PASSWORD_CHANGE',
            'TOKEN_VERIFY': 'TOKEN_VERIFY',
            'LOGOUT': 'LOGOUT'
        }
        
        return mapping.get(event_name, event_name)
    
    # Override de los métodos de logging para agregar persistencia
    
    def info(self, event_name: str, message: str, **kwargs):
        """Log INFO con persistencia en BD"""
        # Llamar al método original
        super().info(event_name, message, **kwargs)
        # Persistir en BD
        self._persist_to_database(event_name, 'INFO', message, **kwargs)
    
    def warning(self, event_name: str, message: str, **kwargs):
        """Log WARNING con persistencia en BD"""
        super().warning(event_name, message, **kwargs)
        self._persist_to_database(event_name, 'WARN', message, **kwargs)
    
    def error(self, event_name: str, message: str, **kwargs):
        """Log ERROR con persistencia en BD"""
        super().error(event_name, message, **kwargs)
        self._persist_to_database(event_name, 'ERROR', message, **kwargs)
    
    def fatal(self, event_name: str, message: str, **kwargs):
        """Log FATAL con persistencia en BD"""
        super().fatal(event_name, message, **kwargs)
        self._persist_to_database(event_name, 'FATAL', message, **kwargs)
    
    def debug(self, event_name: str, message: str, **kwargs):
        """Log DEBUG (sin persistencia en BD por defecto)"""
        super().debug(event_name, message, **kwargs)
        # DEBUG no se persiste por defecto para no saturar la BD