# Team Field "Unknown" Issue Analysis

## Problem Statement
Many records in the `bedrock-proxy-usage-tracking-tbl` table have the team field populated as "unknown" instead of the actual team value. This analysis investigates the root cause and proposes solutions.

## Investigation Findings

### 1. Data Flow Analysis

#### How Team Information Should Flow:
1. **User Creation**: When a user is created in Cognito, custom attributes `custom:team` and `custom:person` are set
2. **JWT Token Generation**: When generating JWT tokens, these custom attributes are included in the token claims
3. **Proxy Request**: When the proxy-bedrock service receives a request, it extracts team information from the JWT token
4. **Usage Tracking**: The team value is stored in the database usage tracking table

### 2. Code Review Findings

#### A. JWT Token Generation (backend/shared/services/jwt_service.py)
The JWT service includes team information in tokens:
```python
# From jwt_service.py
claims = {
    'sub': user_id,
    'email': email,
    'person': person,
    'team': team,
    # ... other claims
}
```

#### B. Proxy Bedrock JWT Parsing (proxy-bedrock/pkg/auth/jwt.go)
The proxy extracts team from JWT claims:
```go
// From jwt.go
team, _ := claims["team"].(string)
if team == "" {
    team = "unknown"
}
```

**ROOT CAUSE #1**: The code defaults to "unknown" when the team claim is empty or missing.

#### C. Usage Tracking (proxy-bedrock/pkg/tracking/tracker.go)
The tracker receives team from the JWT context:
```go
// From tracker.go
team := r.Context().Value("team").(string)
```

### 3. Root Causes Identified

#### Primary Causes:

1. **Missing Custom Attributes in Cognito**
   - Some users may have been created without the `custom:team` attribute set
   - Legacy users created before the custom attribute was implemented
   - Users created through different processes that don't set custom attributes

2. **Empty Team Values**
   - Users with `custom:team` set to empty string or null
   - The proxy code treats empty strings as "unknown"

3. **Token Generation Issues**
   - If a user's Cognito profile doesn't have `custom:team`, the JWT won't include it
   - External app tokens may not include team information

4. **Cognito User Pool Configuration**
   - Custom attributes must be defined in the Cognito User Pool
   - If `custom:team` wasn't configured initially, older users won't have it

### 4. Evidence from Code

#### User Creation Flow (backend/lambdas/identity-mgmt-api/lambda_function.py)
```python
# When creating users, custom attributes should be set:
user_attributes = [
    {'Name': 'email', 'Value': email},
    {'Name': 'custom:person', 'Value': person},
    {'Name': 'custom:team', 'Value': team}
]
```

**ISSUE**: If `team` parameter is not provided or is empty during user creation, the custom attribute will be empty.

#### JWT Service (backend/shared/services/jwt_service.py)
```python
# Team is extracted from user data
team = user_data.get('team', 'unknown')
```

**ISSUE**: If user_data doesn't contain 'team', it defaults to 'unknown' at JWT generation time.

### 5. Verification Steps

To verify which users have missing team information:

```sql
-- Check users in database without team
SELECT user_id, email, team 
FROM users 
WHERE team IS NULL OR team = '' OR team = 'unknown';

-- Check usage tracking records with unknown team
SELECT user_id, COUNT(*) as unknown_count
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE team = 'unknown'
GROUP BY user_id
ORDER BY unknown_count DESC;

-- Cross-reference with Cognito users
-- (Need to query Cognito API to check custom:team attribute)
```

## Solutions

### Immediate Fix (Short-term)

1. **Audit Existing Users**
   - Query all users in Cognito to identify those without `custom:team`
   - Create a script to update missing team values

2. **Backfill Missing Data**
   ```python
   # Script to update users without team
   for user in users_without_team:
       cognito_client.admin_update_user_attributes(
           UserPoolId=user_pool_id,
           Username=user['email'],
           UserAttributes=[
               {'Name': 'custom:team', 'Value': determine_team(user)}
           ]
       )
   ```

3. **Update Existing Tokens**
   - Force token regeneration for affected users
   - Ensure new tokens include correct team information

### Long-term Fix (Recommended)

1. **Enforce Team Attribute at User Creation**
   ```python
   # Make team a required parameter
   def create_user(email, person, team):
       if not team or team.strip() == '':
           raise ValueError("Team is required")
       # ... create user with team
   ```

2. **Add Validation in Proxy**
   ```go
   // In proxy-bedrock/pkg/auth/jwt.go
   team, ok := claims["team"].(string)
   if !ok || team == "" {
       // Log warning and try to fetch from database
       team = fetchTeamFromDatabase(userID)
       if team == "" {
           team = "unknown"
           logger.Warn("User has no team assigned", "user_id", userID)
       }
   }
   ```

3. **Database Fallback**
   - If JWT doesn't have team, query the database
   - Cache team information to avoid repeated queries

4. **Monitoring and Alerts**
   - Add CloudWatch metric for "unknown" team occurrences
   - Alert when threshold is exceeded
   - Dashboard to track team population rate

### Migration Script

```python
#!/usr/bin/env python3
"""
Script to fix users with missing team information
"""
import boto3
import psycopg2

def fix_missing_teams():
    cognito = boto3.client('cognito-idp')
    
    # Get all users from Cognito
    response = cognito.list_users(UserPoolId=USER_POOL_ID)
    
    for user in response['Users']:
        email = next((attr['Value'] for attr in user['Attributes'] 
                     if attr['Name'] == 'email'), None)
        team = next((attr['Value'] for attr in user['Attributes'] 
                    if attr['Name'] == 'custom:team'), None)
        
        if not team or team == '':
            # Determine team from database or other source
            team = determine_team_for_user(email)
            
            # Update Cognito
            cognito.admin_update_user_attributes(
                UserPoolId=USER_POOL_ID,
                Username=email,
                UserAttributes=[
                    {'Name': 'custom:team', 'Value': team}
                ]
            )
            
            print(f"Updated team for {email}: {team}")

def determine_team_for_user(email):
    # Logic to determine team based on email domain, 
    # database records, or manual mapping
    if '@example.com' in email:
        return 'Engineering'
    # Add more logic as needed
    return 'General'

if __name__ == '__main__':
    fix_missing_teams()
```

## Recommendations

### Priority 1 (Immediate)
1. Run audit to identify users without team
2. Create and execute backfill script
3. Add validation to prevent future occurrences

### Priority 2 (Short-term)
1. Implement database fallback in proxy
2. Add monitoring and alerts
3. Update documentation

### Priority 3 (Long-term)
1. Consider making team a required field in UI
2. Add team management interface in dashboard
3. Implement team hierarchy if needed

## Testing Plan

1. **Verify Current State**
   - Count records with "unknown" team
   - Identify affected users

2. **Test Fix**
   - Update test user without team
   - Verify JWT includes team
   - Verify proxy records correct team

3. **Validate Migration**
   - Run migration script on test environment
   - Verify all users have team assigned
   - Check new usage records have correct team

## Monitoring

Add the following metrics:
- `proxy.usage.unknown_team_count` - Count of requests with unknown team
- `proxy.usage.team_population_rate` - Percentage of requests with valid team
- Alert when unknown_team_count > threshold

## Related Files

- `proxy-bedrock/pkg/auth/jwt.go` - JWT parsing and team extraction
- `proxy-bedrock/pkg/tracking/tracker.go` - Usage tracking
- `backend/shared/services/jwt_service.py` - JWT token generation
- `backend/shared/services/cognito_service.py` - Cognito user management
- `backend/lambdas/identity-mgmt-api/lambda_function.py` - User creation/update
- `database/01_schema.sql` - Database schema

## Conclusion

The "unknown" team values are caused by:
1. Users created without `custom:team` attribute in Cognito
2. Empty or missing team values in user profiles
3. No fallback mechanism when team is missing from JWT

The solution requires:
1. Backfilling missing team data in Cognito
2. Adding validation to prevent future occurrences
3. Implementing fallback mechanisms in the proxy
4. Adding monitoring to detect and alert on the issue

---
**Date**: 2026-06-09
**Author**: Cline
**Status**: Analysis Complete - Awaiting Implementation