"""
Unit tests for jwt_service module
"""
import pytest
import jwt
import json
import sys
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Mock psycopg2 and its submodules before importing services
mock_psycopg2 = Mock()
mock_psycopg2.extras = Mock()
mock_psycopg2.extras.RealDictCursor = Mock()
sys.modules['psycopg2'] = mock_psycopg2
sys.modules['psycopg2.extras'] = mock_psycopg2.extras

from services.jwt_service import JWTService


class TestJWTServiceInit:
    """Tests for JWTService initialization"""
    
    def test_init_default_values(self):
        """Test: Service initializes with default values"""
        service = JWTService()
        
        assert service.secret_key is None
        assert service.algorithm == 'HS256'
    
    def test_validity_periods_defined(self):
        """Test: Validity periods are properly defined"""
        assert JWTService.VALIDITY_PERIODS == {
            '1_day': 24,
            '7_days': 168,
            '30_days': 720,
            '60_days': 1440,
            '90_days': 2160
        }


class TestGetSecretKey:
    """Tests for _get_secret_key method"""
    
    @patch('services.jwt_service.boto3.client')
    def test_get_secret_key_from_secrets_manager(self, mock_boto_client, monkeypatch):
        """Test: Get secret key from AWS Secrets Manager"""
        monkeypatch.setenv('JWT_SECRET_NAME', 'test-jwt-secret')
        monkeypatch.setenv('AWS_REGION', 'eu-west-1')
        
        # Mock Secrets Manager response
        mock_sm = Mock()
        mock_sm.get_secret_value.return_value = {
            'SecretString': json.dumps({'jwt_secret_key': 'test-secret-key-12345'})
        }
        mock_boto_client.return_value = mock_sm
        
        service = JWTService()
        secret_key = service._get_secret_key()
        
        assert secret_key == 'test-secret-key-12345'
        assert service.secret_key == 'test-secret-key-12345'
        mock_boto_client.assert_called_once_with('secretsmanager', region_name='eu-west-1')
    
    @patch('services.jwt_service.boto3.client')
    def test_get_secret_key_cached(self, mock_boto_client, monkeypatch):
        """Test: Secret key is cached after first retrieval"""
        monkeypatch.setenv('JWT_SECRET_NAME', 'test-jwt-secret')
        
        mock_sm = Mock()
        mock_sm.get_secret_value.return_value = {
            'SecretString': json.dumps({'jwt_secret_key': 'test-secret-key-12345'})
        }
        mock_boto_client.return_value = mock_sm
        
        service = JWTService()
        secret_key1 = service._get_secret_key()
        secret_key2 = service._get_secret_key()
        
        assert secret_key1 == secret_key2
        # Should only call boto3 once (cached)
        mock_boto_client.assert_called_once()
    
    @patch('services.jwt_service.boto3.client')
    def test_get_secret_key_fallback_to_env(self, mock_boto_client, monkeypatch):
        """Test: Fallback to environment variable if Secrets Manager fails"""
        monkeypatch.setenv('JWT_SECRET_KEY', 'fallback-secret-key')
        
        # Mock Secrets Manager failure
        mock_sm = Mock()
        mock_sm.get_secret_value.side_effect = Exception('Secrets Manager error')
        mock_boto_client.return_value = mock_sm
        
        service = JWTService()
        secret_key = service._get_secret_key()
        
        assert secret_key == 'fallback-secret-key'


class TestGenerateToken:
    """Tests for generate_token method"""
    
    @pytest.fixture
    def jwt_service(self):
        """Create JWT service with mocked secret key"""
        service = JWTService()
        service.secret_key = 'test-secret-key-for-testing-12345'
        return service
    
    @pytest.fixture
    def user_info(self):
        """Sample user info"""
        return {
            'user_id': 'test-user-123',
            'email': 'test@example.com',
            'person': 'Test User',
            'groups': ['developers-group']
        }
    
    @pytest.fixture
    def profile_info(self):
        """Sample profile info"""
        return {
            'profile_id': 'profile-uuid-123',
            'profile_name': 'Test Profile',
            'model_id': 'anthropic.claude-sonnet-4-5-20250929-v1:0'
        }
    
    def test_generate_token_success(self, jwt_service, user_info, profile_info):
        """Test: Successfully generate JWT token"""
        result = jwt_service.generate_token(user_info, profile_info, '90_days')
        
        assert 'jwt' in result
        assert 'jti' in result
        assert 'token_hash' in result
        assert 'issued_at' in result
        assert 'expires_at' in result
        assert 'validity_days' in result
        assert 'payload' in result
        
        assert result['validity_days'] == 90
        assert isinstance(result['jwt'], str)
        assert len(result['jti']) == 36  # UUID format
    
    def test_generate_token_payload_structure(self, jwt_service, user_info, profile_info):
        """Test: Token payload has correct structure"""
        result = jwt_service.generate_token(user_info, profile_info, '30_days')
        payload = result['payload']
        
        assert payload['user_id'] == 'test-user-123'
        assert payload['email'] == 'test@example.com'
        assert payload['person'] == 'Test User'
        assert payload['team'] == 'developers-group'
        assert payload['default_inference_profile'] == 'profile-uuid-123'
        assert payload['iss'] == 'identity-manager'
        assert payload['sub'] == 'test-user-123'
        assert payload['aud'] == ['bedrock-proxy', 'kb-agent']
        assert 'exp' in payload
        assert 'iat' in payload
        assert 'jti' in payload
    
    def test_generate_token_different_validity_periods(self, jwt_service, user_info, profile_info):
        """Test: Different validity periods generate correct expiration"""
        periods = {
            '1_day': 1,
            '7_days': 7,
            '30_days': 30,
            '60_days': 60,
            '90_days': 90
        }
        
        for period, expected_days in periods.items():
            result = jwt_service.generate_token(user_info, profile_info, period)
            assert result['validity_days'] == expected_days
    
    def test_generate_token_invalid_validity_period(self, jwt_service, user_info, profile_info):
        """Test: Invalid validity period raises error"""
        with pytest.raises(ValueError, match='Período de validez inválido'):
            jwt_service.generate_token(user_info, profile_info, 'invalid_period')
    
    def test_generate_token_unique_jti(self, jwt_service, user_info, profile_info):
        """Test: Each token gets unique JTI"""
        result1 = jwt_service.generate_token(user_info, profile_info)
        result2 = jwt_service.generate_token(user_info, profile_info)
        
        assert result1['jti'] != result2['jti']
    
    def test_generate_token_user_without_groups(self, jwt_service, profile_info):
        """Test: Handle user without groups"""
        user_info = {
            'user_id': 'test-user-123',
            'email': 'test@example.com',
            'person': 'Test User',
            'groups': []
        }
        
        result = jwt_service.generate_token(user_info, profile_info)
        assert result['payload']['team'] == 'unknown'
    
    def test_generate_token_can_be_decoded(self, jwt_service, user_info, profile_info):
        """Test: Generated token can be decoded"""
        result = jwt_service.generate_token(user_info, profile_info)
        token = result['jwt']
        
        # Decode without verification to check structure
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        assert decoded['user_id'] == user_info['user_id']
        assert decoded['email'] == user_info['email']


class TestValidateToken:
    """Tests for validate_token method"""
    
    @pytest.fixture
    def jwt_service(self):
        """Create JWT service with mocked secret key"""
        service = JWTService()
        service.secret_key = 'test-secret-key-for-testing-12345'
        return service
    
    @pytest.fixture
    def valid_token(self, jwt_service):
        """Generate a valid token for testing"""
        user_info = {
            'user_id': 'test-user-123',
            'email': 'test@example.com',
            'person': 'Test User',
            'groups': ['developers-group']
        }
        profile_info = {
            'profile_id': 'profile-uuid-123',
            'profile_name': 'Test Profile'
        }
        result = jwt_service.generate_token(user_info, profile_info, '1_day')
        return result['jwt']
    
    def test_validate_token_success(self, jwt_service, valid_token):
        """Test: Successfully validate a valid token"""
        payload = jwt_service.validate_token(valid_token)
        
        assert payload['user_id'] == 'test-user-123'
        assert payload['email'] == 'test@example.com'
        assert payload['iss'] == 'identity-manager'
        assert 'bedrock-proxy' in payload['aud']
    
    def test_validate_token_expired(self, jwt_service):
        """Test: Expired token raises ExpiredSignatureError"""
        # Create an expired token
        now = datetime.utcnow()
        payload = {
            'user_id': 'test-user',
            'email': 'test@example.com',
            'iss': 'identity-manager',
            'sub': 'test-user',
            'aud': ['bedrock-proxy', 'kb-agent'],
            'exp': int((now - timedelta(hours=1)).timestamp()),  # Expired 1 hour ago
            'iat': int((now - timedelta(hours=2)).timestamp())
        }
        
        expired_token = jwt.encode(payload, jwt_service.secret_key, algorithm='HS256')
        
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt_service.validate_token(expired_token)
    
    def test_validate_token_invalid_signature(self, jwt_service, valid_token):
        """Test: Token with invalid signature raises InvalidTokenError"""
        # Change the secret key
        jwt_service.secret_key = 'different-secret-key'
        
        with pytest.raises(jwt.InvalidTokenError):
            jwt_service.validate_token(valid_token)
    
    def test_validate_token_malformed(self, jwt_service):
        """Test: Malformed token raises InvalidTokenError"""
        with pytest.raises(jwt.InvalidTokenError):
            jwt_service.validate_token('not.a.valid.token')


class TestDecodeTokenWithoutValidation:
    """Tests for decode_token_without_validation method"""
    
    @pytest.fixture
    def jwt_service(self):
        """Create JWT service"""
        service = JWTService()
        service.secret_key = 'test-secret-key-for-testing-12345'
        return service
    
    def test_decode_without_validation_success(self, jwt_service):
        """Test: Decode token without validation"""
        user_info = {
            'user_id': 'test-user-123',
            'email': 'test@example.com',
            'person': 'Test User',
            'groups': ['developers-group']
        }
        profile_info = {'profile_id': 'profile-uuid-123'}
        
        result = jwt_service.generate_token(user_info, profile_info)
        token = result['jwt']
        
        decoded = jwt_service.decode_token_without_validation(token)
        
        assert decoded['user_id'] == 'test-user-123'
        assert decoded['email'] == 'test@example.com'
    
    def test_decode_without_validation_expired_token(self, jwt_service):
        """Test: Can decode expired token without validation"""
        now = datetime.utcnow()
        payload = {
            'user_id': 'test-user',
            'exp': int((now - timedelta(hours=1)).timestamp())  # Expired
        }
        
        expired_token = jwt.encode(payload, jwt_service.secret_key, algorithm='HS256')
        decoded = jwt_service.decode_token_without_validation(expired_token)
        
        assert decoded['user_id'] == 'test-user'
    
    def test_decode_without_validation_malformed(self, jwt_service):
        """Test: Malformed token raises ValueError"""
        with pytest.raises(ValueError, match='Token malformado'):
            jwt_service.decode_token_without_validation('not.a.valid.token')


class TestCalculateHash:
    """Tests for _calculate_hash method"""
    
    def test_calculate_hash_consistent(self):
        """Test: Same token produces same hash"""
        service = JWTService()
        token = 'test.jwt.token'
        
        hash1 = service._calculate_hash(token)
        hash2 = service._calculate_hash(token)
        
        assert hash1 == hash2
    
    def test_calculate_hash_different_tokens(self):
        """Test: Different tokens produce different hashes"""
        service = JWTService()
        
        hash1 = service._calculate_hash('token1')
        hash2 = service._calculate_hash('token2')
        
        assert hash1 != hash2
    
    def test_calculate_hash_format(self):
        """Test: Hash is hexadecimal string"""
        service = JWTService()
        token_hash = service._calculate_hash('test.token')
        
        assert isinstance(token_hash, str)
        assert len(token_hash) == 64  # SHA-256 produces 64 hex characters
        assert all(c in '0123456789abcdef' for c in token_hash)


class TestVerifyTokenHash:
    """Tests for verify_token_hash method"""
    
    def test_verify_token_hash_match(self):
        """Test: Matching hash returns True"""
        service = JWTService()
        token = 'test.jwt.token'
        stored_hash = service._calculate_hash(token)
        
        assert service.verify_token_hash(token, stored_hash) is True
    
    def test_verify_token_hash_mismatch(self):
        """Test: Non-matching hash returns False"""
        service = JWTService()
        token = 'test.jwt.token'
        wrong_hash = service._calculate_hash('different.token')
        
        assert service.verify_token_hash(token, wrong_hash) is False


class TestStaticMethods:
    """Tests for static methods"""
    
    def test_get_validity_period_hours(self):
        """Test: Get hours for validity period"""
        assert JWTService.get_validity_period_hours('1_day') == 24
        assert JWTService.get_validity_period_hours('7_days') == 168
        assert JWTService.get_validity_period_hours('30_days') == 720
        assert JWTService.get_validity_period_hours('60_days') == 1440
        assert JWTService.get_validity_period_hours('90_days') == 2160
    
    def test_get_validity_period_hours_invalid(self):
        """Test: Invalid period returns default"""
        assert JWTService.get_validity_period_hours('invalid') == 2160
    
    def test_get_available_validity_periods(self):
        """Test: Get all available validity periods"""
        periods = JWTService.get_available_validity_periods()
        
        assert '1_day' in periods
        assert '7_days' in periods
        assert '30_days' in periods
        assert '60_days' in periods
        assert '90_days' in periods
        
        # Check structure
        assert periods['1_day']['hours'] == 24
        assert periods['1_day']['days'] == 1
        assert 'description' in periods['1_day']
        
        assert periods['90_days']['hours'] == 2160
        assert periods['90_days']['days'] == 90
