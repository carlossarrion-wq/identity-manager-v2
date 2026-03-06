# ============================================================================
# Frontend Deployment - S3 + CloudFront
# ============================================================================
# This module deploys the Identity Manager frontend to S3 with CloudFront CDN

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ============================================================================
# S3 Bucket for Frontend
# ============================================================================

resource "aws_s3_bucket" "frontend" {
  bucket = "${var.project_name}-${var.environment}-frontend-s3"

  tags = {
    Name        = "${var.project_name}-${var.environment}-frontend-s3"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}

# Block public access (CloudFront will access via OAI)
resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable versioning
resource "aws_s3_bucket_versioning" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# ============================================================================
# CloudFront Origin Access Identity
# ============================================================================

resource "aws_cloudfront_origin_access_identity" "frontend" {
  comment = "OAI for ${var.project_name}-${var.environment} frontend"
}

# S3 bucket policy to allow CloudFront access
resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontAccess"
        Effect = "Allow"
        Principal = {
          AWS = aws_cloudfront_origin_access_identity.frontend.iam_arn
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.frontend.arn}/*"
      }
    ]
  })
}

# ============================================================================
# CloudFront Distribution
# ============================================================================

resource "aws_cloudfront_distribution" "frontend" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "${var.project_name}-${var.environment} Frontend"
  default_root_object = "login.html"
  price_class         = var.cloudfront_price_class

  origin {
    domain_name = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id   = "S3-${aws_s3_bucket.frontend.id}"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.frontend.cloudfront_access_identity_path
    }
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${aws_s3_bucket.frontend.id}"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
    compress               = true
  }

  # Cache behavior for static assets (CSS, JS, images)
  ordered_cache_behavior {
    path_pattern     = "/dashboard/css/*"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${aws_s3_bucket.frontend.id}"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 86400  # 1 day
    max_ttl                = 31536000  # 1 year
    compress               = true
  }

  ordered_cache_behavior {
    path_pattern     = "/dashboard/js/*"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${aws_s3_bucket.frontend.id}"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 86400  # 1 day
    max_ttl                = 31536000  # 1 year
    compress               = true
  }

  # Custom error responses
  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/login.html"
  }

  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/login.html"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
    minimum_protocol_version       = "TLSv1.2_2021"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-frontend-cdn"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}

# ============================================================================
# Upload Frontend Files to S3
# ============================================================================

# Upload login.html
resource "aws_s3_object" "login_html" {
  bucket       = aws_s3_bucket.frontend.id
  key          = "login.html"
  source       = "${var.frontend_source_path}/login.html"
  etag         = filemd5("${var.frontend_source_path}/login.html")
  content_type = "text/html"
}

# Upload dashboard index.html
resource "aws_s3_object" "dashboard_index" {
  bucket       = aws_s3_bucket.frontend.id
  key          = "dashboard/index.html"
  source       = "${var.frontend_source_path}/dashboard/index.html"
  etag         = filemd5("${var.frontend_source_path}/dashboard/index.html")
  content_type = "text/html"
}

# Upload CSS files
resource "aws_s3_object" "dashboard_css" {
  for_each = fileset("${var.frontend_source_path}/dashboard/css", "**/*.css")

  bucket       = aws_s3_bucket.frontend.id
  key          = "dashboard/css/${each.value}"
  source       = "${var.frontend_source_path}/dashboard/css/${each.value}"
  etag         = filemd5("${var.frontend_source_path}/dashboard/css/${each.value}")
  content_type = "text/css"
}

# Upload JS files
resource "aws_s3_object" "dashboard_js" {
  for_each = fileset("${var.frontend_source_path}/dashboard/js", "**/*.js")

  bucket       = aws_s3_bucket.frontend.id
  key          = "dashboard/js/${each.value}"
  source       = "${var.frontend_source_path}/dashboard/js/${each.value}"
  etag         = filemd5("${var.frontend_source_path}/dashboard/js/${each.value}")
  content_type = "application/javascript"
}