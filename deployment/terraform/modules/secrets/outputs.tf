output "email_smtp_secret_arn" {
  description = "ARN of the email SMTP secret"
  value       = aws_secretsmanager_secret.email_smtp.arn
}

output "email_smtp_secret_name" {
  description = "Name of the email SMTP secret"
  value       = aws_secretsmanager_secret.email_smtp.name
}
