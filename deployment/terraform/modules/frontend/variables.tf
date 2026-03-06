# ============================================================================
# Frontend Module Variables
# ============================================================================

variable "project_name" {
  description = "Project name (e.g., identity-mgmt, kb-agent, bedrock-proxy)"
  type        = string
  
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]*[a-z0-9]$", var.project_name))
    error_message = "Project name must be lowercase, start with a letter, and contain only letters, numbers, and hyphens."
  }
}

variable "environment" {
  description = "Environment name (dev, pre, pro)"
  type        = string
  
  validation {
    condition     = contains(["dev", "pre", "pro"], var.environment)
    error_message = "Environment must be one of: dev, pre, pro."
  }
}

variable "frontend_source_path" {
  description = "Path to the frontend source files"
  type        = string
  default     = "../../frontend"
}

variable "cloudfront_price_class" {
  description = "CloudFront price class"
  type        = string
  default     = "PriceClass_100"  # US, Canada, Europe
  
  validation {
    condition     = contains(["PriceClass_100", "PriceClass_200", "PriceClass_All"], var.cloudfront_price_class)
    error_message = "Price class must be one of: PriceClass_100, PriceClass_200, PriceClass_All."
  }
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}