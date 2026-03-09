"""
Middlewares para integración con frameworks web
"""

from typing import Callable, Optional
from .context import LogContext


def flask_middleware(logger):
    """
    Middleware para Flask que automáticamente:
    - Extrae trace_id de headers (X-Trace-Id, X-Request-Id, etc.)
    - Genera request_id
    - Registra cada petición HTTP
    
    Args:
        logger: Instancia de AMSLogger
        
    Example:
        from flask import Flask
        from ams_logging import AMSLogger, flask_middleware
        
        app = Flask(__name__)
        logger = AMSLogger(config)
        
        app.before_request(flask_middleware(logger))
    """
    def middleware():
        from flask import request, g
        import time
        
        # Extraer o generar trace_id
        trace_id = (
            request.headers.get("X-Trace-Id") or
            request.headers.get("X-Request-Id") or
            request.headers.get("X-Correlation-Id")
        )
        logger.set_trace_id(trace_id)
        
        # Generar request_id
        request_id = request.headers.get("X-Request-Id")
        logger.set_request_id(request_id)
        
        # Guardar tiempo de inicio
        g.start_time = time.time()
        g.trace_id = LogContext.get_trace_id()
        g.request_id = LogContext.get_request_id()
        
        # Log de inicio de petición
        logger.info(
            event_name="HTTP_REQUEST_START",
            message=f"{request.method} {request.path}",
            http_method=request.method,
            url_path=request.path,
            url_query=request.query_string.decode() if request.query_string else None,
            client_ip=request.remote_addr,
            user_agent=request.headers.get("User-Agent")
        )
    
    return middleware


def flask_after_request(logger):
    """
    Middleware para Flask que registra la respuesta HTTP.
    
    Example:
        app.after_request(flask_after_request(logger))
    """
    def middleware(response):
        from flask import g, request
        import time
        
        if hasattr(g, "start_time"):
            duration_ms = int((time.time() - g.start_time) * 1000)
            
            logger.info(
                event_name="HTTP_REQUEST_COMPLETE",
                message=f"{request.method} {request.path} - {response.status_code}",
                http_method=request.method,
                url_path=request.path,
                http_status_code=response.status_code,
                duration_ms=duration_ms,
                outcome="SUCCESS" if response.status_code < 400 else "FAILURE"
            )
        
        # Añadir headers de trazabilidad a la respuesta
        if hasattr(g, "trace_id"):
            response.headers["X-Trace-Id"] = g.trace_id
        if hasattr(g, "request_id"):
            response.headers["X-Request-Id"] = g.request_id
        
        return response
    
    return middleware


def fastapi_middleware(logger):
    """
    Middleware para FastAPI que automáticamente:
    - Extrae trace_id de headers
    - Genera request_id
    - Registra cada petición HTTP
    
    Args:
        logger: Instancia de AMSLogger
        
    Example:
        from fastapi import FastAPI
        from ams_logging import AMSLogger, fastapi_middleware
        
        app = FastAPI()
        logger = AMSLogger(config)
        
        app.middleware("http")(fastapi_middleware(logger))
    """
    async def middleware(request, call_next):
        import time
        
        # Extraer o generar trace_id
        trace_id = (
            request.headers.get("x-trace-id") or
            request.headers.get("x-request-id") or
            request.headers.get("x-correlation-id")
        )
        logger.set_trace_id(trace_id)
        
        # Generar request_id
        request_id = request.headers.get("x-request-id")
        logger.set_request_id(request_id)
        
        trace_id = LogContext.get_trace_id()
        request_id = LogContext.get_request_id()
        
        # Log de inicio
        start_time = time.time()
        logger.info(
            event_name="HTTP_REQUEST_START",
            message=f"{request.method} {request.url.path}",
            http_method=request.method,
            url_path=request.url.path,
            url_query=str(request.query_params) if request.query_params else None,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        # Procesar petición
        try:
            response = await call_next(request)
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log de finalización
            logger.info(
                event_name="HTTP_REQUEST_COMPLETE",
                message=f"{request.method} {request.url.path} - {response.status_code}",
                http_method=request.method,
                url_path=request.url.path,
                http_status_code=response.status_code,
                duration_ms=duration_ms,
                outcome="SUCCESS" if response.status_code < 400 else "FAILURE"
            )
            
            # Añadir headers de trazabilidad
            response.headers["X-Trace-Id"] = trace_id
            response.headers["X-Request-Id"] = request_id
            
            return response
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            
            logger.error(
                event_name="HTTP_REQUEST_ERROR",
                message=f"{request.method} {request.url.path} - Error",
                http_method=request.method,
                url_path=request.url.path,
                duration_ms=duration_ms,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise
    
    return middleware