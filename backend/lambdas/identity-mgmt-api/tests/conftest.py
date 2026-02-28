"""
Pytest configuration and shared fixtures
"""
import pytest
import os
import sys
from unittest.mock import Mock
import json

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def mock_aws_credentials(monkeypatch):
    """Mock AWS credentials for testing"""
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_REGION', 'eu-west-1')


@pytest.fixture
def mock_environment_variables(monkeypatch):
    """Mock environment variables for Lambda"""
    monkeypatch.setenv('AWS_REGION', 'eu-west-1')
    monkeypatch.setenv('COGNITO_USER_POOL_ID', 'eu-west-1_TestPool')
    monkeypatch.setenv('DB_SECRET_NAME', 'test-db-secret')
    monkeypatch.setenv('JWT_SECRET_NAME', 'test-jwt-secret')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')


@pytest.fixture
def sample_user_info():
    """Sample user information"""
    return {
        'user_id': 'test-user-123',
        'email': 'test@example.com',
        'person': 'Test User',
        'groups': ['developers-group'],
        'status': 'CONFIRMED',
        'enabled': True
    }


@pytest.fixture
def sample_profile_info():
    """Sample profile information"""
    return {
        'profile_id': 'profile-uuid-123',
        'profile_name': 'Test Profile',
        'model_id': 'anthropic.claude-sonnet-4-5-20250929-v1:0',
        'model_arn': 'arn:aws:bedrock:eu-west-1:123456789012:inference-profile/test-profile',
        'is_active': True
    }


@pytest.fixture
def sample_jwt_payload():
    """Sample JWT payload"""
    return {
        'user_id': 'test-user-123',
        'email': 'test@example.com',
        'person': 'Test User',
        'team': 'developers-group',
        'default_inference_profile': 'profile-uuid-123',
        'iss': 'identity-manager',
        'sub': 'test-user-123',
        'aud': ['bedrock-proxy', 'kb-agent'],
        'jti': 'test-jti-123'
    }


@pytest.fixture
def mock_secrets_manager():
    """Mock AWS Secrets Manager"""
    mock_sm = Mock()
    mock_sm.get_secret_value.return_value = {
        'SecretString': json.dumps({
            'host': 'localhost',
            'port': '5432',
            'dbname': 'test_db',
            'username': 'testuser',
            'password': 'testpass',
            'jwt_secret_key': 'test-jwt-secret-key-12345'
        })
    }
    return mock_sm


@pytest.fixture
def sample_lambda_event():
    """Sample Lambda event"""
    return {
        'httpMethod': 'POST',
        'path': '/api/tokens',
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'operation': 'create_token',
            'data': {
                'user_id': 'test@example.com',
                'validity_period': '90_days',
                'application_profile_id': 'profile-uuid-123'
            }
        })
    }


@pytest.fixture
def sample_lambda_context():
    """Sample Lambda context"""
    context = Mock()
    context.function_name = 'identity-mgmt-dev-api-lmbd'
    context.function_version = '$LATEST'
    context.invoked_function_arn = 'arn:aws:lambda:eu-west-1:123456789012:function:identity-mgmt-dev-api-lmbd'
    context.memory_limit_in_mb = '512'
    context.aws_request_id = 'test-request-id-123'
    context.log_group_name = '/aws/lambda/identity-mgmt-dev-api-lmbd'
    context.log_stream_name = '2026/02/28/[$LATEST]test-stream'
    return context
