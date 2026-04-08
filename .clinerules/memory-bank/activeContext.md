# Active Context: Identity Manager v2

## Current Work Focus
The project is in a mature state with core functionality implemented. Recent work has focused on:
- Email case-sensitivity fixes for user lookups
- Token tracking impact analysis
- Proxy usage monitoring enhancements
- User quota management improvements

## Recent Changes

### Email Case-Sensitivity Fix (Latest)
- **Issue**: Email lookups were case-sensitive, causing user lookup failures
- **Solution**: Implemented case-insensitive email comparisons using LOWER() in SQL queries
- **Impact**: Affects user lookup, authentication, and API endpoints
- **Documentation**: See docs/15-EMAIL-CASE-SENSITIVITY-FIX.md

### Token Tracking Analysis
- **Analysis**: Evaluated impact of adding token tracking to proxy-bedrock service
- **Findings**: Documented in docs/16-TOKEN-TRACKING-IMPACT-ANALYSIS.md
- **Status**: Analysis complete, implementation pending decision

### User Quotas Dashboard
- **Feature**: Enhanced dashboard for viewing and managing user quotas
- **Components**: Frontend UI + backend API endpoints
- **Status**: Implemented and documented in docs/09-USER-QUOTAS-DASHBOARD.md

## Next Steps

### Immediate Priorities
1. **Testing**: Comprehensive testing of email case-sensitivity fixes
2. **Token Tracking**: Decision on implementing token tracking in proxy-bedrock
3. **Documentation**: Update API documentation with recent changes
4. **Monitoring**: Enhance CloudWatch dashboards for better observability

### Upcoming Features
1. **Bulk Operations**: Support for bulk user creation/updates
2. **Advanced Filtering**: Enhanced search and filter capabilities in dashboard
3. **Export Functionality**: CSV/JSON export of usage reports
4. **Notification System**: Alerts for quota thresholds and anomalies

## Active Decisions and Considerations

### Architecture Decisions
- **Monorepo Structure**: All components in single repository for easier management
- **Shared Code**: Common utilities in backend/shared for DRY principle
- **Lambda Layers**: Using layers for shared dependencies (psycopg2)
- **Environment Isolation**: Separate Terraform workspaces for dev/pre/pro

### Design Patterns
- **Service Layer**: Business logic separated from Lambda handlers
- **Response Builder**: Standardized API responses across all endpoints
- **Decorator Pattern**: Logging and error handling via decorators
- **Repository Pattern**: Database access abstracted through service classes

### Security Considerations
- **JWT Validation**: Dual validation (Cognito + custom external apps)
- **Permission Caching**: Cache permissions in JWT to reduce database calls
- **SQL Injection**: Using parameterized queries throughout
- **Secrets Management**: AWS Secrets Manager for sensitive configuration

## Important Patterns and Preferences

### Code Organization
- Lambda functions in `backend/lambdas/[function-name]/`
- Shared code in `backend/shared/`
- Database scripts in `database/`
- Frontend in `frontend/dashboard/`
- Infrastructure in `deployment/terraform/`

### Naming Conventions
- Snake_case for Python (PEP 8)
- camelCase for JavaScript
- Kebab-case for file names
- UPPER_CASE for constants and environment variables

### Error Handling
- Always return structured error responses
- Log errors with context (request ID, user ID, etc.)
- Use appropriate HTTP status codes
- Include actionable error messages

### Testing Strategy
- Unit tests for business logic
- Integration tests for API endpoints
- Mock external services (Cognito, RDS) in tests
- Test files colocated with implementation

## Learnings and Project Insights

### What Works Well
1. **Terraform Modules**: Reusable modules simplify multi-environment deployment
2. **Shared Code**: Reduces duplication and ensures consistency
3. **Comprehensive Logging**: AMS logging framework provides excellent observability
4. **JWT Permissions**: Embedding permissions in JWT reduces database load

### Challenges Encountered
1. **Email Case-Sensitivity**: Required careful SQL query updates across codebase
2. **Lambda Cold Starts**: Mitigated with provisioned concurrency for critical functions
3. **Database Connections**: Lambda connection pooling requires careful management
4. **CORS Configuration**: Required precise configuration for frontend-backend communication

### Best Practices Established
1. **Documentation First**: Document design decisions before implementation
2. **Incremental Changes**: Small, focused changes with clear commit messages
3. **Environment Parity**: Keep dev/pre/pro environments as similar as possible
4. **Security by Default**: Secure configurations as baseline, not afterthought

### Technical Debt
1. **Test Coverage**: Need more comprehensive test coverage
2. **Frontend Framework**: Consider migrating from vanilla JS to modern framework
3. **API Versioning**: Implement versioning strategy for breaking changes
4. **Monitoring**: Enhance CloudWatch dashboards and alerts