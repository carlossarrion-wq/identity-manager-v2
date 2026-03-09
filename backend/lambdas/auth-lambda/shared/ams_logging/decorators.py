"""
Decoradores para logging automático
"""

import time
import traceback
from functools import wraps
from typing import Callable, Optional

from .context import LogContext
from .constants import EventOutcome


def log_event(
    event_name: str,
    logger_attr: str = "logger",
    auto_trace: bool = True,
    log_args: bool = False,
    log_result: bool = False
):
    """
    Decorador que registra automáticamente la ejecución de una función.
    
    Args:
        event_name: Nombre del evento a registrar
        logger_attr: Nombre del atributo logger en self (para métodos de clase)
        auto_trace: Si True, genera automáticamente trace_id si no existe
        log_args: Si True, registra los argumentos de la función
        log_result: Si True, registra el resultado de la función
        
    Example:
        @log_event("USER_LOGIN")
        def login(username, password):
            # ...
            return user
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Obtener el logger
            logger = None
            if args and hasattr(args[0], logger_attr):
                logger = getattr(args[0], logger_attr)
            
            # Si no hay logger, ejecutar sin logging
            if logger is None:
                return func(*args, **kwargs)
            
            # Generar trace_id si es necesario
            if auto_trace and not LogContext.get_trace_id():
                LogContext.new_trace()
            
            start_time = time.time()
            metadata = {}
            
            # Registrar argumentos si está habilitado
            if log_args:
                metadata["function_args"] = {
                    "args": [str(arg) for arg in args[1:]] if args else [],
                    "kwargs": {k: str(v) for k, v in kwargs.items()}
                }
            
            try:
                result = func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Registrar resultado si está habilitado
                if log_result and result is not None:
                    metadata["function_result"] = str(result)[:200]  # Limitar tamaño
                
                logger.info(
                    event_name=event_name,
                    message=f"Function {func.__name__} completed successfully",
                    duration_ms=duration_ms,
                    outcome=EventOutcome.SUCCESS,
                    **metadata
                )
                
                return result
                
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                
                logger.error(
                    event_name=event_name,
                    message=f"Function {func.__name__} failed",
                    duration_ms=duration_ms,
                    outcome=EventOutcome.FAILURE,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    error_stack_trace=traceback.format_exc(),
                    **metadata
                )
                raise
        
        return wrapper
    return decorator


def log_operation(event_name: str, logger_attr: str = "logger"):
    """
    Decorador simplificado para operaciones.
    
    Args:
        event_name: Nombre del evento
        logger_attr: Nombre del atributo logger
        
    Example:
        @log_operation("DATA_PROCESS")
        def process_data(self, data):
            # ...
    """
    return log_event(event_name=event_name, logger_attr=logger_attr, auto_trace=True)