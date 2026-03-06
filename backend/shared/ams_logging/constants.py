"""
Constantes definidas en la Política de Logs v1.0
"""

from enum import Enum


class LogLevel(str, Enum):
    """Niveles de severidad de logs según la política"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"


class EventOutcome(str, Enum):
    """Resultados posibles de un evento"""
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


# Inventario oficial de servicios (Sección 9 de la política)
OFFICIAL_SERVICES = {
    "kb-agent": "Agente de Conocimiento",
    "bedrock-proxy": "Proxy de Acceso a Amazon Bedrock",
    "capacity-mgmt": "Gestor de Capacidad",
    "identity-mgmt": "Gestor de Identidades",
    "bedrock-dashboard": "Control de Uso Bedrock",
    "kb-agent-dashboard": "Control de Uso Knowledge Base",
}


# Campos sensibles que deben ser sanitizados (Sección 7 de la política)
SENSITIVE_FIELDS = {
    "password",
    "passwd",
    "pwd",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "credentials",
    "credential",
}


# Patrones de PII que deben ser enmascarados
PII_PATTERNS = {
    "email",
    "mail",
    "dni",
    "nie",
    "nif",
    "phone",
    "telephone",
    "mobile",
    "address",
    "postal_code",
    "zip_code",
    "iban",
    "credit_card",
    "card_number",
}


# Campos obligatorios según la política (Sección 3.1)
MANDATORY_FIELDS = {
    "@timestamp",
    "log.level",
    "service.name",
    "service.version",
    "labels.environment",
    "event.name",
    "event.outcome",
    "message",
    "trace.id",
    "request.id",
    "event.duration_ms",
}


# Entornos válidos
VALID_ENVIRONMENTS = {"dev", "pre", "pro"}