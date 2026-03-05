"""
Validators
==========
Validadores para requests de la API
"""

import re
from typing import Dict, Any, Optional

# Regex para validar email
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


def validate_request(operation: str, body: Dict[str, Any]) -> Optional[str]:
    """
    Validar request según la operación
    
    Args:
        operation: Nombre de la operación
        body: Body del request
        
    Returns:
        Mensaje de error si hay validación fallida, None si es válido
    """
    validators = {
        'create_user': validate_create_user,
        'delete_user': validate_delete_user,
        'create_token': validate_create_token,
        'revoke_token': validate_revoke_token,
        'delete_token': validate_delete_token,
    }
    
    validator = validators.get(operation)
    if validator:
        return validator(body)
    
    return None


def validate_create_user(body: Dict[str, Any]) -> Optional[str]:
    """Validar request de creación de usuario"""
    data = body.get('data', {})
    
    # Email requerido y válido
    email = data.get('email')
    if not email:
        return 'El campo "email" es requerido'
    
    if not EMAIL_REGEX.match(email):
        return f'Email inválido: {email}'
    
    # Person requerido
    person = data.get('person')
    if not person or not person.strip():
        return 'El campo "person" (nombre y apellidos) es requerido'
    
    # Group requerido
    group = data.get('group')
    if not group or not group.strip():
        return 'El campo "group" es requerido'
    
    # Validar password temporal si se proporciona
    temp_password = data.get('temporary_password')
    if temp_password:
        password_error = validate_password(temp_password)
        if password_error:
            return password_error
    
    return None


def validate_delete_user(body: Dict[str, Any]) -> Optional[str]:
    """Validar request de eliminación de usuario"""
    user_id = body.get('user_id')
    
    if not user_id or not user_id.strip():
        return 'El campo "user_id" es requerido'
    
    return None


def validate_create_token(body: Dict[str, Any]) -> Optional[str]:
    """Validar request de creación de token"""
    data = body.get('data', {})
    
    # User ID requerido
    user_id = data.get('user_id')
    if not user_id or not user_id.strip():
        return 'El campo "user_id" es requerido'
    
    # Profile ID requerido
    profile_id = data.get('application_profile_id')
    if not profile_id or not profile_id.strip():
        return 'El campo "application_profile_id" es requerido'
    
    # Validar período de validez si se proporciona
    validity_period = data.get('validity_period')
    if validity_period:
        valid_periods = ['1_minute', '1_day', '7_days', '30_days', '60_days', '90_days']
        if validity_period not in valid_periods:
            return f'Período de validez inválido. Opciones válidas: {", ".join(valid_periods)}'
    
    return None


def validate_revoke_token(body: Dict[str, Any]) -> Optional[str]:
    """Validar request de revocación de token"""
    token_id = body.get('token_id')
    
    if not token_id or not token_id.strip():
        return 'El campo "token_id" es requerido'
    
    return None


def validate_delete_token(body: Dict[str, Any]) -> Optional[str]:
    """Validar request de eliminación de token"""
    token_id = body.get('token_id')
    
    if not token_id or not token_id.strip():
        return 'El campo "token_id" es requerido'
    
    return None


def validate_password(password: str) -> Optional[str]:
    """
    Validar que la contraseña cumple con la política de Cognito
    
    Args:
        password: Contraseña a validar
        
    Returns:
        Mensaje de error si no cumple, None si es válida
    """
    if len(password) < 8:
        return 'La contraseña debe tener al menos 8 caracteres'
    
    if not re.search(r'[A-Z]', password):
        return 'La contraseña debe contener al menos una letra mayúscula'
    
    if not re.search(r'[a-z]', password):
        return 'La contraseña debe contener al menos una letra minúscula'
    
    if not re.search(r'[0-9]', password):
        return 'La contraseña debe contener al menos un número'
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-]', password):
        return 'La contraseña debe contener al menos un carácter especial'
    
    return None


def validate_email(email: str) -> bool:
    """
    Validar formato de email
    
    Args:
        email: Email a validar
        
    Returns:
        True si es válido
    """
    if not email or not isinstance(email, str):
        return False
    return bool(EMAIL_REGEX.match(email))


def validate_uuid(uuid_str: str) -> bool:
    """
    Validar formato de UUID
    
    Args:
        uuid_str: String UUID a validar
        
    Returns:
        True si es válido
    """
    if not uuid_str or not isinstance(uuid_str, str):
        return False
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    return bool(uuid_pattern.match(uuid_str))
