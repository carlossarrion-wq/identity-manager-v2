"""
Logger principal que implementa la Política de Logs v1.0
"""

import json
import sys
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from contextlib import contextmanager

from .config import LogConfig
from .constants import LogLevel, EventOutcome
from .context import LogContext
from .sanitizer import DataSanitizer


class AMSLogger:
    """
    Logger que implementa la Política de Logs v1.0 de AMS Naturgy.
    
    Características:
    - Logs estructurados en JSON (1 línea por evento)
    - Campos obligatorios siempre presentes
    - Sanitización automática de datos sensibles
    - Trazabilidad con trace_id y request_id
    - Validación de service_name contra inventario oficial
    """
    
    def __init__(self, config: LogConfig):
        """
        Inicializa el logger con la configuración proporcionada.
        
        Args:
            config: Configuración del logger
        """
        self.config = config
        self.sanitizer = DataSanitizer() if config.enable_sanitization else None
    
    def _get_base_log_entry(self) -> Dict[str, Any]:
        """Crea la estructura base del log con campos obligatorios"""
        return {
            "@timestamp": datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
            "service.name": self.config.service_name,
            "service.version": self.config.service_version,
            "labels.environment": self.config.environment,
        }
    
    def _add_optional_fields(self, entry: Dict[str, Any]):
        """Añade campos opcionales si están disponibles"""
        if self.config.instance_id:
            entry["service.instance.id"] = self.config.instance_id
        
        # Añadir trace_id y request_id del contexto
        trace_id = LogContext.get_trace_id()
        if trace_id:
            entry["trace.id"] = trace_id
        
        request_id = LogContext.get_request_id()
        if request_id:
            entry["request.id"] = request_id
    
    def _sanitize_if_enabled(self, data: Any) -> Any:
        """Sanitiza los datos si está habilitado"""
        if self.sanitizer and self.config.enable_sanitization:
            return self.sanitizer.sanitize(data)
        return data
    
    def _log(
        self,
        level: LogLevel,
        event_name: str,
        message: str,
        outcome: Optional[EventOutcome] = None,
        duration_ms: Optional[int] = None,
        **kwargs
    ):
        """
        Método interno para generar un log.
        
        Args:
            level: Nivel de severidad
            event_name: Nombre del evento (ej: KB_QUERY)
            message: Mensaje descriptivo
            outcome: Resultado del evento (SUCCESS/FAILURE)
            duration_ms: Duración en milisegundos
            **kwargs: Campos adicionales
        """
        # Crear entrada base
        entry = self._get_base_log_entry()
        
        # Campos obligatorios
        entry["log.level"] = level.value
        entry["event.name"] = event_name.upper()
        entry["message"] = message
        
        # Outcome (por defecto SUCCESS para INFO/DEBUG, FAILURE para ERROR/FATAL)
        if outcome is None:
            if level in (LogLevel.ERROR, LogLevel.FATAL):
                outcome = EventOutcome.FAILURE
            else:
                outcome = EventOutcome.SUCCESS
        entry["event.outcome"] = outcome.value
        
        # Duración
        if duration_ms is not None:
            entry["event.duration_ms"] = int(duration_ms)
        
        # Campos opcionales
        self._add_optional_fields(entry)
        
        # Campos adicionales (sanitizados)
        if kwargs:
            sanitized_kwargs = self._sanitize_if_enabled(kwargs)
            entry.update(sanitized_kwargs)
        
        # Emitir log en JSON (1 línea)
        print(json.dumps(entry, ensure_ascii=False), file=sys.stdout, flush=True)
    
    def debug(self, event_name: str, message: str, **kwargs):
        """Log nivel DEBUG"""
        self._log(LogLevel.DEBUG, event_name, message, **kwargs)
    
    def info(self, event_name: str, message: str, **kwargs):
        """Log nivel INFO"""
        self._log(LogLevel.INFO, event_name, message, **kwargs)
    
    def warning(self, event_name: str, message: str, **kwargs):
        """Log nivel WARN"""
        self._log(LogLevel.WARN, event_name, message, **kwargs)
    
    def warn(self, event_name: str, message: str, **kwargs):
        """Alias de warning"""
        self.warning(event_name, message, **kwargs)
    
    def error(
        self,
        event_name: str,
        message: str,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        error_stack_trace: Optional[str] = None,
        **kwargs
    ):
        """
        Log nivel ERROR.
        
        Args:
            event_name: Nombre del evento
            message: Mensaje descriptivo
            error_type: Tipo de error (ej: TimeoutError)
            error_message: Mensaje del error
            error_code: Código de error
            error_stack_trace: Stack trace
            **kwargs: Campos adicionales
        """
        if error_type:
            kwargs["error.type"] = error_type
        if error_message:
            kwargs["error.message"] = error_message
        if error_code:
            kwargs["error.code"] = error_code
        if error_stack_trace:
            kwargs["error.stack_trace"] = error_stack_trace
        
        self._log(LogLevel.ERROR, event_name, message, EventOutcome.FAILURE, **kwargs)
    
    def fatal(
        self,
        event_name: str,
        message: str,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        **kwargs
    ):
        """Log nivel FATAL"""
        if error_type:
            kwargs["error.type"] = error_type
        if error_message:
            kwargs["error.message"] = error_message
        
        self._log(LogLevel.FATAL, event_name, message, EventOutcome.FAILURE, **kwargs)
    
    def set_trace_id(self, trace_id: Optional[str] = None) -> str:
        """
        Establece el trace_id para los logs subsiguientes.
        
        Args:
            trace_id: ID de traza (si es None, se genera uno nuevo)
            
        Returns:
            El trace_id establecido
        """
        return LogContext.set_trace_id(trace_id)
    
    def set_request_id(self, request_id: Optional[str] = None) -> str:
        """
        Establece el request_id para los logs subsiguientes.
        
        Args:
            request_id: ID de petición (si es None, se genera uno nuevo)
            
        Returns:
            El request_id establecido
        """
        return LogContext.set_request_id(request_id)
    
    def new_trace(self) -> tuple[str, str]:
        """
        Inicia un nuevo trace con IDs nuevos.
        
        Returns:
            Tupla (trace_id, request_id)
        """
        return LogContext.new_trace()
    
    @contextmanager
    def operation(self, event_name: str, **initial_metadata):
        """
        Context manager para operaciones que registra automáticamente inicio, fin y duración.
        
        Args:
            event_name: Nombre del evento
            **initial_metadata: Metadatos iniciales
            
        Yields:
            OperationContext: Contexto de la operación
            
        Example:
            with logger.operation("DATALAKE_QUERY") as op:
                result = query_datalake()
                op.add_metadata(rows=len(result))
        """
        start_time = time.time()
        metadata = dict(initial_metadata)
        
        class OperationContext:
            def add_metadata(self, **kwargs):
                metadata.update(kwargs)
        
        op_context = OperationContext()
        
        try:
            yield op_context
            duration_ms = int((time.time() - start_time) * 1000)
            self.info(
                event_name=event_name,
                message=f"Operation {event_name} completed successfully",
                duration_ms=duration_ms,
                outcome=EventOutcome.SUCCESS,
                **metadata
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.error(
                event_name=event_name,
                message=f"Operation {event_name} failed",
                duration_ms=duration_ms,
                outcome=EventOutcome.FAILURE,
                error_type=type(e).__name__,
                error_message=str(e),
                error_stack_trace=traceback.format_exc(),
                **metadata
            )
            raise
    
    def log_exception(self, event_name: str, exception: Exception, **kwargs):
        """
        Registra una excepción con toda su información.
        
        Args:
            event_name: Nombre del evento
            exception: Excepción capturada
            **kwargs: Campos adicionales
        """
        self.error(
            event_name=event_name,
            message=f"Exception occurred: {str(exception)}",
            error_type=type(exception).__name__,
            error_message=str(exception),
            error_stack_trace=traceback.format_exc(),
            **kwargs
        )