# =====================================================
# Development Environment Outputs
# =====================================================

output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = module.rds.db_instance_endpoint
}

output "rds_address" {
  description = "RDS instance address"
  value       = module.rds.db_instance_address
}

output "rds_port" {
  description = "RDS instance port"
  value       = module.rds.db_instance_port
}

output "database_name" {
  description = "Database name"
  value       = module.rds.db_name
}

output "secret_arn" {
  description = "ARN of Secrets Manager secret with DB credentials"
  value       = module.rds.secret_arn
}

output "secret_name" {
  description = "Name of Secrets Manager secret with DB credentials"
  value       = module.rds.secret_name
}

output "security_group_id" {
  description = "Security group ID for RDS"
  value       = module.rds.security_group_id
}

output "connection_command" {
  description = "Command to connect to the database"
  value       = "aws secretsmanager get-secret-value --secret-id ${module.rds.secret_name} --query SecretString --output text | jq -r 'psql -h \\(.host) -p \\(.port) -U \\(.username) -d \\(.dbname)'"
}
