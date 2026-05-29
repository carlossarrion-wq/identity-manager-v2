# List Users Performance Analysis & Optimization

## Issue Description

**Problem:** The `list_users` operation is experiencing timeouts when there are 215+ users in the system.

**Date Identified:** May 29, 2026

## Root Cause Analysis

### Current Implementation Issues

#### 1. **N+1 Query Problem in `list_users()`**
Located in `backend/shared/services/cognito_service.py` (lines 27-96):

```python
def list_users(self, group=None, status=None, limit=60, pagination_token=None):
    # ... fetch users from Cognito ...
    
    for user_data in users_data:
        user = self._format_user(user_data)
        
        # ❌ PROBLEM: Makes 1 API call per user to get groups
        user['groups'] = self._get_user_groups(user['user_id'])
        
        users.append(user)
```

**Impact with 215 users:**
- 1 API call to list users
- **215 additional API calls** to get groups for each user
- **Total: 216 API calls** → Causes timeout

#### 2. **No Effective Pagination**
- The `limit` parameter is set to 60 by default
- But the code processes ALL users before returning
- Pagination token is returned but not effectively used

#### 3. **Unnecessary Data Fetching**
- Fetches all user attributes even when only basic info is needed
- Groups are fetched for every user, even if not displayed

## Performance Metrics

### Current Performance (215 users)
- **API Calls**: 216 (1 list + 215 group lookups)
- **Estimated Time**: 10-15 seconds (assuming 50-70ms per call)
- **Lambda Timeout**: 30 seconds
- **Risk**: High timeout risk with more users

### Expected Performance After Optimization
- **API Calls**: 1-3 (depending on pagination)
- **Estimated Time**: 1-2 seconds
- **Scalability**: Can handle 1000+ users

## Solutions

### Solution 1: Use `list_users_light()` (Already Implemented! ✅)

The codebase already has an optimized version called `list_users_light()` that **doesn't fetch groups**:

**Location:** `backend/shared/services/cognito_service.py` (lines 307-400)

```python
def list_users_light(self, group=None, status=None, limit=None, pagination_token=None):
    """
    Listar usuarios de Cognito (versión LIGERA y RÁPIDA)
    
    Solo devuelve: user_id, email, person, status
    NO obtiene grupos (elimina N llamadas adicionales a Cognito)
    """
    # ... fetch users ...
    
    for user_data in users_data:
        user = self._format_user(user_data)
        # ✅ NO fetches groups - much faster!
        users.append(user)
```

**Benefits:**
- ✅ No N+1 problem
- ✅ Single API call
- ✅ 10-15x faster
- ✅ Already implemented and tested

### Solution 2: Implement True Pagination

Modify the frontend to use pagination properly:

```javascript
// Current: Fetches all users at once
const data = await api.listUsers();

// Optimized: Fetch page by page
const data = await api.listUsers({
    pagination: {
        limit: 50,
        pagination_token: currentToken
    }
});
```

### Solution 3: Lazy Load Groups (If Needed)

Only fetch groups when user details are viewed:

```python
def list_users_with_lazy_groups(self, ...):
    users = []
    for user_data in users_data:
        user = self._format_user(user_data)
        user['groups'] = None  # Don't fetch initially
        user['groups_loaded'] = False
        users.append(user)
    return users
```

## Recommended Implementation Plan

### Phase 1: Quick Fix (Immediate) ⚡
**Use `list_users_light()` in the dashboard**

1. Update frontend to call `list_users_light` instead of `list_users`
2. Only fetch groups when viewing user details
3. **Impact**: Immediate 10-15x performance improvement

**Changes needed:**
- `frontend/dashboard/js/dashboard.js` (line ~163)
- Change `api.listUsers()` to `api.listUsersLight()`

### Phase 2: Proper Pagination (Short-term) 📄
**Implement server-side pagination**

1. Modify backend to enforce pagination limits
2. Update frontend to handle pagination properly
3. Add "Load More" or page navigation UI

### Phase 3: Optimize Group Fetching (Medium-term) 🔄
**Batch group fetching or caching**

1. Implement group caching in Lambda
2. Use batch API calls where possible
3. Consider storing groups in database for faster access

## Code Changes Required

### 1. Frontend Change (Quick Fix)

**File:** `frontend/dashboard/js/dashboard.js`

```javascript
// BEFORE (line ~163)
async function loadUsers() {
    try {
        const data = await api.listUsers();  // ❌ Slow
        dashboardState.users = data.users || [];
        // ...
    }
}

// AFTER
async function loadUsers() {
    try {
        const data = await api.listUsersLight();  // ✅ Fast
        dashboardState.users = data.users || [];
        // ...
    }
}
```

### 2. API Module Update

**File:** `frontend/dashboard/js/api.js`

Ensure `listUsersLight()` method exists:

```javascript
async listUsersLight(filters = {}, pagination = {}) {
    return this.request('list_users_light', {
        filters,
        pagination
    });
}
```

### 3. Backend Handler (Already Exists)

**File:** `backend/lambdas/identity-mgmt-api/lambda_function.py` (lines 345-368)

```python
def handle_list_users_light(body: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """
    Listar usuarios de Cognito (versión LIGERA y RÁPIDA)
    
    Solo devuelve: user_id, email, person, status
    NO obtiene grupos (elimina N llamadas adicionales a Cognito)
    """
    # Already implemented! ✅
```

## Testing Plan

### Performance Testing

1. **Baseline Test** (Current implementation)
   ```bash
   time curl -X POST https://api-endpoint/users \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"operation":"list_users"}'
   ```

2. **Optimized Test** (list_users_light)
   ```bash
   time curl -X POST https://api-endpoint/users \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"operation":"list_users_light"}'
   ```

3. **Load Test** (with 500+ users)
   - Use Apache Bench or similar tool
   - Measure response times
   - Check for timeouts

### Functional Testing

1. Verify user list displays correctly
2. Verify search/filter still works
3. Verify pagination works
4. Verify user details can be viewed (with groups)

## Expected Results

### Before Optimization
- **Response Time**: 10-15 seconds (215 users)
- **API Calls**: 216
- **Timeout Risk**: High
- **Scalability**: Poor (fails at ~300 users)

### After Optimization (Phase 1)
- **Response Time**: 0.5-1 second (215 users)
- **API Calls**: 1
- **Timeout Risk**: None
- **Scalability**: Excellent (can handle 1000+ users)

### After Full Optimization (Phase 2+3)
- **Response Time**: 0.3-0.5 seconds
- **API Calls**: 1-2 (with pagination)
- **Timeout Risk**: None
- **Scalability**: Excellent (can handle 10,000+ users)

## Monitoring

### CloudWatch Metrics to Track
- Lambda execution duration
- API Gateway latency
- Cognito API call count
- Error rate

### Alerts to Set Up
- Lambda duration > 5 seconds
- Error rate > 1%
- Timeout count > 0

## Related Documentation

- [List Users Light Implementation](./14-LIST-USERS-LIGHT.md)
- [API Reference](./04-API-REFERENCE.md)
- [Performance Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)

## Version History

- **v1.0** (2026-05-29): Initial analysis and recommendations