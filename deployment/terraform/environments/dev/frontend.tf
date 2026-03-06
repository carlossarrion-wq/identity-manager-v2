# ============================================================================
# Frontend Deployment - Development Environment
# ============================================================================

module "frontend" {
  source = "../../modules/frontend"

  project_name         = "identity-mgmt"
  environment          = "dev"
  frontend_source_path = "${path.module}/../../../../frontend"
  cloudfront_price_class = "PriceClass_100"

  tags = {
    Team        = "Platform"
    CostCenter  = "Engineering"
    Application = "Identity Manager"
  }
}

# ============================================================================
# Outputs
# ============================================================================

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