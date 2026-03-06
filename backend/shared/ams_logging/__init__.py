"""
AMS Logging Policy - Python Implementation
Implementación de la Política de Logs v1.0 para Transformación AMS Naturgy
"""

from .logger import AMSLogger
from .config import LogConfig
from .decorators import log_event, log_operation
from .context import LogContext
from .constants import LogLevel, EventOutcome, OFFICIAL_SERVICES
from .async_logger import (
    AsyncAMSLogger,
    OptimizedAMSLogger,
    HighPerformanceLogger,
    LevelFilteredLogger,
    setup_signal_handlers,
)

__version__ = "1.0.0"
__all__ = [
    "AMSLogger",
    "AsyncAMSLogger",
    "OptimizedAMSLogger",
    "HighPerformanceLogger",
    "LevelFilteredLogger",
    "LogConfig",
    "LogContext",
    "LogLevel",
    "EventOutcome",
    "OFFICIAL_SERVICES",
    "log_event",
    "log_operation",
    "setup_signal_handlers",
]