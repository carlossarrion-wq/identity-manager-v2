"""
Unit tests for validators module
"""
import pytest
from utils.validators import validate_email, validate_uuid


class TestValidateEmail:
    """Tests for email validation"""
    
    def test_valid_email(self):
        """Test: Valid email addresses"""
        valid_emails = [
            'test@example.com',
            'user.name@example.com',
            'user+tag@example.co.uk',
            'test123@test-domain.com'
        ]
        
        for email in valid_emails:
            assert validate_email(email) is True, f"Email {email} should be valid"
    
    def test_invalid_email(self):
        """Test: Invalid email addresses"""
        invalid_emails = [
            'invalid',
            '@example.com',
            'user@',
            'user @example.com',
            'user@.com',
            ''
        ]
        
        for email in invalid_emails:
            assert validate_email(email) is False, f"Email {email} should be invalid"
    
    def test_none_email(self):
        """Test: None email"""
        assert validate_email(None) is False


class TestValidateUUID:
    """Tests for UUID validation"""
    
    def test_valid_uuid(self):
        """Test: Valid UUIDs"""
        valid_uuids = [
            '550e8400-e29b-41d4-a716-446655440000',
            '6ba7b810-9dad-11d1-80b4-00c04fd430c8',
            'f47ac10b-58cc-4372-a567-0e02b2c3d479'
        ]
        
        for uuid_str in valid_uuids:
            assert validate_uuid(uuid_str) is True, f"UUID {uuid_str} should be valid"
    
    def test_invalid_uuid(self):
        """Test: Invalid UUIDs"""
        invalid_uuids = [
            'not-a-uuid',
            '550e8400-e29b-41d4-a716',  # Too short
            '550e8400-e29b-41d4-a716-446655440000-extra',  # Too long
            '550e8400e29b41d4a716446655440000',  # No hyphens
            ''
        ]
        
        for uuid_str in invalid_uuids:
            assert validate_uuid(uuid_str) is False, f"UUID {uuid_str} should be invalid"
    
    def test_none_uuid(self):
        """Test: None UUID"""
        assert validate_uuid(None) is False


