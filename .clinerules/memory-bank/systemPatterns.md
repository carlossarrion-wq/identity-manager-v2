# System Patterns: Identity Manager v2

## System Architecture

### High-Level Architecture
```
┌─────────────┐
│   Browser   │
│  Dashboard  │
└──────┬──────┘
       │ HTTPS
       ▼
┌─────────────────┐
│   CloudFront    │
│   + S3 Static   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│  API Gateway    │◄────►│   Cognito    │
│  (REST API)     │      │  User Pool   │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐
│ Lambda          │
│ Authorizer      │
│ (JWT Validator) │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│         Lambda Functions            │
│  ┌──────────────────────────────┐  │
│  │  identity-mgmt-api           │  │
│  │  - User CRUD                 │  │
│  │  - Permission Management     │  │
│  │  - Usage Queries             │  │
│  └──────────────────────────────┘  │
│  ┌──────────────────────────────┐  │
│  │  proxy-bedrock               │  │
│  │  - Request Forwarding        │  │
│  │  - Usage Tracking            │  │
│  │  - Quota Enforcement         │  │
│  └──────────────────────────────┘  │
└──────────────┬──────────────────────┘
               │
               ▼
        ┌──────────────┐
        │  RDS Postgres│
        │  - Users     │
        │  - Roles     │
        │  - Permissions│
        │  - Usage Logs│
        └──────────────┘
```

### Component Relationships

#### Frontend → Backend
- **Protocol**: HTTPS REST API
- **Authentication**: JWT Bearer tokens
- **Data Format**: JSON
- **CORS**: Configured for specific origins

#### API Gateway → Lambda
- **Integration**: Lambda Proxy Integration
- **Authorization**: Custom Lambda Authorizer
- **Request Transformation**: None (proxy passes through)
- **Response Transformation**: None (proxy passes through)

#### Lambda → RDS
- **Connection**: psycopg2 with connection pooling
- **Authentication**: IAM + Secrets Manager
- **Network**: VPC with private subnets
- **Security Groups**: Restricted to Lambda security group

#### Lambda → Cognito
- **SDK**: boto3 cognito-idp client
- **Operations**: User management, token validation
- **Authentication**: IAM role-based

## Key Technical Decisions

### Decision: Lambda Authorizer Pattern
**Context**: Need to validate JWT tokens and enforce permissions
**Decision**: Use custom Lambda authorizer instead of Cognito authorizer
**Rationale**: 
- Support both Cognito and external app tokens
- Embed permissions in authorization context
- Reduce database calls in main Lambda functions
**Trade-offs**: Additional Lambda invocation, but better separation of concerns

### Decision: Shared Code via Lambda Layers
**Context**: Multiple Lambda functions need common utilities
**Decision**: Use Lambda layers for shared dependencies, direct imports for shared code
**Rationale**:
- Layers for binary dependencies (psycopg2)
- Direct imports for Python code (easier development)
- Reduces deployment package size
**Trade-offs**: Slightly more complex deployment, but better code reuse

### Decision: JWT Permission Embedding
**Context**: Need to check permissions on every API request
**Decision**: Embed permissions in JWT claims during token generation
**Rationale**:
- Reduces database queries
- Faster authorization checks
- Permissions cached until token expiry
**Trade-offs**: Permissions not updated until token refresh

### Decision: Email Case-Insensitive Lookups
**Context**: Users experiencing login issues due to email case variations
**Decision**: Use LOWER() function in all email comparison queries
**Rationale**:
- Email addresses are case-insensitive per RFC 5321
- Prevents duplicate users with different cases
- Improves user experience
**Trade-offs**: Slight performance impact, but negligible with proper indexing

### Decision: Monorepo Structure
**Context**: Multiple related components (frontend, backend, infrastructure)
**Decision**: Single repository with organized subdirectories
**Rationale**:
- Easier to maintain consistency
- Simplified CI/CD
- Better visibility of cross-component changes
**Trade-offs**: Larger repository, but better organization

## Design Patterns in Use

### Service Layer Pattern
**Location**: `backend/shared/services/`
**Purpose**: Encapsulate business logic separate from Lambda handlers
**Example**:
```python
# services/database_service.py
class DatabaseService:
    def get_user_by_email(self, email):
        # Business logic here
        pass
```

### Repository Pattern
**Location**: Database access in service classes
**Purpose**: Abstract database operations
**Benefits**: Easier testing, database independence

### Decorator Pattern
**Location**: `backend/shared/ams_logging/decorators.py`
**Purpose**: Cross-cutting concerns (logging, error handling)
**Example**:
```python
@log_execution_time
@handle_exceptions
def lambda_handler(event, context):
    # Handler logic
    pass
```

### Builder Pattern
**Location**: `backend/shared/utils/response_builder.py`
**Purpose**: Construct standardized API responses
**Example**:
```python
ResponseBuilder.success(data, status_code=200)
ResponseBuilder.error(message, status_code=400)
```

### Factory Pattern
**Location**: Service initialization in Lambda handlers
**Purpose**: Create service instances with proper configuration
**Example**:
```python
def get_database_service():
    return DatabaseService(
        host=os.environ['DB_HOST'],
        database=os.environ['DB_NAME']
    )
```

## Critical Implementation Paths

### User Authentication Flow
1. User submits credentials to Cognito
2. Cognito validates and returns JWT tokens
3. Frontend stores tokens in localStorage
4. Subsequent requests include JWT in Authorization header
5. API Gateway invokes Lambda authorizer
6. Authorizer validates JWT and extracts permissions
7. Main Lambda function receives authorization context
8. Function executes with permission context

### User Creation Flow
1. Admin submits user creation request
2. Lambda validates input data
3. Creates user in Cognito user pool
4. Inserts user record in RDS database
5. Assigns default role and permissions
6. Returns user details to admin
7. Cognito sends welcome email to user

### Usage Tracking Flow
1. User makes request to Bedrock proxy
2. Proxy validates JWT and permissions
3. Checks user quota availability
4. Forwards request to AWS Bedrock
5. Receives response from Bedrock
6. Extracts usage metadata (tokens, model)
7. Calculates cost based on model pricing
8. Records usage in database
9. Updates user quota counters
10. Returns response to user

### Permission Check Flow
1. Request arrives with JWT token
2. Lambda authorizer extracts permissions from JWT
3. Passes permissions in authorization context
4. Main Lambda receives permission list
5. Checks required permission for operation
6. Proceeds if authorized, returns 403 if not

## Data Flow Patterns

### Request/Response Pattern
- All API endpoints follow consistent request/response structure
- Request: JSON body with required/optional fields
- Response: JSON with `success`, `data`, `message`, `error` fields

### Event-Driven Pattern
- Lambda functions triggered by API Gateway events
- Asynchronous processing for non-critical operations
- CloudWatch Events for scheduled tasks

### Caching Pattern
- JWT permissions cached until token expiry
- Cognito user pool data cached in RDS
- CloudFront caching for static assets

## Security Patterns

### Defense in Depth
- Multiple layers of security (API Gateway, Lambda Authorizer, IAM)
- Network isolation via VPC
- Encryption at rest and in transit

### Principle of Least Privilege
- IAM roles with minimal required permissions
- Database users with restricted access
- API permissions granularly defined

### Secure by Default
- All endpoints require authentication
- HTTPS enforced
- Secrets in AWS Secrets Manager
- No hardcoded credentials