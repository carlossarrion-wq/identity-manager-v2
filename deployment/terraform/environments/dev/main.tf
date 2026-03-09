# =====================================================
# Identity Manager - Development Environment
# =====================================================

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }

  # Uncomment and configure for remote state
  # backend "s3" {
  #   bucket         = "your-terraform-state-bucket"
  #   key            = "identity-manager/dev/terraform.tfstate"
  #   region         = "eu-west-1"
  #   encrypt        = true
  #   dynamodb_table = "terraform-state-lock"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "identity-manager"
      Environment = "dev"
      ManagedBy   = "Terraform"
    }
  }
}

# Use RAG-VPC (same as EC2)
data "aws_vpc" "rag" {
  id = "vpc-04ba39cd0772a280b"
}

# Use existing PUBLIC subnets from RAG-VPC (for RDS with publicly_accessible)
data "aws_subnet" "rag_public" {
  for_each = toset(["subnet-038b1f57392415153", "subnet-0e984b3f275d482f1"])
  id       = each.value
}

# Use existing PRIVATE subnets from RAG-VPC (for Lambda if needed)
data "aws_subnet" "rag_private" {
  for_each = toset(["subnet-09d9eef6deec49835", "subnet-095c40811320a693a"])
  id       = each.value
}

# RDS Module - Using PUBLIC subnets for publicly_accessible RDS
module "rds" {
  source = "../../modules/rds"

  project_name = "identity-manager"
  environment  = "dev"

  vpc_id     = data.aws_vpc.rag.id
  subnet_ids = [for s in data.aws_subnet.rag_public : s.id]  # PUBLIC subnets for internet access

  allowed_cidr_blocks = [data.aws_vpc.rag.cidr_block]

  database_name   = "identity_manager_dev_rds"
  master_username = var.db_master_username

  postgres_version  = var.postgres_version
  instance_class    = var.db_instance_class
  allocated_storage = var.db_allocated_storage
  storage_type      = var.db_storage_type

  publicly_accessible     = var.db_publicly_accessible
  backup_retention_period = var.db_backup_retention_period
  deletion_protection     = var.db_deletion_protection
  skip_final_snapshot     = var.db_skip_final_snapshot

  monitoring_interval = var.db_monitoring_interval

  tags = {
    Environment = "dev"
    Application = "identity-manager"
  }
}

# Secrets Module - Email SMTP Credentials
module "secrets" {
  source = "../../modules/secrets"

  project_name = "identity-mgmt"
  environment  = "dev"
}

# Create JWT Secret Key (nomenclatura: identity-mgmt-dev-key-access)
resource "random_password" "jwt_secret" {
  length  = 64
  special = true
}

resource "aws_secretsmanager_secret" "jwt_secret" {
  name        = "identity-mgmt-dev-key-access"
  description = "JWT Private Key for Identity Manager Dev - Token Signing"

  tags = {
    Environment = "dev"
    Application = "identity-mgmt"
    Type        = "key"
    Detail      = "access"
  }
}

resource "aws_secretsmanager_secret_version" "jwt_secret" {
  secret_id     = aws_secretsmanager_secret.jwt_secret.id
  secret_string = jsonencode({
    jwt_secret_key = random_password.jwt_secret.result
  })
}

# ============================================================================
# LAMBDA FUNCTIONS
# ============================================================================

# Lambda API - identity-mgmt-dev-api-lmbd
module "lambda" {
  source = "../../modules/lambda"

  function_name    = "identity-mgmt-dev-api-lmbd"
  lambda_zip_path  = "/Users/csarrion/Cline/identity-manager-v2/deployment/terraform/lambda-packages/identity-mgmt-api-lambda-latest.zip"
  
  # S3 deployment not needed (ZIP < 50MB after cleanup)
  # s3_bucket        = "gestion-demanda-lambda-deployments"
  # s3_key           = "identity-manager/identity-mgmt-api-lambda-20260303.zip"
  
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
  # vpc_config = {
  #   subnet_ids         = [for s in data.aws_subnet.rag_private : s.id]
  #   security_group_ids = [module.rds.security_group_id]
  # }
  
  # Optional features
  enable_xray          = true
  create_function_url  = true  # Para testing
  create_alarms        = false # Disabled for dev
  
  tags = {
    Environment = "dev"
    Application = "identity-manager"
    Component   = "api"
  }
}

# Lambda Auth - login-authorization-service
module "auth_lambda" {
  source = "../../modules/lambda"

  function_name    = "login-authorization-service"
  lambda_zip_path  = "../../../backend/lambdas/auth-lambda"
  
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
  vpc_config = null
  
  # Optional features
  enable_xray          = false
  create_function_url  = false  # Auth Lambda usa API Gateway
  create_alarms        = false  # Disabled for dev
  log_retention_days   = 7
  
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

# ============================================================================
# FRONTEND - S3 + CloudFront
# ============================================================================

module "frontend" {
  source = "../../modules/frontend"

  project_name         = "identity-mgmt"
  environment          = "dev"
  frontend_source_path = "${path.module}/../../../../frontend"
  cloudfront_price_class = "PriceClass_100"

  tags = {
    Environment = "dev"
    Application = "identity-manager"
    Component   = "frontend"
    Team        = "Platform"
    CostCenter  = "Engineering"
  }
}

# ============================================================================
# OUTPUTS
# ============================================================================

# RDS Outputs
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

# Lambda API Outputs
output "lambda_function_name" {
  description = "Nombre de la función Lambda API"
  value       = module.lambda.function_name
}

output "lambda_function_arn" {
  description = "ARN de la función Lambda API"
  value       = module.lambda.function_arn
}

# Lambda Auth Outputs
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

# Frontend Outputs
output "frontend_cloudfront_url" {
  description = "CloudFront URL for the frontend"
  value       = module.frontend.cloudfront_url
}

output "frontend_s3_bucket" {
  description = "S3 bucket name"
  value       = module.frontend.s3_bucket_name
}

output "frontend_cloudfront_distribution_id" {
  description = "CloudFront distribution ID (for cache invalidation)"
  value       = module.frontend.cloudfront_distribution_id
}
