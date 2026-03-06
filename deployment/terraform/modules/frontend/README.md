# Frontend Deployment Module

This Terraform module deploys the Identity Manager frontend to AWS S3 with CloudFront CDN distribution.

## Features

- ✅ S3 bucket with versioning and encryption
- ✅ CloudFront CDN for global distribution
- ✅ Origin Access Identity (OAI) for secure S3 access
- ✅ Automatic HTTPS redirect
- ✅ Custom error pages (404/403 → login.html)
- ✅ Optimized caching for static assets
- ✅ Automatic file upload to S3

## Architecture

```
┌─────────────┐
│   Users     │
└──────┬──────┘
       │ HTTPS
       ▼
┌─────────────────┐
│   CloudFront    │ ← CDN Distribution
│   (Global CDN)  │
└────────┬────────┘
         │ OAI
         ▼
┌─────────────────┐
│   S3 Bucket     │ ← Static Files
│ (Private)       │
└─────────────────┘
```

## Naming Convention

**S3 Bucket:** `<project>-<environment>-frontend-s3`

Examples:
- `identity-mgmt-dev-frontend-s3`
- `identity-mgmt-pre-frontend-s3`
- `identity-mgmt-pro-frontend-s3`

## Usage

### Basic Example

```hcl
module "frontend" {
  source = "../../modules/frontend"

  project_name         = "identity-mgmt"
  environment          = "dev"
  frontend_source_path = "${path.module}/../../../../frontend"
}
```

### Complete Example

```hcl
module "frontend" {
  source = "../../modules/frontend"

  project_name           = "identity-mgmt"
  environment            = "dev"
  frontend_source_path   = "${path.module}/../../../../frontend"
  cloudfront_price_class = "PriceClass_100"

  tags = {
    Team        = "Platform"
    CostCenter  = "Engineering"
    Application = "Identity Manager"
  }
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| project_name | Project name (e.g., identity-mgmt) | string | - | yes |
| environment | Environment (dev, pre, pro) | string | - | yes |
| frontend_source_path | Path to frontend source files | string | `../../frontend` | no |
| cloudfront_price_class | CloudFront price class | string | `PriceClass_100` | no |
| tags | Additional tags | map(string) | `{}` | no |

## Outputs

| Name | Description |
|------|-------------|
| s3_bucket_name | Name of the S3 bucket |
| s3_bucket_arn | ARN of the S3 bucket |
| cloudfront_distribution_id | CloudFront distribution ID |
| cloudfront_domain_name | CloudFront domain name |
| cloudfront_url | Full HTTPS URL |

## Deployment

### Using the Script

```bash
cd deployment/terraform/environments/dev
./deploy-frontend.sh
```

### Manual Deployment

```bash
cd deployment/terraform/environments/dev

# Initialize Terraform
terraform init

# Plan deployment
terraform plan -target=module.frontend

# Apply deployment
terraform apply -target=module.frontend
```

## Updating Frontend Files

After making changes to frontend files:

```bash
# Re-apply Terraform to upload new files
terraform apply -target=module.frontend

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id $(terraform output -raw frontend_cloudfront_distribution_id) \
  --paths "/*"
```

## CloudFront Price Classes

- **PriceClass_100**: US, Canada, Europe (cheapest)
- **PriceClass_200**: US, Canada, Europe, Asia, Middle East, Africa
- **PriceClass_All**: All edge locations (most expensive)

## File Structure

```
frontend/
├── login.html              # Login page (root)
└── dashboard/
    ├── index.html          # Dashboard
    ├── css/
    │   └── *.css          # Stylesheets
    └── js/
        └── *.js           # JavaScript files
```

## Security Features

- ✅ S3 bucket is private (no public access)
- ✅ CloudFront uses Origin Access Identity (OAI)
- ✅ HTTPS enforced (HTTP redirects to HTTPS)
- ✅ Server-side encryption (AES256)
- ✅ Versioning enabled

## Cache Behavior

- **HTML files**: 1 hour cache (3600s)
- **CSS/JS files**: 1 day cache (86400s)
- **Compression**: Enabled for all files

## Cost Optimization

- Uses `PriceClass_100` by default (cheapest)
- Compression enabled to reduce data transfer
- Efficient caching to reduce origin requests

## Troubleshooting

### Files not updating

```bash
# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id YOUR_DISTRIBUTION_ID \
  --paths "/*"
```

### Access denied errors

Check that:
1. S3 bucket policy allows CloudFront OAI
2. CloudFront distribution is enabled
3. Files have correct permissions

### 404 errors

The module redirects 404/403 to `/login.html`. Ensure `login.html` exists in the S3 bucket.

## Examples

See `deployment/terraform/environments/dev/frontend.tf` for a complete working example.

## Requirements

- Terraform >= 1.0
- AWS Provider ~> 5.0
- AWS CLI configured with appropriate credentials

## License

Internal use only.