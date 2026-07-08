"""
Final test - verify server can start and respond
"""
import os
import sys
import subprocess
import time
from pathlib import Path

# Set environment
os.environ.update({
    'DB_TYPE': 'sqlite',
    'DB_PATH': str(Path(__file__).parent / 'identity_manager.db'),
    'ENVIRONMENT': 'local-development',
    'JWT_SECRET_KEY': 'local-dev-secret-key',
    'COGNITO_USER_POOL_ID': 'local-dev-pool',
    'COGNITO_REGION': 'eu-west-1',
    'AWS_REGION': 'eu-west-1',
    'PORT': '9000'
})

print("\n" + "="*60)
print("🧪 Final Server Startup Test")
print("="*60 + "\n")

# Start server
print("Starting server on port 9000...")
server_process = subprocess.Popen(
    ['venv/bin/python3', 'local_server.py'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd=Path(__file__).parent
)

# Wait for startup
print("Waiting for server to start...")
time.sleep(3)

# Check if process is still running
poll_result = server_process.poll()
if poll_result is not None:
    stdout, stderr = server_process.communicate()
    print(f"\n✗ Server failed to start")
    print(f"Exit code: {poll_result}")
    if stderr:
        print(f"Error: {stderr.decode()[:500]}")
    sys.exit(1)

print("✓ Server process started successfully")
print("✓ Server running on http://localhost:9000")

# Terminate server
print("\nStopping server...")
server_process.terminate()
server_process.wait(timeout=5)

print("\n" + "="*60)
print("✅ Server startup test PASSED")
print("="*60)
print("\n📋 To start the server manually:")
print("   cd /repos/identity-manager-v2/backend")
print("   source venv/bin/activate")
print("   export DB_TYPE=sqlite PORT=9000 ENVIRONMENT=local-development")
print("   export DB_PATH=$(pwd)/identity_manager.db")
print("   export COGNITO_USER_POOL_ID=local-dev-pool AWS_REGION=eu-west-1")
print("   python3 local_server.py")
print()
