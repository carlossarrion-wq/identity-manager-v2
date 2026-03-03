-- =====================================================
-- SEED DATA: Usage Tracking Examples
-- =====================================================
-- Purpose: Insert example usage tracking data for testing
-- Version: 1.0
-- Date: 2026-03-02
-- =====================================================

-- Note: This script assumes you have existing data in:
-- - identity-manager-profiles-tbl (for model_id references)
-- - Cognito users (for cognito_user_id and cognito_email)

-- =====================================================
-- EXAMPLE 1: Successful request
-- =====================================================
INSERT INTO "bedrock-proxy-usage-tracking-tbl" (
    cognito_user_id,
    cognito_email,
    request_timestamp,
    model_id,
    source_ip,
    user_agent,
    aws_region,
    tokens_input,
    tokens_output,
    tokens_cache_read,
    tokens_cache_creation,
    cost_usd,
    processing_time_ms,
    response_status,
    error_message
) VALUES (
    'us-east-1_abc123def',
    'user@example.com',
    CURRENT_TIMESTAMP - INTERVAL '1 hour',
    (SELECT id FROM "identity-manager-profiles-tbl" LIMIT 1),
    '192.168.1.100',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
    'us-east-1',
    1500,
    800,
    0,
    0,
    0.034500,
    2345,
    'success',
    NULL
);

-- =====================================================
-- EXAMPLE 2: Request with cache usage
-- =====================================================
INSERT INTO "bedrock-proxy-usage-tracking-tbl" (
    cognito_user_id,
    cognito_email,
    request_timestamp,
    model_id,
    source_ip,
    user_agent,
    aws_region,
    tokens_input,
    tokens_output,
    tokens_cache_read,
    tokens_cache_creation,
    cost_usd,
    processing_time_ms,
    response_status,
    error_message
) VALUES (
    'us-east-1_abc123def',
    'user@example.com',
    CURRENT_TIMESTAMP - INTERVAL '30 minutes',
    (SELECT id FROM "identity-manager-profiles-tbl" LIMIT 1),
    '192.168.1.100',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
    'us-east-1',
    1200,
    600,
    500,
    200,
    0.025800,
    1890,
    'success',
    NULL
);

-- =====================================================
-- EXAMPLE 3: Failed request with error
-- =====================================================
INSERT INTO "bedrock-proxy-usage-tracking-tbl" (
    cognito_user_id,
    cognito_email,
    request_timestamp,
    model_id,
    source_ip,
    user_agent,
    aws_region,
    tokens_input,
    tokens_output,
    tokens_cache_read,
    tokens_cache_creation,
    cost_usd,
    processing_time_ms,
    response_status,
    error_message
) VALUES (
    'us-east-1_xyz789ghi',
    'another.user@example.com',
    CURRENT_TIMESTAMP - INTERVAL '15 minutes',
    (SELECT id FROM "identity-manager-profiles-tbl" LIMIT 1),
    '10.0.1.50',
    'Python/3.11 boto3/1.34.0',
    'us-east-1',
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    567,
    'error',
    'ThrottlingException: Rate exceeded for model invocations'
);

-- =====================================================
-- EXAMPLE 4: Timeout error
-- =====================================================
INSERT INTO "bedrock-proxy-usage-tracking-tbl" (
    cognito_user_id,
    cognito_email,
    request_timestamp,
    model_id,
    source_ip,
    user_agent,
    aws_region,
    tokens_input,
    tokens_output,
    tokens_cache_read,
    tokens_cache_creation,
    cost_usd,
    processing_time_ms,
    response_status,
    error_message
) VALUES (
    'us-east-1_xyz789ghi',
    'another.user@example.com',
    CURRENT_TIMESTAMP - INTERVAL '5 minutes',
    (SELECT id FROM "identity-manager-profiles-tbl" LIMIT 1),
    '10.0.1.50',
    'Python/3.11 boto3/1.34.0',
    'us-west-2',
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    30000,
    'timeout',
    'Request timeout after 30 seconds'
);

-- =====================================================
-- EXAMPLE 5: Large request with high token usage
-- =====================================================
INSERT INTO "bedrock-proxy-usage-tracking-tbl" (
    cognito_user_id,
    cognito_email,
    request_timestamp,
    model_id,
    source_ip,
    user_agent,
    aws_region,
    tokens_input,
    tokens_output,
    tokens_cache_read,
    tokens_cache_creation,
    cost_usd,
    processing_time_ms,
    response_status,
    error_message
) VALUES (
    'us-east-1_abc123def',
    'user@example.com',
    CURRENT_TIMESTAMP - INTERVAL '2 hours',
    (SELECT id FROM "identity-manager-profiles-tbl" LIMIT 1),
    '192.168.1.100',
    'Cline/1.0',
    'us-east-1',
    8500,
    4200,
    0,
    0,
    0.188500,
    8934,
    'success',
    NULL
);

-- =====================================================
-- QUERY EXAMPLES TO VERIFY DATA
-- =====================================================

-- View all inserted records
-- SELECT * FROM "bedrock-proxy-usage-tracking-tbl" ORDER BY request_timestamp DESC;

-- View usage summary by user
-- SELECT * FROM "v_usage_by_user";

-- View usage summary by model
-- SELECT * FROM "v_usage_by_model";

-- View daily usage
-- SELECT * FROM "v_usage_daily";

-- View recent errors
-- SELECT * FROM "v_recent_errors";

-- View top users by cost
-- SELECT * FROM "v_top_users_by_cost";

-- Get usage stats for last 24 hours
-- SELECT * FROM get_usage_stats(
--     CURRENT_TIMESTAMP - INTERVAL '24 hours',
--     CURRENT_TIMESTAMP
-- );

-- Calculate cost for a hypothetical request
-- SELECT calculate_usage_cost(1000, 500, 'anthropic');

-- =====================================================
-- END OF SEED DATA
-- =====================================================