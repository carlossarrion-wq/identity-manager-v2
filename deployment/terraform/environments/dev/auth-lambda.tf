# =====================================================
# Auth Lambda - login-authorization-service
# =====================================================
# Lambda para autenticación de usuarios con Cognito
# Nomenclatura: login-authorization-service
# =====================================================

# Lambda Module para Auth
module "auth_lambda" {
  source = "../../modules/lambda"

  function_name    = "login-authorization-service"
  lambda_zip_path  = "../../../backend/lambdas/auth-lambda"  # Path relativo al directorio de trabajo
  
  timeout          = 30
  memory_size      = 512
  log_level        = "INFO"
  
  # Cognito Configuration
  cognito_user_pool_id  = "eu-west-1_UaMIbG9pD"
  cognito_user_pool_arn = "arn:aws:cognito-idp:eu-west-1:701055077130:userpool/eu-west-1_UaMIbG9pD"
  
  # Secrets Manager
  db_secret_name         = module.rds.secret_name
  db_secret_arn          = module.rds.secret_arn
  jwt_secret_name        = aws_secretsmanager_secret.jwt_secret.name
  jwt_secret_arn         = aws_secretsmanager_secret.jwt_secret.arn
  email_smtp_secret_name = module.secrets.email_smtp_secret_name
  email_smtp_secret_arn  = module.secrets.email_smtp_secret_arn
  
  # VPC Configuration - DISABLED for DEV
  # Lambda without VPC can access: Cognito (internet), RDS (public), Secrets Manager (internet)
  vpc_config = null
  
  # Optional features
  enable_xray          = false
  create_function_url  = false  # Auth Lambda usa API Gateway
  create_alarms        = false  # Disabled for dev
  log_retention_days   = 7      # Retención de logs para dev
  
  tags = {
    Environment = "dev"
    Application = "identity-manager"
    Component   = "authentication"
  }
  
  depends_on = [
    module.rds,
    aws_secretsmanager_secret.jwt_secret
  ]
}

# Output para la Lambda de Auth
output "auth_lambda_function_name" {
  description = "Nombre de la función Lambda de autenticación"
  value       = module.auth_lambda.function_name
}

output "auth_lambda_function_arn" {
  description = "ARN de la función Lambda de autenticación"
  value       = module.auth_lambda.function_arn
}

output "auth_lambda_role_arn" {
  description = "ARN del rol IAM de la Lambda de autenticación"
  value       = module.auth_lambda.role_arn
}