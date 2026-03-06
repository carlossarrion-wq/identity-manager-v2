"""
Módulo de logging centralizado para Identity Manager
Proporciona acceso simplificado al logger AMS configurado
"""

from .ams_logger_wrapper import get_logger, configure_logger

__all__ = ['get_logger', 'configure_logger']