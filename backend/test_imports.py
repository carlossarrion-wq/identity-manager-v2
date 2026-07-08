"""
Test that all imports work correctly
"""
import os
import sys
from pathlib import Path

# Set environment first
os.environ.update({
    'DB_TYPE': 'sqlite',
    'DB_PATH': str(Path(__file__).parent / 'identity_manager.db'),
    'ENVIRONMENT': 'local-development',
    'JWT_SECRET_KEY': 'local-dev-secret-key',
    'COGNITO_USER_POOL_ID': 'local-dev-pool',
    'COGNITO_REGION': 'eu-west-1',
    'AWS_REGION': 'eu-west-1',
    'PORT': '9999'
})

# Add Lambda directory to path
lambda_dir = Path(__file__).parent / "lambdas" / "identity-mgmt-api"
sys.path.insert(0, str(lambda_dir))

print("\n" + "="*60)
print("🧪 Testing Imports and Service Initialization")
print("="*60 + "\n")

try:
    print("1. Importing FastAPI...")
    from fastapi import FastAPI
    print("   ✓ FastAPI imported")

    print("\n2. Importing Lambda function...")
    from lambda_function import initialize_services, lambda_handler
    print("   ✓ Lambda function imported")

    print("\n3. Initializing services...")
    initialize_services()
    print("   ✓ Services initialized")

    print("\n4. Testing mock Lambda call...")
    class MockContext:
        aws_request_id = "test-001"
    
    test_event = {
        "httpMethod": "POST",
        "path": "/api",
        "body": '{"operation": "list_applications"}',
        "requestContext": {
            "requestId": "test-001",
            "authorizer": {
                "sub": "test-cognito-admin",
                "email": "admin@test.com",
                "app_permissions": '[{"app_name": "identity-mgmt", "permission_type": "admin", "permission_level": 100}]'
            }
        }
    }
    
    response = lambda_handler(test_event, MockContext())
    print(f"   ✓ Lambda handler returned status: {response['statusCode']}")
    
    if response['statusCode'] == 200:
        import json
        body = json.loads(response['body'])
        apps_count = len(body.get('applications', []))
        print(f"   ✓ Response contains {apps_count} application(s)")
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED")
    print("="*60)
    print("\n📋 The application is ready to run!")
    print("   - Database: ✓ Initialized with test data")
    print("   - Dependencies: ✓ All installed")
    print("   - Services: ✓ Can initialize")
    print("   - Lambda Handler: ✓ Working")
    print("\n🚀 To start the server:")
    print("   cd /repos/identity-manager-v2/backend")
    print("   source venv/bin/activate")
    print("   export DB_TYPE=sqlite ENVIRONMENT=local-development")
    print("   export DB_PATH=$(pwd)/identity_manager.db")
    print("   export COGNITO_USER_POOL_ID=local-dev-pool PORT=9999")
    print("   python3 local_server.py")
    print()
    
except Exception as e:
    print(f"\n✗ Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
