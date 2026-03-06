"""
Configuración del logger AMS
"""

from dataclasses import dataclass, field
from typing import Optional
from .constants import OFFICIAL_SERVICES, VALID_ENVIRONMENTS, LogLevel


@dataclass
class LogConfig:
    """
    Configuración para el logger AMS.
    
    Attributes:
        service_name: Nombre del servicio (debe estar en el inventario oficial)
        service_version: Versión del servicio desplegado
        environment: Entorno (dev/pre/pro)
        instance_id: Identificador de la instancia (opcional)
        default_level: Nivel de log por defecto
        enable_sanitization: Activar sanitización de datos sensibles
        validate_service_name: Validar que service_name esté en el inventario
    """
    
    service_name: str
    service_version: str
    environment: str
    instance_id: Optional[str] = None
    default_level: LogLevel = LogLevel.INFO
    enable_sanitization: bool = True
    validate_service_name: bool = True
    
    def __post_init__(self):
        """Validación de la configuración"""
        
        # Validar service_name contra inventario oficial
        if self.validate_service_name and self.service_name not in OFFICIAL_SERVICES:
            raise ValueError(
                f"service_name '{self.service_name}' no está en el inventario oficial. "
                f"Servicios válidos: {', '.join(OFFICIAL_SERVICES.keys())}"
            )
        
        # Validar environment
        if self.environment not in VALID_ENVIRONMENTS:
            raise ValueError(
                f"environment '{self.environment}' no es válido. "
                f"Valores válidos: {', '.join(VALID_ENVIRONMENTS)}"
            )
        
        # Validar que service_version no esté vacío
        if not self.service_version or not self.service_version.strip():
            raise ValueError("service_version no puede estar vacío")
    
    def to_dict(self) -> dict:
        """Convierte la configuración a diccionario"""
        return {
            "service.name": self.service_name,
            "service.version": self.service_version,
            "labels.environment": self.environment,
            "service.instance.id": self.instance_id,
        }