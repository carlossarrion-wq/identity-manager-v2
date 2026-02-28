# ============================================================================
# Lambda Module Outputs
# ============================================================================

output "function_name" {
  description = "Nombre de la función Lambda"
  value       = aws_lambda_function.api.function_name
}

output "function_arn" {
  description = "ARN de la función Lambda"
  value       = aws_lambda_function.api.arn
}

output "function_invoke_arn" {
  description = "ARN de invocación de la función Lambda (para API Gateway)"
  value       = aws_lambda_function.api.invoke_arn
}

output "function_url" {
  description = "URL de la función Lambda (si está habilitada)"
  value       = var.create_function_url ? aws_lambda_function_url.api_url[0].function_url : null
}

output "function_role_arn" {
  description = "ARN del rol IAM de la función Lambda"
  value       = aws_iam_role.lambda_role.arn
}

output "function_role_name" {
  description = "Nombre del rol IAM de la función Lambda"
  value       = aws_iam_role.lambda_role.name
}

output "log_group_name" {
  description = "Nombre del grupo de logs de CloudWatch"
  value       = aws_cloudwatch_log_group.lambda_logs.name
}

output "log_group_arn" {
  description = "ARN del grupo de logs de CloudWatch"
  value       = aws_cloudwatch_log_group.lambda_logs.arn
}
