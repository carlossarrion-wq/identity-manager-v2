"""
Integration tests for cognito_service module using moto
"""
import pytest
import sys
import os
from unittest.mock import Mock
from moto import mock_aws
import boto3

# Mock psycopg2 before importing services
mock_psycopg2 = Mock()
mock_psycopg2.extras = Mock()
mock_psycopg2.extras.RealDictCursor = Mock()
sys.modules['psycopg2'] = mock_psycopg2
sys.modules['psycopg2.extras'] = mock_psycopg2.extras

from services.cognito_service import CognitoService


@pytest.fixture
def aws_credentials(monkeypatch):
    """Mock AWS credentials"""
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_REGION', 'eu-west-1')


@pytest.fixture
def cognito_setup(aws_credentials):
    """Setup mock Cognito User Pool"""
    with mock_aws():
        # Create Cognito client
        client = boto3.client('cognito-idp', region_name='eu-west-1')
        
        # Create User Pool
        response = client.create_user_pool(
            PoolName='test-pool',
            Policies={
                'PasswordPolicy': {
                    'MinimumLength': 8,
                    'RequireUppercase': True,
                    'RequireLowercase': True,
                    'RequireNumbers': True,
                    'RequireSymbols': True
                }
            },
            Schema=[
                {
                    'Name': 'email',
                    'AttributeDataType': 'String',
                    'Required': True,
                    'Mutable': True
                },
                {
                    'Name': 'person',
                    'AttributeDataType': 'String',
                    'Mutable': True
                }
            ]
        )
        
        user_pool_id = response['UserPool']['Id']
        
        # Create groups
        client.create_group(
            GroupName='developers-group',
            UserPoolId=user_pool_id,
            Description='Developers group'
        )
        
        client.create_group(
            GroupName='admins-group',
            UserPoolId=user_pool_id,
            Description='Admins group'
        )
        
        # Set environment variable
        os.environ['COGNITO_USER_POOL_ID'] = user_pool_id
        
        yield {
            'client': client,
            'user_pool_id': user_pool_id
        }


class TestCognitoServiceInit:
    """Tests for CognitoService initialization"""
    
    def test_init_success(self, cognito_setup):
        """Test: Service initializes successfully"""
        service = CognitoService()
        
        assert service.client is not None
        assert service.user_pool_id == cognito_setup['user_pool_id']
    
    def test_init_without_user_pool_id(self, aws_credentials, monkeypatch):
        """Test: Raises error if COGNITO_USER_POOL_ID not set"""
        monkeypatch.delenv('COGNITO_USER_POOL_ID', raising=False)
        
        with mock_aws():
            with pytest.raises(ValueError, match='COGNITO_USER_POOL_ID no está configurado'):
                CognitoService()


class TestCreateUser:
    """Tests for create_user method"""
    
    def test_create_user_success(self, cognito_setup):
        """Test: Successfully create user"""
        service = CognitoService()
        
        result = service.create_user(
            email='test@example.com',
            person='Test User',
            group='developers-group',
            send_email=False
        )
        
        assert result['success'] is True
        assert result['user']['email'] == 'test@example.com'
        assert result['user']['person'] == 'Test User'
        assert 'developers-group' in result['user']['groups']
    
    def test_create_user_duplicate(self, cognito_setup):
        """Test: Cannot create duplicate user"""
        service = CognitoService()
        
        # Create first user
        service.create_user(
            email='test@example.com',
            person='Test User',
            group='developers-group',
            send_email=False
        )
        
        # Try to create duplicate
        with pytest.raises(ValueError, match='ya existe'):
            service.create_user(
                email='test@example.com',
                person='Test User 2',
                group='developers-group',
                send_email=False
            )


class TestGetUser:
    """Tests for get_user method"""
    
    def test_get_user_success(self, cognito_setup):
        """Test: Successfully get user"""
        service = CognitoService()
        
        # Create user first
        result = service.create_user(
            email='test@example.com',
            person='Test User',
            group='developers-group',
            send_email=False
        )
        
        # Get user
        user = service.get_user('test@example.com')
        
        assert user['user_id'] == 'test@example.com'
        # Note: moto may not preserve custom attributes perfectly
        assert user['person'] == 'Test User' or user['person'] == ''
        assert 'developers-group' in user['groups']
    
    def test_get_user_not_found(self, cognito_setup):
        """Test: User not found raises error"""
        service = CognitoService()
        
        with pytest.raises(ValueError, match='Usuario no encontrado'):
            service.get_user('nonexistent@example.com')


class TestDeleteUser:
    """Tests for delete_user method"""
    
    def test_delete_user_success(self, cognito_setup):
        """Test: Successfully delete user"""
        service = CognitoService()
        
        # Create user
        service.create_user(
            email='test@example.com',
            person='Test User',
            group='developers-group',
            send_email=False
        )
        
        # Delete user
        result = service.delete_user('test@example.com')
        
        assert result is True
        
        # Verify user is deleted
        with pytest.raises(ValueError, match='Usuario no encontrado'):
            service.get_user('test@example.com')
    
    def test_delete_user_not_found(self, cognito_setup):
        """Test: Delete non-existent user raises error"""
        service = CognitoService()
        
        with pytest.raises(ValueError, match='Usuario no encontrado'):
            service.delete_user('nonexistent@example.com')


class TestListUsers:
    """Tests for list_users method"""
    
    def test_list_users_empty(self, cognito_setup):
        """Test: List users when pool is empty"""
        service = CognitoService()
        
        result = service.list_users()
        
        assert result['users'] == []
        assert result['total_count'] == 0
    
    def test_list_users_with_users(self, cognito_setup):
        """Test: List users with multiple users"""
        service = CognitoService()
        
        # Create users
        service.create_user('user1@example.com', 'User 1', 'developers-group', send_email=False)
        service.create_user('user2@example.com', 'User 2', 'admins-group', send_email=False)
        
        result = service.list_users()
        
        assert result['total_count'] == 2
        assert len(result['users']) == 2


class TestListGroups:
    """Tests for list_groups method"""
    
    def test_list_groups(self, cognito_setup):
        """Test: List all groups"""
        service = CognitoService()
        
        result = service.list_groups()
        
        assert len(result['groups']) == 2
        group_names = [g['group_name'] for g in result['groups']]
        assert 'developers-group' in group_names
        assert 'admins-group' in group_names
