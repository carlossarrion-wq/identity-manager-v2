# ============================================================================
# AWS Secrets Manager - Email SMTP Credentials
# ============================================================================

resource "aws_secretsmanager_secret" "email_smtp" {
  name        = "${var.project_name}-${var.environment}-email-smtp"
  description = "Gmail SMTP credentials for email notifications"

  tags = {
    Name        = "${var.project_name}-${var.environment}-email-smtp"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}

resource "aws_secretsmanager_secret_version" "email_smtp" {
  secret_id = aws_secretsmanager_secret.email_smtp.id
  secret_string = jsonencode({
    gmail_smtp = {
      server   = "smtp.gmail.com"
      port     = 587
      user     = "cline.aws.noreply@gmail.com"
      password = "lozs wwqa vfpn nlup"
      use_tls  = true
    }
    email_settings = {
      default_language = "es"
      timezone         = "Europe/Madrid"
      reply_to         = "cline.aws.noreply@gmail.com"
    }
  })
}
