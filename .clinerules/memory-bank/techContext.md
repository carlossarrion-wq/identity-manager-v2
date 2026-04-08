# Technical Context: Identity Manager v2

## Technologies Used

### Backend Technologies

#### Python 3.x
- **Version**: Python 3.9+ (Lambda runtime)
- **Purpose**: Primary backend language
- **Key Libraries**:
  - `boto3`: AWS SDK for Python
  - `psycopg2`: PostgreSQL database adapter
  - `PyJWT`: JWT token handling
  - `python-dateutil`: Date/time utilities

#### AWS Lambda
- **Runtime**: Python 3.9
- **Memory**: 512MB - 1024MB (varies by function)
- **Timeout**: 30 seconds (API), 300 seconds (background tasks)
- **Concurrency**: Provisioned for critical functions
- **VPC**: Enabled for database access

#### AWS RDS PostgreSQL
- **Version**: PostgreSQL 14.x
- **Instance**: db.t3.medium (adjustable per environment)
- **Storage**: 100GB GP3 with autoscaling
- **Backup**: Automated daily backups, 7-day retention
- **Multi-AZ**: Enabled in production

#### AWS Cognito
- **Purpose**: User authentication and management
- **Features Used**:
  - User pools
  - JWT token generation
  - Password policies
  - Email verification
  - MFA support (optional)

### Frontend Technologies

#### Vanilla JavaScript
- **Version**: ES6+
- **Purpose**: Dashboard UI logic
- **No Framework**: Intentional choice for simplicity
- **Key Patterns**:
  - Module pattern for organization
  - Async/await for API calls
  - Event delegation for dynamic content

#### HTML5/CSS3
- **Purpose**: Dashboard structure and styling
- **CSS Framework**: Custom CSS (no Bootstrap/Tailwind)
- **Responsive**: Mobile-first design
- **Browser Support**: Modern browsers (Chrome, Firefox, Safari, Edge)

### Infrastructure Technologies

#### Terraform
- **Version**: 1.5+
- **Purpose**: Infrastructure as Code
- **Structure**:
  - Modules for reusable components
  - Workspaces for environments (dev/pre/pro)
  - Remote state in S3
  - State locking with DynamoDB

#### AWS Services
- **API Gateway**: REST API endpoints
- **CloudFront**: CDN for frontend
- **S3**: Static website hosting, Terraform state
- **Secrets Manager**: Sensitive configuration
- **CloudWatch**: Logging and monitoring
- **VPC**: Network isolation
- **IAM**: Access control

## Development Setup

### Prerequisites
```bash
# Required tools
- Python 3.9+
- Node.js 16+ (for frontend tooling)
- Terraform 1.5+
- AWS CLI v2
- Git
- PostgreSQL client (psql)

# Optional but recommended
- Docker (for local testing)
- jq (JSON processing)
- make (build automation)
```

### Local Development Environment

#### Backend Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
cd backend/lambdas/identity-mgmt-api
pip install -r requirements.txt
pip install -r requirements-dev.txt  # for testing

# Set environment variables
export DB_HOST=localhost
export DB_NAME=identity_manager
export DB_USER=postgres
export DB_PASSWORD=your_password
export COGNITO_USER_POOL_ID=your_pool_id
export COGNITO_CLIENT_ID=your_client_id
```

#### Database Setup
```bash
# Start PostgreSQL (local or Docker)
docker run -d \
  --name postgres-identity \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=identity_manager \
  -p 5432:5432 \
  postgres:14

# Run migrations
psql -h localhost -U postgres -d identity_manager -f database/01_schema.sql
psql -h localhost -U postgres -d identity_manager -f database/02_functions_views.sql
psql -h localhost -U postgres -d identity_manager -f database/03_seed_data.sql
```

#### Frontend Setup
```bash
# No build step required (vanilla JS)
# Simply open frontend/dashboard/index.html in browser
# Or use a local server:
cd frontend/dashboard
python3 -m http.server 8000
# Access at http://localhost:8000
```

### Testing Setup

#### Unit Tests
```bash
cd backend/lambdas/identity-mgmt-api
pytest tests/ -v --cov=. --cov-report=html
```

#### Integration Tests
```bash
# Requires AWS credentials and test environment
export AWS_PROFILE=identity-manager-dev
pytest tests/integration/ -v
```

## Technical Constraints

### AWS Lambda Limitations
- **Execution Time**: Max 15 minutes (using 30s for API functions)
- **Memory**: Max 10GB (using 512MB-1GB)
- **Package Size**: 50MB zipped, 250MB unzipped
- **Concurrent Executions**: Account limit (default 1000)
- **Cold Starts**: 1-3 seconds for Python runtime

### RDS Constraints
- **Connection Limit**: Based on instance size (db.t3.medium ~150 connections)
- **Connection Pooling**: Required for Lambda functions
- **VPC Latency**: Additional 10-50ms for VPC-enabled Lambdas
- **Backup Window**: Daily maintenance window required

### API Gateway Limits
- **Payload Size**: 10MB max
- **Timeout**: 29 seconds max
- **Rate Limiting**: 10,000 requests/second (default)
- **Throttling**: Burst limit 5,000 requests

### Cognito Constraints
- **User Pool Limit**: 40 million users per pool
- **Token Expiry**: Configurable (default 1 hour access, 30 days refresh)
- **Custom Attributes**: Max 50 per user pool
- **API Rate Limits**: 120 requests/second for user operations

## Dependencies

### Backend Dependencies (requirements.txt)
```
boto3==1.42.59          # AWS SDK
psycopg2-binary==2.9.9  # PostgreSQL adapter
PyJWT==2.11.0           # JWT handling
python-dateutil==2.9.0  # Date utilities
pytz==2025.2            # Timezone support
```

### Development Dependencies (requirements-dev.txt)
```
pytest==7.4.3           # Testing framework
pytest-cov==4.1.0       # Coverage reporting
pytest-mock==3.12.0     # Mocking utilities
moto==4.2.9             # AWS service mocking
black==23.12.1          # Code formatting
flake8==6.1.0           # Linting
mypy==1.7.1             # Type checking
```

### Lambda Layers
- **psycopg2**: PostgreSQL driver (binary compiled for Lambda)
- **shared**: Common utilities and services

## Tool Usage Patterns

### AWS CLI
```bash
# Deploy Lambda function
aws lambda update-function-code \
  --function-name identity-mgmt-api \
  --zip-file fileb://function.zip

# Invoke Lambda for testing
aws lambda invoke \
  --function-name identity-mgmt-api \
  --payload '{"httpMethod":"GET","path":"/users"}' \
  response.json

# View logs
aws logs tail /aws/lambda/identity-mgmt-api --follow
```

### Terraform
```bash
# Initialize
terraform init

# Plan changes
terraform plan -var-file=environments/dev/terraform.tfvars

# Apply changes
terraform apply -var-file=environments/dev/terraform.tfvars

# Destroy (careful!)
terraform destroy -var-file=environments/dev/terraform.tfvars
```

### Database Management
```bash
# Connect to RDS
psql -h your-rds-endpoint.amazonaws.com -U admin -d identity_manager

# Run migration
psql -h your-rds-endpoint.amazonaws.com -U admin -d identity_manager \
  -f database/migrations/014_create_cognito_users_cache.sql

# Backup database
pg_dump -h your-rds-endpoint.amazonaws.com -U admin identity_manager > backup.sql

# Restore database
psql -h your-rds-endpoint.amazonaws.com -U admin identity_manager < backup.sql
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_email_case_sensitivity.py -v

# Run with coverage
pytest --cov=. --cov-report=html

# Run integration tests only
pytest tests/integration/ -v -m integration
```

## Environment Configuration

### Environment Variables (Lambda)
```bash
# Database
DB_HOST=your-rds-endpoint.amazonaws.com
DB_NAME=identity_manager
DB_USER=admin
DB_PASSWORD_SECRET_ARN=arn:aws:secretsmanager:...

# Cognito
COGNITO_USER_POOL_ID=us-east-1_xxxxx
COGNITO_CLIENT_ID=xxxxxxxxxxxxx
COGNITO_REGION=us-east-1

# JWT
JWT_SECRET_ARN=arn:aws:secretsmanager:...
JWT_ALGORITHM=HS256

# Email (SES)
SES_REGION=us-east-1
SES_FROM_EMAIL=noreply@example.com

# Application
ENVIRONMENT=dev
LOG_LEVEL=INFO
```

### Terraform Variables
```hcl
# environments/dev/terraform.tfvars
environment = "dev"
vpc_id = "vpc-xxxxx"
subnet_ids = ["subnet-xxxxx", "subnet-yyyyy"]
allowed_cidr_blocks = ["10.0.0.0/8"]
db_instance_class = "db.t3.micro"
db_allocated_storage = 20
```

## Common Development Tasks

### Deploy Lambda Function
```bash
cd backend/lambdas/identity-mgmt-api
./deploy.sh dev  # or pre, pro
```

### Run Database Migration
```bash
cd database/migrations
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f 015_new_migration.sql
```

### Test API Locally
```bash
# Using AWS SAM
sam local start-api

# Or invoke directly
sam local invoke IdentityMgmtApi -e events/test-event.json
```

### View Logs
```bash
# CloudWatch Logs
aws logs tail /aws/lambda/identity-mgmt-dev-api-lmbd --follow

# Or using SAM
sam logs -n IdentityMgmtApi --tail
```

## Troubleshooting

### Common Issues

#### Lambda Cold Starts
- **Symptom**: First request takes 2-3 seconds
- **Solution**: Use provisioned concurrency for critical functions
- **Workaround**: Implement warming strategy with CloudWatch Events

#### Database Connection Timeouts
- **Symptom**: Lambda times out connecting to RDS
- **Solution**: Verify VPC configuration and security groups
- **Check**: Lambda must be in same VPC as RDS

#### JWT Validation Failures
- **Symptom**: Valid tokens rejected
- **Solution**: Verify JWT secret matches between services
- **Check**: Token expiration and clock skew

#### CORS Errors
- **Symptom**: Browser blocks API requests
- **Solution**: Configure CORS in API Gateway
- **Check**: Allowed origins match frontend domain