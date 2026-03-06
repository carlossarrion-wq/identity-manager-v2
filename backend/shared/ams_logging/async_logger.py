"""
Logger asíncrono de alto rendimiento para aplicaciones con alto volumen de logs.

Este módulo proporciona implementaciones optimizadas del logger que minimizan
el impacto en el rendimiento de la aplicación principal.
"""

import atexit
import json
import queue
import signal
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .config import LogConfig
from .constants import LogLevel, EventOutcome
from .logger import AMSLogger


class AsyncAMSLogger(AMSLogger):
    """
    Logger asíncrono que usa una cola para no bloquear el thread principal.
    
    Características:
    - Escritura de logs en thread separado
    - Cola con tamaño configurable
    - Fallback a escritura síncrona si la cola está llena
    - Shutdown graceful para no perder logs
    
    Ideal para aplicaciones con >10,000 logs/segundo.
    
    Example:
        >>> config = LogConfig(service_name="kb-agent", service_version="1.0.0", environment="pre")
        >>> logger = AsyncAMSLogger(config, queue_size=10000)
        >>> logger.info("API_CALL", "Request processed")
        >>> # Al finalizar la aplicación
        >>> logger.shutdown()
    """
    
    def __init__(self, config: LogConfig, queue_size: int = 10000, auto_shutdown: bool = True):
        """
        Inicializa el logger asíncrono.
        
        Args:
            config: Configuración del logger
            queue_size: Tamaño máximo de la cola de logs
            auto_shutdown: Si True, registra shutdown automático con atexit
        """
        super().__init__(config)
        self._log_queue = queue.Queue(maxsize=queue_size)
        self._shutdown = False
        self._worker_thread = threading.Thread(
            target=self._log_worker,
            daemon=True,
            name="AMSLoggerWorker"
        )
        self._worker_thread.start()
        
        # Estadísticas
        self._stats = {
            "logs_queued": 0,
            "logs_dropped": 0,
            "logs_written": 0,
            "errors": 0
        }
        self._stats_lock = threading.Lock()
        
        # Registrar shutdown automático
        if auto_shutdown:
            atexit.register(lambda: self.shutdown(timeout=5.0))
    
    def _log_worker(self):
        """Worker thread que procesa la cola de logs"""
        while not self._shutdown:
            try:
                entry = self._log_queue.get(timeout=0.1)
                if entry is None:  # Señal de shutdown
                    break
                
                # Escribir log
                print(json.dumps(entry, ensure_ascii=False), file=sys.stdout, flush=True)
                
                with self._stats_lock:
                    self._stats["logs_written"] += 1
                
                self._log_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                # Fallback: log directo en caso de error
                print(f"[AMSLogger] Worker error: {e}", file=sys.stderr, flush=True)
                with self._stats_lock:
                    self._stats["errors"] += 1
    
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
        Versión asíncrona que encola el log.
        
        Si la cola está llena, hace fallback a escritura síncrona para no perder el log.
        """
        # Crear entrada de log
        entry = self._get_base_log_entry()
        entry["log.level"] = level.value
        entry["event.name"] = event_name.upper()
        entry["message"] = message
        
        # Outcome
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
        
        # Intentar encolar
        try:
            self._log_queue.put_nowait(entry)
            with self._stats_lock:
                self._stats["logs_queued"] += 1
        except queue.Full:
            # Fallback: log directo si la cola está llena
            print(json.dumps(entry, ensure_ascii=False), file=sys.stdout, flush=True)
            with self._stats_lock:
                self._stats["logs_dropped"] += 1
    
    def shutdown(self, timeout: float = 5.0):
        """
        Cierra el logger esperando a que se procesen los logs pendientes.
        
        Args:
            timeout: Tiempo máximo de espera en segundos
        """
        if self._shutdown:
            return  # Ya está cerrado
        
        self._shutdown = True
        
        # Esperar a que se vacíe la cola
        try:
            self._log_queue.join()
        except:
            pass
        
        # Enviar señal de shutdown al worker
        try:
            self._log_queue.put(None, timeout=1.0)
        except queue.Full:
            pass
        
        # Esperar a que termine el worker
        self._worker_thread.join(timeout=timeout)
    
    def get_stats(self) -> Dict[str, int]:
        """
        Obtiene estadísticas del logger.
        
        Returns:
            Diccionario con estadísticas de uso
        """
        with self._stats_lock:
            return self._stats.copy()
    
    def get_queue_size(self) -> int:
        """Retorna el número de logs pendientes en la cola"""
        return self._log_queue.qsize()


class OptimizedAMSLogger(AMSLogger):
    """
    Logger con optimizaciones de caché para campos estáticos.
    
    Reduce el overhead de creación de logs al cachear campos que no cambian
    durante la ejecución de la aplicación.
    
    Ideal para aplicaciones con muchos logs pero sin necesidad de asincronía.
    
    Example:
        >>> config = LogConfig(service_name="kb-agent", service_version="1.0.0", environment="pre")
        >>> logger = OptimizedAMSLogger(config)
        >>> logger.info("API_CALL", "Request processed")
    """
    
    def __init__(self, config: LogConfig):
        super().__init__(config)
        # Pre-calcular campos estáticos
        self._static_fields = {
            "service.name": self.config.service_name,
            "service.version": self.config.service_version,
            "labels.environment": self.config.environment,
        }
        if self.config.instance_id:
            self._static_fields["service.instance.id"] = self.config.instance_id
    
    def _get_base_log_entry(self) -> Dict[str, Any]:
        """Versión optimizada que reutiliza campos estáticos"""
        # Copia shallow (muy rápida)
        entry = self._static_fields.copy()
        # Solo calcular timestamp
        entry["@timestamp"] = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
        return entry


class HighPerformanceLogger(OptimizedAMSLogger, AsyncAMSLogger):
    """
    Logger de máximo rendimiento que combina caché de campos y procesamiento asíncrono.
    
    Combina las optimizaciones de OptimizedAMSLogger y AsyncAMSLogger para
    obtener el máximo rendimiento posible.
    
    Ideal para microservicios críticos con >50,000 logs/segundo.
    
    Example:
        >>> config = LogConfig(service_name="kb-agent", service_version="1.0.0", environment="pre")
        >>> logger = HighPerformanceLogger(config, queue_size=50000)
        >>> logger.info("API_CALL", "Request processed")
        >>> logger.shutdown()
    """
    
    def __init__(self, config: LogConfig, queue_size: int = 50000, auto_shutdown: bool = True):
        # Inicializar en orden correcto
        AMSLogger.__init__(self, config)
        OptimizedAMSLogger.__init__(self, config)
        AsyncAMSLogger.__init__(self, config, queue_size, auto_shutdown)


class LevelFilteredLogger(AMSLogger):
    """
    Logger que filtra logs por nivel mínimo antes de procesarlos.
    
    Útil para reducir el volumen de logs en producción sin modificar el código.
    
    Example:
        >>> config = LogConfig(service_name="kb-agent", service_version="1.0.0", environment="pre")
        >>> # Solo logs INFO y superiores
        >>> logger = LevelFilteredLogger(config, min_level=LogLevel.INFO)
        >>> logger.debug("DEBUG_EVENT", "This will be ignored")
        >>> logger.info("INFO_EVENT", "This will be logged")
    """
    
    def __init__(self, config: LogConfig, min_level: LogLevel = LogLevel.INFO):
        super().__init__(config)
        self.min_level = min_level
        self._level_priority = {
            LogLevel.DEBUG: 0,
            LogLevel.INFO: 1,
            LogLevel.WARN: 2,
            LogLevel.ERROR: 3,
            LogLevel.FATAL: 4,
        }
    
    def _log(
        self,
        level: LogLevel,
        event_name: str,
        message: str,
        outcome: Optional[EventOutcome] = None,
        duration_ms: Optional[int] = None,
        **kwargs
    ):
        """Solo procesa logs del nivel mínimo o superior"""
        if self._level_priority[level] < self._level_priority[self.min_level]:
            return  # Skip log
        super()._log(level, event_name, message, outcome, duration_ms, **kwargs)


def setup_signal_handlers(logger: AsyncAMSLogger):
    """
    Configura handlers de señales para shutdown graceful del logger asíncrono.
    
    Args:
        logger: Logger asíncrono a cerrar en caso de señal
        
    Example:
        >>> logger = AsyncAMSLogger(config)
        >>> setup_signal_handlers(logger)
    """
    def signal_handler(signum, frame):
        print(f"[AMSLogger] Received signal {signum}, shutting down...", file=sys.stderr)
        logger.shutdown(timeout=2.0)
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)