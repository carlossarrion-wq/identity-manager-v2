"""
Sanitización de datos sensibles según la Política de Logs (Sección 7)
"""

import re
from typing import Any, Dict
from .constants import SENSITIVE_FIELDS, PII_PATTERNS


class DataSanitizer:
    """Sanitiza datos sensibles y PII de los logs"""
    
    REDACTED = "***REDACTED***"
    
    # Patrones regex para detectar PII
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    DNI_PATTERN = re.compile(r'\b\d{8}[A-Z]\b')
    PHONE_PATTERN = re.compile(r'\b(\+34|0034)?[6-9]\d{8}\b')
    
    @classmethod
    def sanitize(cls, data: Any) -> Any:
        """
        Sanitiza recursivamente un objeto de datos.
        
        Args:
            data: Datos a sanitizar (dict, list, str, etc.)
            
        Returns:
            Datos sanitizados
        """
        if isinstance(data, dict):
            return cls._sanitize_dict(data)
        elif isinstance(data, list):
            return [cls.sanitize(item) for item in data]
        elif isinstance(data, str):
            return cls._sanitize_string(data)
        else:
            return data
    
    @classmethod
    def _sanitize_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitiza un diccionario"""
        sanitized = {}
        
        for key, value in data.items():
            key_lower = key.lower().replace("-", "_").replace(".", "_")
            
            # Si la clave es sensible, redactar completamente
            if any(sensitive in key_lower for sensitive in SENSITIVE_FIELDS):
                sanitized[key] = cls.REDACTED
            # Si la clave indica PII, enmascarar
            elif any(pii in key_lower for pii in PII_PATTERNS):
                sanitized[key] = cls._mask_pii(value)
            # Sanitizar recursivamente
            else:
                sanitized[key] = cls.sanitize(value)
        
        return sanitized
    
    @classmethod
    def _sanitize_string(cls, text: str) -> str:
        """Sanitiza una cadena de texto buscando patrones de PII"""
        # Enmascarar emails
        text = cls.EMAIL_PATTERN.sub(cls._mask_email, text)
        # Enmascarar DNIs
        text = cls.DNI_PATTERN.sub(lambda m: cls._mask_dni(m.group(0)), text)
        # Enmascarar teléfonos
        text = cls.PHONE_PATTERN.sub(lambda m: cls._mask_phone(m.group(0)), text)
        
        return text
    
    @classmethod
    def _mask_pii(cls, value: Any) -> Any:
        """Enmascara un valor PII"""
        if isinstance(value, str):
            if cls.EMAIL_PATTERN.match(value):
                return cls._mask_email(value)
            elif cls.DNI_PATTERN.match(value):
                return cls._mask_dni(value)
            elif cls.PHONE_PATTERN.match(value):
                return cls._mask_phone(value)
            else:
                # Enmascarar genéricamente
                if len(value) > 4:
                    return value[0] + "*" * (len(value) - 2) + value[-1]
                else:
                    return "***"
        return value
    
    @staticmethod
    def _mask_email(email: str) -> str:
        """Enmascara un email: john.doe@example.com -> j***@example.com"""
        if isinstance(email, re.Match):
            email = email.group(0)
        
        if "@" in email:
            local, domain = email.split("@", 1)
            if len(local) > 1:
                masked_local = local[0] + "***"
            else:
                masked_local = "***"
            return f"{masked_local}@{domain}"
        return email
    
    @staticmethod
    def _mask_dni(dni: str) -> str:
        """Enmascara un DNI: 12345678A -> ****5678A"""
        if len(dni) >= 5:
            return "****" + dni[-5:]
        return "***"
    
    @staticmethod
    def _mask_phone(phone: str) -> str:
        """Enmascara un teléfono: 612345678 -> ***345678"""
        # Eliminar prefijos
        phone = phone.replace("+34", "").replace("0034", "")
        if len(phone) >= 6:
            return "***" + phone[-6:]
        return "***"