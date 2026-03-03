# Migration 010: Add Person Field to Proxy Tables

## Overview

This migration adds the `person` field from JWT tokens to the bedrock-proxy database tables. This field complements the existing `team` field and provides better user identification and analytics.

## Date
2026-03-03

## Motivation

The JWT token contains a `person` field with the user's full name (e.g., "Carlos Sarrión"). This information is valuable for:

1. **Better User Identification**: Display human-readable names instead of just emails
2. **Enhanced Analytics**: Track usage by person name
3. **Improved Reporting**: Generate reports with actual person names
4. **Audit Trail**: Better tracking of who is using the system

## JWT Token Structure

The JWT token contains the following relevant fields:

```json
{
  "user_id": "1285a444-d011-7063-0d76-ffeb254d0e69",
  "email": "carlos.sarrion@es.ibm.com",
  "person": "Carlos Sarrión",
  "team": "lcs-sdlc-gen-group",
  "default_inference_profile": "dc1b3985-78df-4ef6-804a-2cfb50f7dee3"
}
```

## Database Changes

### Tables Modified

#### 1. `bedrock-proxy-usage-tracking-tbl`
- **New Column**: `person VARCHAR(255)`
- **Purpose**: Store person name for each request
- **Index**: `idx_usage_person` for query performance

#### 2. `bedrock-proxy-user-quotas-tbl`
- **New Column**: `person VARCHAR(255)`
- **Purpose**: Associate person name with quota records
- **Index**: `idx_quotas_person` for query performance

#### 3. `bedrock-proxy-quota-blocks-history-tbl`
- **New Column**: `person VARCHAR(255)`
- **Purpose**: Track person name in quota block history
- **Index**: `idx_quota_history_person` for query performance

### Views Updated

#### 1. `v_usage_detailed`
Updated to include `person` field in the SELECT clause:
```sql
SELECT 
    id, cognito_user_id, cognito_email, person, team, request_timestamp,
    model_id, source_ip, user_agent, aws_region,
    tokens_input, tokens_output, tokens_cache_read, tokens_cache_creation,
    cost_usd, processing_time_ms, response_status, error_message, created_at
FROM "bedrock-proxy-usage-tracking-tbl"
ORDER BY request_timestamp DESC;
```

#### 2. `v_recent_errors`
Updated to include `person` field:
```sql
SELECT 
    id, cognito_user_id, cognito_email, person, team, request_timestamp,
    model_id, response_status, error_message, created_at
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE response_status != 'success'
ORDER BY request_timestamp DESC
LIMIT 100;
```

#### 3. `v_usage_by_team`
Updated to include person count:
```sql
SELECT 
    team,
    COUNT(*) as request_count,
    COUNT(DISTINCT cognito_user_id) as unique_users,
    COUNT(DISTINCT person) as unique_persons,  -- NEW
    SUM(tokens_input) as total_tokens_input,
    ...
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE team IS NOT NULL
GROUP BY team
ORDER BY request_count DESC;
```

### New Views

#### `v_usage_by_person`
New view for aggregated usage statistics by person:
```sql
CREATE VIEW v_usage_by_person AS
SELECT 
    person,
    cognito_email,
    team,
    COUNT(*) as request_count,
    SUM(tokens_input) as total_tokens_input,
    SUM(tokens_output) as total_tokens_output,
    SUM(tokens_cache_read) as total_tokens_cache_read,
    SUM(tokens_cache_creation) as total_tokens_cache_creation,
    SUM(cost_usd) as total_cost_usd,
    AVG(processing_time_ms) as avg_processing_time_ms,
    MIN(request_timestamp) as first_request,
    MAX(request_timestamp) as last_request
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE person IS NOT NULL
GROUP BY person, cognito_email, team
ORDER BY request_count DESC;
```

### Functions Updated

#### `check_and_update_quota()`

**Old Signature:**
```sql
check_and_update_quota(
    p_cognito_user_id VARCHAR(255),
    p_cognito_email VARCHAR(255),
    p_team VARCHAR(100) DEFAULT NULL
)
```

**New Signature:**
```sql
check_and_update_quota(
    p_cognito_user_id VARCHAR(255),
    p_cognito_email VARCHAR(255),
    p_team VARCHAR(100) DEFAULT NULL,
    p_person VARCHAR(255) DEFAULT NULL  -- NEW PARAMETER
)
```

**Changes:**
- Added `p_person` parameter (optional, defaults to NULL)
- Updates `person` field in INSERT and UPDATE operations
- Includes `person` in quota block history records

## Application Changes Required

### 1. Go Code (proxy-bedrock)

#### Extract Person from JWT
Update JWT parsing to extract the `person` field:

```go
// In pkg/auth/jwt.go or similar
type JWTClaims struct {
    UserID                  string   `json:"user_id"`
    Email                   string   `json:"email"`
    Person                  string   `json:"person"`  // NEW
    Team                    string   `json:"team"`
    DefaultInferenceProfile string   `json:"default_inference_profile"`
    // ... other fields
}
```

#### Update Usage Tracking
Modify usage tracking to include person:

```go
// In pkg/auth/usage_tracking.go
func TrackUsage(ctx context.Context, db *sql.DB, claims *JWTClaims, ...) error {
    query := `
        INSERT INTO "bedrock-proxy-usage-tracking-tbl" (
            cognito_user_id, cognito_email, person, team,  -- Added person
            request_timestamp, model_id, ...
        ) VALUES ($1, $2, $3, $4, $5, $6, ...)
    `
    _, err := db.ExecContext(ctx, query,
        claims.UserID,
        claims.Email,
        claims.Person,  // NEW
        claims.Team,
        // ... other parameters
    )
    return err
}
```

#### Update Quota Checks
Modify quota check calls to include person:

```go
// In pkg/quota/middleware.go
func CheckQuota(ctx context.Context, db *sql.DB, claims *JWTClaims) (*QuotaResult, error) {
    query := `
        SELECT * FROM check_and_update_quota($1, $2, $3, $4)
    `
    var result QuotaResult
    err := db.QueryRowContext(ctx, query,
        claims.UserID,
        claims.Email,
        claims.Team,
        claims.Person,  // NEW
    ).Scan(&result.Allowed, &result.RequestsToday, ...)
    
    return &result, err
}
```

### 2. Backend API (identity-mgmt-api)

#### Update Proxy Usage Queries
Modify queries to include `person` field:

```python
# In backend/lambdas/identity-mgmt-api/services/database_service.py

def get_proxy_usage_by_user(filters):
    query = """
        SELECT 
            cognito_email as email,
            person,  -- NEW
            team,
            COUNT(*) as requests,
            SUM(tokens_input + tokens_output) as tokens,
            SUM(cost_usd) as cost
        FROM "bedrock-proxy-usage-tracking-tbl"
        WHERE request_timestamp BETWEEN %s AND %s
        GROUP BY cognito_email, person, team  -- Added person
        ORDER BY requests DESC
    """
    # ... execute query
```

### 3. Frontend Dashboard

The frontend already displays the `person` field in the Usage by User table, so no changes are needed there.

## Migration Steps

### 1. Apply Database Migration

```bash
# Set environment variables
export DB_HOST=your-db-host
export DB_NAME=your-db-name
export DB_USER=your-db-user
export DB_PASSWORD=your-db-password

# Run migration script
chmod +x scripts/apply_migration_010.sh
./scripts/apply_migration_010.sh
```

### 2. Update Go Code

1. Update JWT claims structure to include `person`
2. Update usage tracking to insert `person` field
3. Update quota check calls to pass `person` parameter
4. Test changes locally

### 3. Deploy Changes

1. Build and test proxy-bedrock with new changes
2. Deploy to development environment
3. Verify person field is being populated
4. Deploy to production

## Verification

### Check Person Field Population

```sql
-- Check if person field is being populated
SELECT 
    cognito_email,
    person,
    team,
    COUNT(*) as request_count
FROM "bedrock-proxy-usage-tracking-tbl"
WHERE request_timestamp > CURRENT_DATE
GROUP BY cognito_email, person, team
ORDER BY request_count DESC
LIMIT 10;
```

### Test New View

```sql
-- Test v_usage_by_person view
SELECT * FROM v_usage_by_person
LIMIT 10;
```

### Verify Quota Function

```sql
-- Test quota function with person parameter
SELECT * FROM check_and_update_quota(
    'test-user-id',
    'test@example.com',
    'test-team',
    'Test Person'
);
```

## Rollback Plan

If issues arise, the migration can be rolled back:

```sql
-- Remove person column from tables
ALTER TABLE "bedrock-proxy-usage-tracking-tbl" DROP COLUMN person;
ALTER TABLE "bedrock-proxy-user-quotas-tbl" DROP COLUMN person;
ALTER TABLE "bedrock-proxy-quota-blocks-history-tbl" DROP COLUMN person;

-- Drop indexes
DROP INDEX IF EXISTS idx_usage_person;
DROP INDEX IF EXISTS idx_quotas_person;
DROP INDEX IF EXISTS idx_quota_history_person;

-- Drop new view
DROP VIEW IF EXISTS v_usage_by_person;

-- Restore previous function signature
-- (Re-run migration 009 function definition)
```

## Benefits

1. **Better User Identification**: Display "Carlos Sarrión" instead of just "carlos.sarrion@es.ibm.com"
2. **Enhanced Analytics**: Track usage by person name for better insights
3. **Improved Reporting**: Generate reports with actual person names
4. **Consistent with Team Field**: Follows the same pattern as the team field migration
5. **Backward Compatible**: Person field is optional (NULL allowed)

## Notes

- The `person` field is optional and defaults to NULL
- Existing records will have NULL for person until updated
- The field will be populated automatically for new requests once Go code is updated
- No data loss occurs during migration
- All existing functionality continues to work

## Related Documents

- [Migration 009: Add Team Field](./TEAM_FIELD_MIGRATION.md)
- [Proxy Bedrock Integration](./PROXY_BEDROCK_INTEGRATION.md)
- [Usage Tracking](./USAGE_TRACKING.md)