"""
Wrapper del logger AMS para Identity Manager
Proporciona configuración centralizada y funciones de utilidad
"""

import os
from typing import Optional
from shared.ams_logging import AMSLogger, LogConfig

# Logger singleton
_logger_instance: Optional[AMSLogger] = None


def configure_logger(
    service_version: str = "1.0.0",
    environment: Optional[str] = None,
    instance_id: Optional[str] = None
) -> AMSLogger:
    """
    Configura el logger global para Identity Manager.
    
    Args:
        service_version: Versión del servicio
        environment: Entorno (dev/pre/pro). Si es None, se lee de ENV
        instance_id: ID de la instancia. Si es None, se lee de ENV
        
    Returns:
        Logger configurado
    """
    global _logger_instance
    
    # Obtener configuración de variables de entorno si no se proporciona
    if environment is None:
        environment = os.environ.get('ENVIRONMENT', 'dev')
    
    if instance_id is None:
        # En Lambda, usar el log stream name como instance_id
        instance_id = os.environ.get('AWS_LAMBDA_LOG_STREAM_NAME')
    
    config = LogConfig(
        service_name="identity-mgmt",
        service_version=service_version,
        environment=environment,
        instance_id=instance_id,
        enable_sanitization=True  # Siempre sanitizar en Identity Manager
    )
    
    _logger_instance = AMSLogger(config)
    return _logger_instance


def get_logger() -> AMSLogger:
    """
    Obtiene el logger configurado.
    Si no está configurado, lo configura con valores por defecto.
    
    Returns:
        Logger configurado
    """
    global _logger_instance
    
    if _logger_instance is None:
        _logger_instance = configure_logger()
    
    return _logger_instance