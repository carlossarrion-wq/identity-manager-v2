"""
Unit Tests for Permissions Validators
======================================
Tests unitarios para validadores de operaciones de permisos
"""

import pytest
from utils.validators import (
    validate_assign_app_permission,
    validate_assign_module_permission,
    validate_revoke_app_permission,
    validate_revoke_module_permission,
    validate_get_user_permissions
)


class TestValidateAssignAppPermission:
    """Tests para validación de asignación de permiso de aplicación"""
    
    def test_valid_request(self):
        """Test: Request válido"""
        body = {
            'data': {
                'user_id': 'user-123',
                'user_email': 'test@example.com',
                'application_id': '12345678-1234-1234-1234-123456789012',
                'permission_type_id': '87654321-4321-4321-4321-210987654321',
                'duration_days': 30
            }
        }
        
        result = validate_assign_app_permission(body)
        assert result is None
    
    def test_valid_request_without_duration(self):
        """Test: Request válido sin duración (indefinido)"""
        body = {
            'data': {
                'user_id': 'user-123',
                'user_email': 'test@example.com',
                'application_id': '12345678-1234-1234-1234-123456789012',
                'permission_type_id': '87654321-4321-4321-4321-210987654321'
            }
        }
        
        result = validate_assign_app_permission(body)
        assert result is None
    
    def test_missing_user_id(self):
        """Test: Falta user_id"""
        body = {
            'data': {
                'user_email': 'test@example.com',
                'application_id': '12345678-1234-1234-1234-123456789012',
                'permission_type_id': '87654321-4321-4321-4321-210987654321'
            }
        }
        
        result = validate_assign_app_permission(body)
        assert result is not None
        assert 'user_id' in result
    
    def test_missing_user_email(self):
        """Test: Falta user_email"""
        body = {
            'data': {
                'user_id': 'user-123',
                'application_id': '12345678-1234-1234-1234-123456789012',
                'permission_type_id': '87654321-4321-4321-4321-210987654321'
            }
        }
        
        result = validate_assign_app_permission(body)
        assert result is not None
        assert 'user_email' in result
    
    def test_invalid_email(self):
        """Test: Email inválido"""
        body = {
            'data': {
                'user_id': 'user-123',
                'user_email': 'invalid-email',
                'application_id': '12345678-1234-1234-1234-123456789012',
                'permission_type_id': '87654321-4321-4321-4321-210987654321'
            }
        }
        
        result = validate_assign_app_permission(body)
        assert result is not None
        assert 'Email inválido' in result
    
    def test_missing_application_id(self):
        """Test: Falta application_id"""
        body = {
            'data': {
                'user_id': 'user-123',
                'user_email': 'test@example.com',
                'permission_type_id': '87654321-4321-4321-4321-210987654321'
            }
        }
        
        result = validate_assign_app_permission(body)
        assert result is not None
        assert 'application_id' in result
    
    def test_invalid_application_id_uuid(self):
        """Test: UUID de aplicación inválido"""
        body = {
            'data': {
                'user_id': 'user-123',
                'user_email': 'test@example.com',
                'application_id': 'not-a-uuid',
                'permission_type_id': '87654321-4321-4321-4321-210987654321'
            }
        }
        
        result = validate_assign_app_permission(body)
        assert result is not None
        assert 'ID de aplicación inválido' in result
    
    def test_missing_permission_type_id(self):
        """Test: Falta permission_type_id"""
        body = {
            'data': {
                'user_id': 'user-123',
                'user_email': 'test@example.com',
                'application_id': '12345678-1234-1234-1234-123456789012'
            }
        }
        
        result = validate_assign_app_permission(body)
        assert result is not None
        assert 'permission_type_id' in result
    
    def test_invalid_permission_type_id_uuid(self):
        """Test: UUID de tipo de permiso inválido"""
        body = {
            'data': {
                'user_id': 'user-123',
                'user_email': 'test@example.com',
                'application_id': '12345678-1234-1234-1234-123456789012',
                'permission_type_id': 'invalid-uuid'
            }
        }
        
        result = validate_assign_app_permission(body)
        assert result is not None
        assert 'ID de tipo de permiso inválido' in result
    
    def test_invalid_duration_days_negative(self):
        """Test: duration_days negativo"""
        body = {
            'data': {
                'user_id': 'user-123',
                'user_email': 'test@example.com',
                'application_id': '12345678-1234-1234-1234-123456789012',
                'permission_type_id': '87654321-4321-4321-4321-210987654321',
                'duration_days': -5
            }
        }
        
        result = validate_assign_app_permission(body)
        assert result is not None
        assert 'duration_days' in result
    
    def test_invalid_duration_days_not_integer(self):
        """Test: duration_days no es entero"""
        body = {
            'data': {
                'user_id': 'user-123',
                'user_email': 'test@example.com',
                'application_id': '12345678-1234-1234-1234-123456789012',
                'permission_type_id': '87654321-4321-4321-4321-210987654321',
                'duration_days': '30'
            }
        }
        
        result = validate_assign_app_permission(body)
        assert result is not None
        assert 'duration_days' in result


class TestValidateAssignModulePermission:
    """Tests para validación de asignación de permiso de módulo"""
    
    def test_valid_request(self):
        """Test: Request válido"""
        body = {
            'data': {
                'user_id': 'user-123',
                'user_email': 'test@example.com',
                'module_id': '12345678-1234-1234-1234-123456789012',
                'permission_type_id': '87654321-4321-4321-4321-210987654321',
                'duration_days': 7
            }
        }
        
        result = validate_assign_module_permission(body)
        assert result is None
    
    def test_missing_module_id(self):
        """Test: Falta module_id"""
        body = {
            'data': {
                'user_id': 'user-123',
                'user_email': 'test@example.com',
                'permission_type_id': '87654321-4321-4321-4321-210987654321'
            }
        }
        
        result = validate_assign_module_permission(body)
        assert result is not None
        assert 'module_id' in result
    
    def test_invalid_module_id_uuid(self):
        """Test: UUID de módulo inválido"""
        body = {
            'data': {
                'user_id': 'user-123',
                'user_email': 'test@example.com',
                'module_id': 'not-a-uuid',
                'permission_type_id': '87654321-4321-4321-4321-210987654321'
            }
        }
        
        result = validate_assign_module_permission(body)
        assert result is not None
        assert 'ID de módulo inválido' in result


class TestValidateRevokeAppPermission:
    """Tests para validación de revocación de permiso de aplicación"""
    
    def test_valid_request(self):
        """Test: Request válido"""
        body = {
            'user_id': 'user-123',
            'application_id': '12345678-1234-1234-1234-123456789012'
        }
        
        result = validate_revoke_app_permission(body)
        assert result is None
    
    def test_missing_user_id(self):
        """Test: Falta user_id"""
        body = {
            'application_id': '12345678-1234-1234-1234-123456789012'
        }
        
        result = validate_revoke_app_permission(body)
        assert result is not None
        assert 'user_id' in result
    
    def test_missing_application_id(self):
        """Test: Falta application_id"""
        body = {
            'user_id': 'user-123'
        }
        
        result = validate_revoke_app_permission(body)
        assert result is not None
        assert 'application_id' in result
    
    def test_invalid_application_id_uuid(self):
        """Test: UUID de aplicación inválido"""
        body = {
            'user_id': 'user-123',
            'application_id': 'invalid-uuid'
        }
        
        result = validate_revoke_app_permission(body)
        assert result is not None
        assert 'ID de aplicación inválido' in result


class TestValidateRevokeModulePermission:
    """Tests para validación de revocación de permiso de módulo"""
    
    def test_valid_request(self):
        """Test: Request válido"""
        body = {
            'user_id': 'user-123',
            'module_id': '12345678-1234-1234-1234-123456789012'
        }
        
        result = validate_revoke_module_permission(body)
        assert result is None
    
    def test_missing_user_id(self):
        """Test: Falta user_id"""
        body = {
            'module_id': '12345678-1234-1234-1234-123456789012'
        }
        
        result = validate_revoke_module_permission(body)
        assert result is not None
        assert 'user_id' in result
    
    def test_missing_module_id(self):
        """Test: Falta module_id"""
        body = {
            'user_id': 'user-123'
        }
        
        result = validate_revoke_module_permission(body)
        assert result is not None
        assert 'module_id' in result
    
    def test_invalid_module_id_uuid(self):
        """Test: UUID de módulo inválido"""
        body = {
            'user_id': 'user-123',
            'module_id': 'not-a-uuid'
        }
        
        result = validate_revoke_module_permission(body)
        assert result is not None
        assert 'ID de módulo inválido' in result


class TestValidateGetUserPermissions:
    """Tests para validación de obtención de permisos de usuario"""
    
    def test_valid_request(self):
        """Test: Request válido"""
        body = {
            'user_id': 'user-123'
        }
        
        result = validate_get_user_permissions(body)
        assert result is None
    
    def test_missing_user_id(self):
        """Test: Falta user_id"""
        body = {}
        
        result = validate_get_user_permissions(body)
        assert result is not None
        assert 'user_id' in result
    
    def test_empty_user_id(self):
        """Test: user_id vacío"""
        body = {
            'user_id': ''
        }
        
        result = validate_get_user_permissions(body)
        assert result is not None
        assert 'user_id' in result
