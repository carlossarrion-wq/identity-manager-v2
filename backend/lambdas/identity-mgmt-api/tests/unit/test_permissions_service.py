"""
Unit Tests for Permissions Service
===================================
Tests unitarios para el servicio de gestión de permisos
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from services.permissions_service import PermissionsService


@pytest.fixture
def mock_db_service():
    """Mock del DatabaseService"""
    with patch('services.permissions_service.DatabaseService') as mock:
        db_instance = Mock()
        mock.return_value = db_instance
        yield db_instance


@pytest.fixture
def permissions_service(mock_db_service):
    """Instancia del servicio de permisos con DB mockeada"""
    return PermissionsService()


@pytest.fixture
def sample_app_permission():
    """Permiso de aplicación de ejemplo"""
    return {
        'permission_id': 'perm-uuid-123',
        'user_id': 'user-123',
        'email': 'test@example.com',
        'application_id': 'app-uuid-456',
        'application_name': 'Cline',
        'permission_type': 'Admin',
        'permission_level': 100,
        'granted_at': datetime.now(),
        'expires_at': None,
        'is_active': True
    }


@pytest.fixture
def sample_module_permission():
    """Permiso de módulo de ejemplo"""
    return {
        'permission_id': 'perm-uuid-789',
        'user_id': 'user-123',
        'email': 'test@example.com',
        'module_id': 'module-uuid-111',
        'module_name': 'RAG',
        'application_id': 'app-uuid-456',
        'application_name': 'Cline',
        'permission_type': 'Write',
        'permission_level': 50,
        'granted_at': datetime.now(),
        'expires_at': datetime.now() + timedelta(days=30),
        'is_active': True
    }


class TestAssignAppPermission:
    """Tests para asignación de permisos de aplicación"""
    
    def test_assign_new_app_permission_success(self, permissions_service, mock_db_service, sample_app_permission):
        """Test: Asignar nuevo permiso de aplicación exitosamente"""
        # Arrange
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_service.get_connection.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # No existe permiso previo
        mock_cursor.fetchone.side_effect = [
            None,  # check_query
            {'id': 'perm-uuid-123', 'granted_at': datetime.now()},  # insert
            sample_app_permission  # _get_app_permission_info
        ]
        
        # Act
        result = permissions_service.assign_app_permission(
            user_id='user-123',
            user_email='test@example.com',
            app_id='app-uuid-456',
            permission_type_id='ptype-uuid-789',
            duration_days=None
        )
        
        # Assert
        assert result['success'] is True
        assert result['action'] == 'created'
        assert 'permission' in result
        assert result['message'] == 'Permiso de aplicación created correctamente'
    
    def test_assign_app_permission_with_duration(self, permissions_service, mock_db_service, sample_app_permission):
        """Test: Asignar permiso con duración específica"""
        # Arrange
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_service.get_connection.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchone.side_effect = [
            None,
            {'id': 'perm-uuid-123', 'granted_at': datetime.now()},
            sample_app_permission
        ]
        
        # Act
        result = permissions_service.assign_app_permission(
            user_id='user-123',
            user_email='test@example.com',
            app_id='app-uuid-456',
            permission_type_id='ptype-uuid-789',
            duration_days=30
        )
        
        # Assert
        assert result['success'] is True
        # Verificar que se llamó con expires_at
        insert_call = mock_cursor.execute.call_args_list[1]
        assert insert_call[0][1][4] is not None  # expires_at no es None
    
    def test_update_existing_app_permission(self, permissions_service, mock_db_service, sample_app_permission):
        """Test: Actualizar permiso existente"""
        # Arrange
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_service.get_connection.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Existe permiso previo
        mock_cursor.fetchone.side_effect = [
            {'id': 'perm-uuid-123', 'is_active': False},  # check_query
            {'id': 'perm-uuid-123', 'granted_at': datetime.now()},  # update
            sample_app_permission  # _get_app_permission_info
        ]
        
        # Act
        result = permissions_service.assign_app_permission(
            user_id='user-123',
            user_email='test@example.com',
            app_id='app-uuid-456',
            permission_type_id='ptype-uuid-789',
            duration_days=None
        )
        
        # Assert
        assert result['success'] is True
        assert result['action'] == 'updated'


class TestAssignModulePermission:
    """Tests para asignación de permisos de módulo"""
    
    def test_assign_new_module_permission_success(self, permissions_service, mock_db_service, sample_module_permission):
        """Test: Asignar nuevo permiso de módulo exitosamente"""
        # Arrange
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_service.get_connection.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchone.side_effect = [
            None,
            {'id': 'perm-uuid-789', 'granted_at': datetime.now()},
            sample_module_permission
        ]
        
        # Act
        result = permissions_service.assign_module_permission(
            user_id='user-123',
            user_email='test@example.com',
            module_id='module-uuid-111',
            permission_type_id='ptype-uuid-789',
            duration_days=30
        )
        
        # Assert
        assert result['success'] is True
        assert result['action'] == 'created'
        assert 'permission' in result


class TestRevokePermissions:
    """Tests para revocación de permisos"""
    
    def test_revoke_app_permission_success(self, permissions_service, mock_db_service):
        """Test: Revocar permiso de aplicación exitosamente"""
        # Arrange
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_service.get_connection.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = {'id': 'perm-uuid-123'}
        
        # Act
        result = permissions_service.revoke_app_permission(
            user_id='user-123',
            app_id='app-uuid-456'
        )
        
        # Assert
        assert result['success'] is True
        assert result['permission_id'] == 'perm-uuid-123'
        assert 'revocado' in result['message']
    
    def test_revoke_app_permission_not_found(self, permissions_service, mock_db_service):
        """Test: Error al revocar permiso inexistente"""
        # Arrange
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_service.get_connection.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError, match='Permiso no encontrado'):
            permissions_service.revoke_app_permission(
                user_id='user-123',
                app_id='app-uuid-456'
            )
    
    def test_revoke_module_permission_success(self, permissions_service, mock_db_service):
        """Test: Revocar permiso de módulo exitosamente"""
        # Arrange
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_service.get_connection.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = {'id': 'perm-uuid-789'}
        
        # Act
        result = permissions_service.revoke_module_permission(
            user_id='user-123',
            module_id='module-uuid-111'
        )
        
        # Assert
        assert result['success'] is True
        assert result['permission_id'] == 'perm-uuid-789'


class TestGetUserPermissions:
    """Tests para consulta de permisos de usuario"""
    
    def test_get_user_permissions_success(self, permissions_service, mock_db_service):
        """Test: Obtener permisos de usuario exitosamente"""
        # Arrange
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_service.get_connection.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        app_perms = [
            {'permission_id': 'p1', 'scope': 'application', 'resource_name': 'Cline'}
        ]
        module_perms = [
            {'permission_id': 'p2', 'scope': 'module', 'resource_name': 'RAG'}
        ]
        
        mock_cursor.fetchall.side_effect = [app_perms, module_perms]
        
        # Act
        result = permissions_service.get_user_permissions('user-123')
        
        # Assert
        assert result['user_id'] == 'user-123'
        assert result['total_count'] == 2
        assert result['app_permissions_count'] == 1
        assert result['module_permissions_count'] == 1
        assert len(result['permissions']) == 2
    
    def test_get_user_permissions_empty(self, permissions_service, mock_db_service):
        """Test: Usuario sin permisos"""
        # Arrange
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_service.get_connection.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.fetchall.side_effect = [[], []]
        
        # Act
        result = permissions_service.get_user_permissions('user-123')
        
        # Assert
        assert result['total_count'] == 0
        assert result['permissions'] == []


class TestListAllPermissions:
    """Tests para listar todos los permisos"""
    
    def test_list_all_permissions_success(self, permissions_service, mock_db_service):
        """Test: Listar todos los permisos del sistema"""
        # Arrange
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_service.get_connection.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        all_perms = [
            {'user_id': 'u1', 'resource_name': 'Cline', 'permission_type': 'Admin'},
            {'user_id': 'u2', 'resource_name': 'KB-Agent', 'permission_type': 'Read'}
        ]
        
        mock_cursor.fetchall.return_value = all_perms
        
        # Act
        result = permissions_service.list_all_permissions()
        
        # Assert
        assert result['total_count'] == 2
        assert len(result['permissions']) == 2


class TestCatalogs:
    """Tests para catálogos"""
    
    def test_list_permission_types(self, permissions_service, mock_db_service):
        """Test: Listar tipos de permisos"""
        # Arrange
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_service.get_connection.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        perm_types = [
            {'id': 'pt1', 'name': 'Read-only', 'level': 10},
            {'id': 'pt2', 'name': 'Write', 'level': 50},
            {'id': 'pt3', 'name': 'Admin', 'level': 100}
        ]
        
        mock_cursor.fetchall.return_value = perm_types
        
        # Act
        result = permissions_service.list_permission_types()
        
        # Assert
        assert 'permission_types' in result
        assert len(result['permission_types']) == 3
    
    def test_list_modules_all(self, permissions_service, mock_db_service):
        """Test: Listar todos los módulos"""
        # Arrange
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_service.get_connection.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        modules = [
            {'module_id': 'm1', 'module_name': 'RAG', 'application_name': 'Cline'},
            {'module_id': 'm2', 'module_name': 'Chat', 'application_name': 'Cline'}
        ]
        
        mock_cursor.fetchall.return_value = modules
        
        # Act
        result = permissions_service.list_modules()
        
        # Assert
        assert 'modules' in result
        assert len(result['modules']) == 2
    
    def test_list_modules_by_app(self, permissions_service, mock_db_service):
        """Test: Listar módulos de una aplicación específica"""
        # Arrange
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_service.get_connection.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        modules = [
            {'module_id': 'm1', 'module_name': 'RAG', 'application_name': 'Cline'}
        ]
        
        mock_cursor.fetchall.return_value = modules
        
        # Act
        result = permissions_service.list_modules(app_id='app-uuid-456')
        
        # Assert
        assert 'modules' in result
        assert len(result['modules']) == 1
        # Verificar que se pasó el app_id en la query
        execute_call = mock_cursor.execute.call_args
        assert 'app-uuid-456' in execute_call[0][1]
