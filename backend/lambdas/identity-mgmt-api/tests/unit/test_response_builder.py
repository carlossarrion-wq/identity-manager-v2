"""
Unit tests for response_builder module
"""
import pytest
import json
from utils.response_builder import (
    build_response,
    build_error_response,
    build_validation_error_response,
    build_not_found_response,
    build_unauthorized_response,
    build_forbidden_response
)


class TestBuildResponse:
    """Tests for build_response function"""
    
    def test_success_response_with_data(self):
        """Test: Successful response with data"""
        data = {'user_id': '123', 'email': 'test@example.com'}
        response = build_response(data)
        
        assert response['statusCode'] == 200
        assert 'body' in response
        
        body = json.loads(response['body'])
        assert body['success'] is True
        assert body['data'] == data
        assert 'timestamp' in body
    
    def test_success_response_with_custom_status(self):
        """Test: Successful response with custom status code"""
        data = {'token_id': 'abc-123'}
        response = build_response(data, status_code=201)
        
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['success'] is True
        assert body['data'] == data
    
    def test_success_response_with_message(self):
        """Test: Successful response with message"""
        data = {'result': 'ok'}
        message = 'Operation completed successfully'
        response = build_response(data, message=message)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        assert body['data'] == data
        assert body['message'] == message
    
    def test_response_has_cors_headers(self):
        """Test: Response includes CORS headers"""
        response = build_response({'test': 'data'})
        
        assert 'headers' in response
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
        assert response['headers']['Access-Control-Allow-Headers'] == 'Content-Type,Authorization'
        assert response['headers']['Access-Control-Allow-Methods'] == 'GET,POST,PUT,DELETE,OPTIONS'
        assert response['headers']['Content-Type'] == 'application/json'
    
    def test_response_body_is_json_string(self):
        """Test: Response body is a JSON string"""
        data = {'key': 'value'}
        response = build_response(data)
        
        assert isinstance(response['body'], str)
        # Should be able to parse it back
        parsed = json.loads(response['body'])
        assert parsed['data'] == data


class TestBuildErrorResponse:
    """Tests for build_error_response function"""
    
    def test_error_response_basic(self):
        """Test: Basic error response"""
        error_code = 'INTERNAL_ERROR'
        error_message = 'Something went wrong'
        response = build_error_response(error_code, error_message, 500)
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['success'] is False
        assert body['error']['code'] == error_code
        assert body['error']['message'] == error_message
        assert 'timestamp' in body
    
    def test_error_response_with_details(self):
        """Test: Error response with details"""
        error_code = 'VALIDATION_ERROR'
        error_message = 'Validation failed'
        details = {'field': 'email', 'reason': 'invalid format'}
        response = build_error_response(error_code, error_message, 400, details)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
        assert body['error']['code'] == error_code
        assert body['error']['message'] == error_message
        assert body['error']['details'] == details
    
    def test_error_response_has_cors_headers(self):
        """Test: Error response includes CORS headers"""
        response = build_error_response('ERROR', 'Error message', 500)
        
        assert 'headers' in response
        assert response['headers']['Access-Control-Allow-Origin'] == '*'


class TestBuildValidationErrorResponse:
    """Tests for build_validation_error_response function"""
    
    def test_validation_error_basic(self):
        """Test: Basic validation error"""
        validation_errors = {'email': 'Email is required'}
        response = build_validation_error_response(validation_errors)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
        assert body['error']['code'] == 'VALIDATION_ERROR'
        assert 'validación' in body['error']['message'].lower()
        assert body['error']['details']['validation_errors'] == validation_errors
    
    def test_validation_error_multiple_fields(self):
        """Test: Validation error with multiple fields"""
        validation_errors = {
            'email': 'Invalid format',
            'password': 'Too short',
            'name': 'Required field'
        }
        response = build_validation_error_response(validation_errors)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'VALIDATION_ERROR'
        assert body['error']['details']['validation_errors'] == validation_errors


class TestBuildNotFoundResponse:
    """Tests for build_not_found_response function"""
    
    def test_not_found_basic(self):
        """Test: Basic not found response"""
        resource_type = 'User'
        resource_id = '123'
        response = build_not_found_response(resource_type, resource_id)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['success'] is False
        assert body['error']['code'] == 'NOT_FOUND'
        assert resource_type in body['error']['message']
        assert body['error']['details']['resource_type'] == resource_type
        assert body['error']['details']['resource_id'] == resource_id
    
    def test_not_found_token(self):
        """Test: Token not found"""
        resource_type = 'Token'
        resource_id = 'abc-123'
        response = build_not_found_response(resource_type, resource_id)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error']['details']['resource_type'] == resource_type
        assert body['error']['details']['resource_id'] == resource_id


class TestBuildUnauthorizedResponse:
    """Tests for build_unauthorized_response function"""
    
    def test_unauthorized_default(self):
        """Test: Default unauthorized response"""
        response = build_unauthorized_response()
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['success'] is False
        assert body['error']['code'] == 'UNAUTHORIZED'
        assert 'autorizado' in body['error']['message'].lower()
    
    def test_unauthorized_custom_message(self):
        """Test: Unauthorized with custom message"""
        message = 'Invalid token'
        response = build_unauthorized_response(message)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error']['code'] == 'UNAUTHORIZED'
        assert body['error']['message'] == message


class TestBuildForbiddenResponse:
    """Tests for build_forbidden_response function"""
    
    def test_forbidden_default(self):
        """Test: Default forbidden response"""
        response = build_forbidden_response()
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body['success'] is False
        assert body['error']['code'] == 'FORBIDDEN'
        assert 'acceso' in body['error']['message'].lower() or 'denegado' in body['error']['message'].lower()
    
    def test_forbidden_custom_message(self):
        """Test: Forbidden with custom message"""
        message = 'Insufficient permissions'
        response = build_forbidden_response(message)
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body['error']['code'] == 'FORBIDDEN'
        assert body['error']['message'] == message


class TestResponseConsistency:
    """Tests for response consistency across all builders"""
    
    def test_all_responses_have_required_fields(self):
        """Test: All responses have required fields"""
        responses = [
            build_response({'data': 'test'}),
            build_error_response('ERROR', 'Error message', 500),
            build_validation_error_response({'field': 'error'}),
            build_not_found_response('Resource', '123'),
            build_unauthorized_response(),
            build_forbidden_response()
        ]
        
        for response in responses:
            assert 'statusCode' in response
            assert 'headers' in response
            assert 'body' in response
            assert isinstance(response['body'], str)
            
            # Parse body and check structure
            body = json.loads(response['body'])
            assert 'success' in body
            assert 'timestamp' in body
    
    def test_all_responses_have_cors_headers(self):
        """Test: All responses include CORS headers"""
        responses = [
            build_response({'data': 'test'}),
            build_error_response('ERROR', 'Error message', 500),
            build_validation_error_response({'field': 'error'}),
            build_not_found_response('Resource', '123'),
            build_unauthorized_response(),
            build_forbidden_response()
        ]
        
        for response in responses:
            headers = response['headers']
            assert 'Access-Control-Allow-Origin' in headers
            assert 'Access-Control-Allow-Headers' in headers
            assert 'Access-Control-Allow-Methods' in headers
            assert 'Content-Type' in headers
    
    def test_success_responses_have_success_true(self):
        """Test: Success responses have success=true"""
        response = build_response({'data': 'test'})
        body = json.loads(response['body'])
        assert body['success'] is True
    
    def test_error_responses_have_success_false(self):
        """Test: Error responses have success=false"""
        error_responses = [
            build_error_response('ERROR', 'Error message', 500),
            build_validation_error_response({'field': 'error'}),
            build_not_found_response('Resource', '123'),
            build_unauthorized_response(),
            build_forbidden_response()
        ]
        
        for response in error_responses:
            body = json.loads(response['body'])
            assert body['success'] is False
    
    def test_error_responses_have_error_structure(self):
        """Test: Error responses have consistent error structure"""
        error_responses = [
            build_error_response('ERROR', 'Error message', 500),
            build_validation_error_response({'field': 'error'}),
            build_not_found_response('Resource', '123'),
            build_unauthorized_response(),
            build_forbidden_response()
        ]
        
        for response in error_responses:
            body = json.loads(response['body'])
            assert 'error' in body
            assert 'code' in body['error']
            assert 'message' in body['error']
