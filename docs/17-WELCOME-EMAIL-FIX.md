# Welcome Email Fix

## Issue Description

**Problem:** When creating a user through the dashboard, even when the "Send Welcome Email" checkbox was unchecked, the system was still sending welcome emails to new users.

**Date Identified:** May 29, 2026

## Root Cause Analysis

The issue was located in `backend/shared/services/cognito_service.py` in the `create_user` method.

### Original Code (Incorrect)
```python
# Determine MessageAction based on send_welcome_email
if send_welcome_email:
    message_action = 'RESEND'  # This will send the welcome email
# If send_welcome_email is False, we don't set MessageAction, which defaults to sending email
```

### Problem
When `send_welcome_email` was `False`, the code did not set the `MessageAction` parameter at all. According to AWS Cognito's behavior:
- **When `MessageAction` is not specified:** Cognito sends a welcome email by default
- **When `MessageAction='SUPPRESS'`:** Cognito suppresses the welcome email
- **When `MessageAction='RESEND'`:** Cognito sends/resends the welcome email

Therefore, omitting the `MessageAction` parameter when `send_welcome_email=False` resulted in emails being sent anyway.

## Solution

### Fixed Code
```python
# Determine MessageAction based on send_welcome_email
if send_welcome_email:
    message_action = 'RESEND'  # This will send the welcome email
else:
    message_action = 'SUPPRESS'  # This will suppress the welcome email
```

### Changes Made
1. Added explicit `else` clause to handle `send_welcome_email=False` case
2. Set `message_action = 'SUPPRESS'` when welcome email should not be sent
3. This ensures the `MessageAction` parameter is always explicitly set in the Cognito API call

## Files Modified

- `backend/shared/services/cognito_service.py` (lines 119-122)

## Testing Recommendations

### Test Case 1: Create User WITH Welcome Email
1. Navigate to dashboard user creation form
2. Fill in user details
3. **Check** the "Send Welcome Email" checkbox
4. Submit the form
5. **Expected:** User receives welcome email from Cognito

### Test Case 2: Create User WITHOUT Welcome Email
1. Navigate to dashboard user creation form
2. Fill in user details
3. **Uncheck** the "Send Welcome Email" checkbox (or leave it unchecked)
4. Submit the form
5. **Expected:** User does NOT receive welcome email from Cognito

### Test Case 3: API Direct Call
```bash
# Test with send_welcome_email=false
curl -X POST https://your-api-endpoint/users \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "given_name": "Test",
    "family_name": "User",
    "send_welcome_email": false
  }'
```

## AWS Cognito MessageAction Reference

From AWS Cognito AdminCreateUser API documentation:

- **RESEND:** Resend the invitation message to a user that already exists and reset the expiration limit on the user's account
- **SUPPRESS:** Suppress sending the message. Only administrators can create user accounts. The user account will be created but no invitation message will be sent

## Impact Assessment

### Affected Functionality
- User creation via dashboard
- User creation via API endpoint `/users` (POST)
- Any code path that calls `cognito_service.create_user()`

### Backward Compatibility
- **No breaking changes:** The fix only corrects the behavior to match the intended functionality
- **Default behavior preserved:** When `send_welcome_email` parameter is not provided, it defaults to `True` (sending email), which maintains backward compatibility

### Deployment Notes
- This is a bug fix that should be deployed as soon as possible
- No database migrations required
- No frontend changes required
- Lambda function needs to be redeployed with updated code

## Related Documentation

- [AWS Cognito AdminCreateUser API](https://docs.aws.amazon.com/cognito-user-identity-pools/latest/APIReference/API_AdminCreateUser.html)
- [User Management Documentation](./04-API-REFERENCE.md#create-user)

## Version History

- **v1.0** (2026-05-29): Initial fix applied