# Project Brief: Identity Manager v2

## Project Overview
Identity Manager v2 is a comprehensive AWS-based identity and access management system that provides centralized user management, authentication, authorization, and usage tracking for AI/ML services (specifically AWS Bedrock).

## Core Requirements

### Primary Objectives
1. **Centralized Identity Management**: Manage users, roles, and permissions across multiple environments
2. **Authentication & Authorization**: Secure JWT-based authentication with fine-grained permission control
3. **Usage Tracking**: Monitor and track AI service usage (tokens, costs) per user and organization
4. **Multi-Environment Support**: Support dev, pre, and production environments with isolated configurations
5. **Dashboard Interface**: Web-based UI for administrators to manage users, permissions, and view usage analytics

### Key Features
- User CRUD operations with email-based identification
- Role-based access control (RBAC) with hierarchical permissions
- AWS Cognito integration for authentication
- JWT token validation and authorization
- User quota management and enforcement
- Proxy service for AWS Bedrock with usage tracking
- Real-time usage analytics and reporting
- Email case-insensitive user lookups

## Technical Constraints
- **Cloud Platform**: AWS (Lambda, RDS PostgreSQL, Cognito, API Gateway, S3)
- **Infrastructure**: Terraform for IaC
- **Backend**: Python 3.x with AWS Lambda
- **Frontend**: Vanilla JavaScript (no frameworks)
- **Database**: PostgreSQL on AWS RDS
- **Authentication**: AWS Cognito + Custom JWT validation

## Success Criteria
1. Secure, scalable identity management system
2. Sub-second API response times
3. Accurate usage tracking and quota enforcement
4. Easy deployment across multiple environments
5. Comprehensive audit logging
6. Intuitive admin dashboard

## Out of Scope
- Self-service user registration (admin-managed only)
- Multi-factor authentication (handled by Cognito)
- Custom authentication providers beyond Cognito
- Real-time streaming analytics