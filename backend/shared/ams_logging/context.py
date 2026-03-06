"""
Contexto de logging para mantener trace_id y request_id
"""

import uuid
from contextvars import ContextVar
from typing import Optional


# Variables de contexto para trazabilidad
_trace_id: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class LogContext:
    """Gestión del contexto de logging (trace_id, request_id)"""
    
    @staticmethod
    def generate_uuid() -> str:
        """Genera un UUID corto para IDs"""
        return str(uuid.uuid4())[:8]
    
    @classmethod
    def set_trace_id(cls, trace_id: Optional[str] = None) -> str:
        """
        Establece el trace_id. Si no se proporciona, genera uno nuevo.
        
        Args:
            trace_id: ID de traza (opcional)
            
        Returns:
            El trace_id establecido
        """
        if trace_id is None:
            trace_id = cls.generate_uuid()
        _trace_id.set(trace_id)
        return trace_id
    
    @classmethod
    def get_trace_id(cls) -> Optional[str]:
        """Obtiene el trace_id actual"""
        return _trace_id.get()
    
    @classmethod
    def set_request_id(cls, request_id: Optional[str] = None) -> str:
        """
        Establece el request_id. Si no se proporciona, genera uno nuevo.
        
        Args:
            request_id: ID de petición (opcional)
            
        Returns:
            El request_id establecido
        """
        if request_id is None:
            request_id = f"req-{cls.generate_uuid()}"
        _request_id.set(request_id)
        return request_id
    
    @classmethod
    def get_request_id(cls) -> Optional[str]:
        """Obtiene el request_id actual"""
        return _request_id.get()
    
    @classmethod
    def clear(cls):
        """Limpia el contexto"""
        _trace_id.set(None)
        _request_id.set(None)
    
    @classmethod
    def new_trace(cls) -> tuple[str, str]:
        """
        Inicia un nuevo trace con trace_id y request_id nuevos.
        
        Returns:
            Tupla (trace_id, request_id)
        """
        trace_id = cls.set_trace_id()
        request_id = cls.set_request_id()
        return trace_id, request_id