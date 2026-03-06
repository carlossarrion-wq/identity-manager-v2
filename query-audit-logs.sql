-- Consultar los últimos eventos de auditoría
-- Ordenados por fecha más reciente primero

SELECT 
    id,
    operation_type,
    cognito_email,
    operation_timestamp,
    new_value->>'event_name' as event_name,
    new_value->>'log_level' as log_level,
    new_value->>'message' as message,
    new_value->>'trace_id' as trace_id,
    new_value->>'request_id' as request_id
FROM "identity-manager-audit-tbl"
WHERE operation_type LIKE '%AUTH%' 
   OR operation_type LIKE '%LOGIN%'
ORDER BY operation_timestamp DESC
LIMIT 20;

-- Contar eventos por tipo
SELECT 
    operation_type,
    COUNT(*) as total_events,
    MAX(operation_timestamp) as last_event
FROM "identity-manager-audit-tbl"
WHERE operation_type LIKE '%AUTH%' 
   OR operation_type LIKE '%LOGIN%'
GROUP BY operation_type
ORDER BY total_events DESC;