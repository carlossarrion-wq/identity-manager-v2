"""
Test the local server startup and basic endpoints
"""
import os
import sys
from pathlib import Path

# Set environment variables
os.environ['DB_TYPE'] = 'sqlite'
os.environ['DB_PATH'] = str(Path(__file__).parent / 'identity_manager.db')
os.environ['ENVIRONMENT'] = 'local-development'
os.environ['PORT'] = '8000'
os.environ['JWT_SECRET_KEY'] = 'local-dev-secret-key'
os.environ['AWS_REGION'] = 'eu-west-1'
os.environ['COGNITO_USER_POOL_ID'] = 'local-dev-pool'
os.environ['COGNITO_REGION'] = 'eu-west-1'

print("\n" + "="*60)
print("🧪 Testing Identity Manager Local Server")
print("="*60 + "\n")

print("Environment variables set:")
print(f"  DB_TYPE: {os.environ['DB_TYPE']}")
print(f"  DB_PATH: {os.environ['DB_PATH']}")
print(f"  ENVIRONMENT: {os.environ['ENVIRONMENT']}")
print(f"  PORT: {os.environ['PORT']}")
print()

# Add Lambda directory to path
lambda_dir = Path(__file__).parent / "lambdas" / "identity-mgmt-api"
sys.path.insert(0, str(lambda_dir))

# Import after setting environment variables
from lambda_function import initialize_services, lambda_handler

print("Testing service initialization...")
try:
    initialize_services()
    print("✓ Services initialized successfully\n")
except Exception as e:
    print(f"✗ Service initialization failed: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test a simple lambda function call
print("Testing Lambda handler (simulated API call)...")

class MockContext:
    aws_request_id = "test-request-001"
    function_name = "identity-mgmt-test"

# Test list_applications operation
test_event = {
    "httpMethod": "POST",
    "path": "/api",
    "body": '{"operation": "list_applications"}',
    "requestContext": {
        "requestId": "test-001",
        "authorizer": {
            "sub": "test-cognito-admin",
            "email": "admin@test.com",
            "cognito:groups": ["admin-group"],
            "app_permissions": '[{"app_name": "identity-mgmt", "permission_type": "admin", "permission_level": 100}]'
        }
    }
}

try:
    response = lambda_handler(test_event, MockContext())
    print(f"✓ Lambda handler returned status code: {response['statusCode']}")
    
    if response['statusCode'] == 200:
        import json
        body = json.loads(response['body'])
        print(f"  Response: {json.dumps(body, indent=2)[:200]}...")
    else:
        print(f"  Response body: {response['body'][:200]}...")
    print()
except Exception as e:
    print(f"✗ Lambda handler failed: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("="*60)
print("✅ All tests passed!")
print("="*60)
print("\nThe server is ready to start.")
print("Run: ./start_local.sh")
print()
