# ============================================================================
# Lambda Function Module - Identity Manager API
# ============================================================================
# Módulo para desplegar la función Lambda de Identity Manager API
# Nomenclatura: identity-mgmt-<entorno>-api-lmbd
# ============================================================================

# Data source para obtener la cuenta de AWS
data "aws_caller_identity" "current" {}

# Data source para obtener la región
data "aws_region" "current" {}

# ============================================================================
# IAM Role para Lambda
# ============================================================================

resource "aws_iam_role" "lambda_role" {
  name = "${var.function_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name = "${var.function_name}-role"
    }
  )
}

# Policy para logs de CloudWatch
resource "aws_iam_role_policy" "lambda_logging" {
  name = "${var.function_name}-logging"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.function_name}:*"
      }
    ]
  })
}

# Policy para VPC (si se usa)
resource "aws_iam_role_policy" "lambda_vpc" {
  count = var.vpc_config != null ? 1 : 0
  name  = "${var.function_name}-vpc"
  role  = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface",
          "ec2:AssignPrivateIpAddresses",
          "ec2:UnassignPrivateIpAddresses"
        ]
        Resource = "*"
      }
    ]
  })
}

# Policy para Secrets Manager
resource "aws_iam_role_policy" "lambda_secrets" {
  name = "${var.function_name}-secrets"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          var.db_secret_arn,
          var.jwt_secret_arn,
          var.email_smtp_secret_arn
        ]
      }
    ]
  })
}

# Policy para Cognito
resource "aws_iam_role_policy" "lambda_cognito" {
  name = "${var.function_name}-cognito"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cognito-idp:AdminCreateUser",
          "cognito-idp:AdminDeleteUser",
          "cognito-idp:AdminGetUser",
          "cognito-idp:AdminAddUserToGroup",
          "cognito-idp:AdminRemoveUserFromGroup",
          "cognito-idp:AdminListGroupsForUser",
          "cognito-idp:ListUsers",
          "cognito-idp:ListUsersInGroup",
          "cognito-idp:ListGroups"
        ]
        Resource = var.cognito_user_pool_arn
      }
    ]
  })
}

# ============================================================================
# CloudWatch Log Group
# ============================================================================

resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = var.log_retention_days

  tags = merge(
    var.tags,
    {
      Name = "${var.function_name}-logs"
    }
  )
}

# ============================================================================
# Lambda Function
# ============================================================================

resource "aws_lambda_function" "api" {
  # Usar S3 si el archivo es mayor a 50MB, sino usar filename directo
  s3_bucket        = var.s3_bucket != null ? var.s3_bucket : null
  s3_key           = var.s3_key != null ? var.s3_key : null
  filename         = var.s3_bucket == null ? var.lambda_zip_path : null
  function_name    = var.function_name
  role            = aws_iam_role.lambda_role.arn
  handler         = "lambda_function.lambda_handler"
  source_code_hash = filebase64sha256(var.lambda_zip_path)
  runtime         = "python3.12"
  timeout         = var.timeout
  memory_size     = var.memory_size

  # Lambda Layer - Klayers psycopg2-binary (mismo que Dashboard Consultas RAG)
  layers = [
    "arn:aws:lambda:eu-west-1:770693421928:layer:Klayers-p312-psycopg2-binary:2"
  ]

  environment {
    variables = {
      COGNITO_USER_POOL_ID    = var.cognito_user_pool_id
      DB_SECRET_NAME          = var.db_secret_name
      JWT_SECRET_NAME         = var.jwt_secret_name
      EMAIL_SMTP_SECRET_NAME  = var.email_smtp_secret_name
      LOG_LEVEL               = var.log_level
    }
  }

  # VPC Configuration (opcional)
  dynamic "vpc_config" {
    for_each = var.vpc_config != null ? [var.vpc_config] : []
    content {
      subnet_ids         = vpc_config.value.subnet_ids
      security_group_ids = vpc_config.value.security_group_ids
    }
  }

  # Tracing con X-Ray
  tracing_config {
    mode = var.enable_xray ? "Active" : "PassThrough"
  }

  # Dead Letter Queue (opcional)
  dynamic "dead_letter_config" {
    for_each = var.dlq_arn != null ? [var.dlq_arn] : []
    content {
      target_arn = dead_letter_config.value
    }
  }

  tags = merge(
    var.tags,
    {
      Name = var.function_name
    }
  )

  depends_on = [
    aws_cloudwatch_log_group.lambda_logs,
    aws_iam_role_policy.lambda_logging,
    aws_iam_role_policy.lambda_secrets
  ]
}

# ============================================================================
# Lambda Function URL (opcional - para testing)
# ============================================================================

resource "aws_lambda_function_url" "api_url" {
  count              = var.create_function_url ? 1 : 0
  function_name      = aws_lambda_function.api.function_name
  authorization_type = "NONE"  # Cambiar a "AWS_IAM" en producción

  cors {
    allow_credentials = false
    allow_origins     = ["*"]
    allow_methods     = ["*"]
    allow_headers     = ["content-type", "authorization", "x-amz-date", "x-api-key", "x-amz-security-token"]
    expose_headers    = ["content-type", "x-amzn-requestid"]
    max_age          = 86400
  }
}

# ============================================================================
# CloudWatch Alarms
# ============================================================================

# Alarm para errores
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  count               = var.create_alarms ? 1 : 0
  alarm_name          = "${var.function_name}-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "Lambda function errors"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.api.function_name
  }

  tags = var.tags
}

# Alarm para throttling
resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  count               = var.create_alarms ? 1 : 0
  alarm_name          = "${var.function_name}-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "Lambda function throttles"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.api.function_name
  }

  tags = var.tags
}

# Alarm para duración
resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  count               = var.create_alarms ? 1 : 0
  alarm_name          = "${var.function_name}-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = var.timeout * 1000 * 0.8  # 80% del timeout
  alarm_description   = "Lambda function duration approaching timeout"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.api.function_name
  }

  tags = var.tags
}
