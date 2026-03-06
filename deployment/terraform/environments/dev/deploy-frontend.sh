#!/bin/bash
# ============================================================================
# Frontend Deployment Script
# ============================================================================
# This script deploys the Identity Manager frontend to S3 + CloudFront

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Identity Manager - Frontend Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "frontend.tf" ]; then
    echo -e "${RED}Error: frontend.tf not found. Please run this script from deployment/terraform/environments/dev/${NC}"
    exit 1
fi

# Initialize Terraform if needed
if [ ! -d ".terraform" ]; then
    echo -e "${YELLOW}Initializing Terraform...${NC}"
    terraform init
    echo ""
fi

# Plan the deployment
echo -e "${YELLOW}Planning deployment...${NC}"
terraform plan -target=module.frontend -out=frontend.tfplan
echo ""

# Ask for confirmation
read -p "Do you want to apply this plan? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo -e "${RED}Deployment cancelled.${NC}"
    rm -f frontend.tfplan
    exit 0
fi

# Apply the plan
echo -e "${YELLOW}Deploying frontend...${NC}"
terraform apply frontend.tfplan
rm -f frontend.tfplan
echo ""

# Get outputs
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}CloudFront URL:${NC}"
terraform output -raw frontend_cloudfront_url
echo ""
echo ""
echo -e "${YELLOW}S3 Bucket:${NC}"
terraform output -raw frontend_s3_bucket
echo ""
echo ""
echo -e "${YELLOW}CloudFront Distribution ID:${NC}"
terraform output -raw frontend_cloudfront_distribution_id
echo ""
echo ""

# Instructions for cache invalidation
echo -e "${YELLOW}To invalidate CloudFront cache after updates:${NC}"
echo "aws cloudfront create-invalidation --distribution-id \$(terraform output -raw frontend_cloudfront_distribution_id) --paths '/*'"
echo ""

echo -e "${GREEN}✓ Frontend deployed successfully!${NC}"