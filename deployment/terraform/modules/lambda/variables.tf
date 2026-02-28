# ============================================================================
# Lambda Module Variables
# ============================================================================

variable "function_name" {
  description = "Nombre de la función Lambda (debe seguir nomenclatura: identity-mgmt-<env>-api-lmbd)"
  type        = string

  validation {
    condition     = can(regex("^identity-mgmt-(dev|pre|pro)-api-lmbd$", var.function_name))
    error_message = "El nombre debe seguir el formato: identity-mgmt-<env>-api-lmbd donde env es dev, pre o pro"
  }
}

variable "lambda_zip_path" {
  description = "Ruta al archivo ZIP con el código de la Lambda"
  type        = string
}

variable "timeout" {
  description = "Timeout de la función Lambda en segundos"
  type        = number
  default     = 30
}

variable "memory_size" {
  description = "Memoria asignada a la función Lambda en MB"
  type        = number
  default     = 512
}

variable "log_retention_days" {
  description = "Días de retención de logs en CloudWatch"
  type        = number
  default     = 7
}

variable "log_level" {
  description = "Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
  type        = string
  default     = "INFO"
}

# ============================================================================
# Cognito Configuration
# ============================================================================

variable "cognito_user_pool_id" {
  description = "ID del User Pool de Cognito"
  type        = string
}

variable "cognito_user_pool_arn" {
  description = "ARN del User Pool de Cognito"
  type        = string
}

# ============================================================================
# Secrets Manager Configuration
# ============================================================================

variable "db_secret_name" {
  description = "Nombre del secreto de base de datos en Secrets Manager"
  type        = string
}

variable "db_secret_arn" {
  description = "ARN del secreto de base de datos"
  type        = string
}

variable "jwt_secret_name" {
  description = "Nombre del secreto JWT en Secrets Manager"
  type        = string
}

variable "jwt_secret_arn" {
  description = "ARN del secreto JWT"
  type        = string
}

variable "email_smtp_secret_name" {
  description = "Nombre del secreto de email SMTP en Secrets Manager"
  type        = string
}

variable "email_smtp_secret_arn" {
  description = "ARN del secreto de email SMTP"
  type        = string
}

# ============================================================================
# VPC Configuration (opcional)
# ============================================================================

variable "vpc_config" {
  description = "Configuración de VPC para la Lambda"
  type = object({
    subnet_ids         = list(string)
    security_group_ids = list(string)
  })
  default = null
}

# ============================================================================
# Optional Features
# ============================================================================

variable "enable_xray" {
  description = "Habilitar AWS X-Ray tracing"
  type        = bool
  default     = true
}

variable "create_function_url" {
  description = "Crear Function URL para acceso directo (útil para testing)"
  type        = bool
  default     = false
}

variable "create_alarms" {
  description = "Crear alarmas de CloudWatch"
  type        = bool
  default     = true
}

variable "dlq_arn" {
  description = "ARN de Dead Letter Queue (opcional)"
  type        = string
  default     = null
}

# ============================================================================
# Tags
# ============================================================================

variable "tags" {
  description = "Tags para aplicar a todos los recursos"
  type        = map(string)
  default     = {}
}
