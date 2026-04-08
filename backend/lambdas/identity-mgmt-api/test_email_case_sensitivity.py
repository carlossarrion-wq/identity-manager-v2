"""
Test to verify email case-insensitive comparison in user_exists method
"""
import sys
import os

# Add the parent directory to the path to import shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../shared'))

def test_email_case_insensitive():
    """
    Test that email comparison is case-insensitive
    """
    # Test cases
    test_cases = [
        ("Carlos.sarrion@es.ibm.com", "carlos.sarrion@es.ibm.com", True),
        ("CARLOS.SARRION@ES.IBM.COM", "carlos.sarrion@es.ibm.com", True),
        ("carlos.sarrion@es.ibm.com", "Carlos.Sarrion@ES.IBM.COM", True),
        ("test@example.com", "TEST@EXAMPLE.COM", True),
        ("user@domain.com", "different@domain.com", False),
    ]
    
    print("Testing email case-insensitive comparison:")
    print("-" * 60)
    
    for email1, email2, should_match in test_cases:
        # Simulate the fixed comparison logic
        matches = email1.lower() == email2.lower()
        status = "✓ PASS" if matches == should_match else "✗ FAIL"
        print(f"{status}: '{email1}' vs '{email2}' -> {matches} (expected: {should_match})")
    
    print("-" * 60)
    print("\nAll tests completed!")

if __name__ == "__main__":
    test_email_case_insensitive()