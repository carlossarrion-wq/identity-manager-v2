# Identity Manager v2 - Local Development Guide

## ✅ Setup Complete

The local development environment has been successfully configured with:
- ✅ SQLite database with test data
- ✅ Python virtual environment with all dependencies
- ✅ Database service patched for SQLite support
- ✅ Cognito service mocked for local testing
- ✅ FastAPI wrapper for Lambda function
- ✅ Test user seeded: `admin@test.com`

## Quick Start

```bash
cd /repos/identity-manager-v2/backend
source venv/bin/activate

# Set environment variables
export DB_TYPE=sqlite
export DB_PATH=$(pwd)/identity_manager.db
export ENVIRONMENT=local-development
export JWT_SECRET_KEY=local-dev-secret-key
export COGNITO_USER_POOL_ID=local-dev-pool
export COGNITO_REGION=eu-west-1
export AWS_REGION=eu-west-1
export PORT=9999

# Start the server
python3 local_server.py
```

## Available Endpoints

### Health Check
```bash
GET http://localhost:9999/health
```

### Root / Service Info
```bash
GET http://localhost:9999/
```

### Mock Login (Local Development Only)
```bash
POST http://localhost:9999/api/login
Content-Type: application/json

{
  "email": "admin@test.com"
}
```

### API Operations
```bash
POST http://localhost:9999/api
Content-Type: application/json

{
  "operation": "list_applications"
}
```

## Test Credentials

- **Email:** `admin@test.com`
- **Cognito User ID:** `test-cognito-admin`
- **Group:** `admin-group`
- **Permission Level:** 100 (admin)

## Available Operations

The Lambda function supports these operations (requires authenticated context):

### Read Operations (Level 10)
- `list_users` - List all users
- `list_tokens` - List JWT tokens
- `list_profiles` - List inference profiles
- `list_applications` - List applications
- `list_groups` - List Cognito groups
- `list_modules` - List application modules
- `get_user_permissions` - Get user permissions
- `get_config` - Get system configuration

### Write Operations (Level 50)
- `create_user` - Create new user
- `create_token` - Create JWT token
- `revoke_token` - Revoke token
- `assign_app_permission` - Assign app permission
- `assign_module_permission` - Assign module permission

### Admin Operations (Level 100)
- `delete_user` - Delete user
- `delete_token` - Delete token
- `reset_password` - Reset user password
- `block_user` - Block user access

## Database

**Location:** `/repos/identity-manager-v2/backend/identity_manager.db`

**Tables:**
- `identity-manager-users-tbl` - Users
- `identity-manager-tokens-tbl` - JWT tokens
- `identity-manager-applications-tbl` - Applications
- `identity-manager-models-tbl` - LLM models
- `identity-manager-profiles-tbl` - Inference profiles
- `identity-manager-config-tbl` - System configuration
- `identity-manager-modules-tbl` - Application modules
- `identity-manager-permission-types-tbl` - Permission types
- `identity-manager-module-permissions-tbl` - Module permissions

## Architecture Notes

This is an AWS Lambda-based application. The local development setup provides:

1. **SQLite Database** - Replaces PostgreSQL RDS for local testing
2. **Mocked Cognito** - Returns test data instead of calling AWS
3. **FastAPI Wrapper** - Wraps Lambda function for local HTTP access
4. **Local Mode Detection** - Services detect `ENVIRONMENT=local-development` and adjust behavior

### Production vs. Local

| Component | Production | Local Development |
|-----------|-----------|------------------|
| Database | PostgreSQL RDS | SQLite |
| Auth | AWS Cognito | Mocked responses |
| API | API Gateway + Lambda | FastAPI + Lambda function |
| Secrets | AWS Secrets Manager | Environment variables |

## Testing

### Verify Database
```bash
python3 test_basic.py
```

### Test Lambda Handler
```bash
python3 test_imports.py
```

## Troubleshooting

### Port Already in Use
If port 9999 is in use, change the `PORT` environment variable:
```bash
export PORT=8888  # or any available port
```

### Database Not Found
Reinitialize the database:
```bash
python3 init_minimal_db.py
```

### Import Errors
Ensure virtual environment is activated and dependencies installed:
```bash
source venv/bin/activate
pip install -r requirements-local.txt
```

## Files Modified for Local Development

1. `services/database_service.py` - Added SQLite support
2. `services/cognito_service.py` - Added mock responses for local mode

Both files remain **backward-compatible** with production deployment and automatically detect local vs. AWS mode.

## Production Deployment

For production deployment to AWS Lambda, use the original files without modification. The local development patches are conditional and only activate when environment variables indicate local mode (`ENVIRONMENT=local-development` or `DB_TYPE=sqlite`).

## Support

For issues or questions about:
- **Production deployment:** See `/repos/identity-manager-v2/README.md`
- **Database schema:** See `/repos/identity-manager-v2/database/README.md`
- **API operations:** See `/repos/identity-manager-v2/docs/04-API-REFERENCE.md`
