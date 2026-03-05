/**
 * Identity Manager Dashboard - API Client
 * ========================================
 * Functions to interact with the Identity Manager Lambda API
 */

class IdentityManagerAPI {
    constructor() {
        this.endpoint = API_CONFIG.endpoint;
        this.timeout = API_CONFIG.timeout;
    }

    /**
     * Make API request to Lambda
     */
    async request(operation, data = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);

        try {
            console.log(`📡 API Request: ${operation}`, data);
            
            const response = await fetch(this.endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    operation: operation,
                    ...data
                }),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            // Try to parse response body even if status is not OK
            let result;
            try {
                result = await response.json();
            } catch (parseError) {
                // If JSON parsing fails, create a generic error
                throw new Error(`HTTP ${response.status}: ${response.statusText || 'Request failed'}`);
            }

            // Check if response is not OK
            if (!response.ok) {
                // Extract detailed error message from backend
                const errorMessage = this.extractErrorMessage(result, response.status);
                const error = new Error(errorMessage);
                error.statusCode = response.status;
                error.details = result.error;
                throw error;
            }

            // Check if API returned success: false
            if (!result.success) {
                const errorMessage = this.extractErrorMessage(result);
                const error = new Error(errorMessage);
                error.details = result.error;
                throw error;
            }

            console.log(`✅ API Response: ${operation}`, result.data);
            return result.data;

        } catch (error) {
            clearTimeout(timeoutId);
            
            // Handle timeout errors
            if (error.name === 'AbortError') {
                error.message = `Request timeout after ${this.timeout/1000}s`;
            }
            
            console.error(`❌ API Error: ${operation}`, error);
            throw error;
        }
    }

    /**
     * Extract detailed error message from API response
     */
    extractErrorMessage(result, statusCode = null) {
        // Priority 1: Check for error.message
        if (result.error?.message) {
            return result.error.message;
        }

        // Priority 2: Check for error.error (nested error)
        if (result.error?.error) {
            return result.error.error;
        }

        // Priority 3: Check for message at root level
        if (result.message) {
            return result.message;
        }

        // Priority 4: Check for error string
        if (typeof result.error === 'string') {
            return result.error;
        }

        // Priority 5: Check for error_type
        if (result.error?.error_type) {
            return `${result.error.error_type}: ${result.error.details || 'Unknown error'}`;
        }

        // Priority 6: Use status code if available
        if (statusCode) {
            const statusMessages = {
                400: 'Bad Request - Invalid input data',
                401: 'Unauthorized - Authentication required',
                403: 'Forbidden - Access denied',
                404: 'Not Found - Resource does not exist',
                409: 'Conflict - Resource already exists or conflict detected',
                422: 'Validation Error - Invalid data provided',
                500: 'Internal Server Error - Something went wrong on the server',
                502: 'Bad Gateway - Server communication error',
                503: 'Service Unavailable - Server is temporarily unavailable'
            };
            return statusMessages[statusCode] || `HTTP Error ${statusCode}`;
        }

        // Fallback
        return 'An unknown error occurred';
    }

    // ============================================================================
    // USERS API
    // ============================================================================

    async listUsers(filters = {}, pagination = {}) {
        return await this.request('list_users', { filters, pagination });
    }

    async createUser(email, person, group, temporaryPassword = null, sendEmail = true, autoRegenerate = true) {
        return await this.request('create_user', {
            data: {
                email,
                person,
                group,
                temporary_password: temporaryPassword,
                send_email: sendEmail,
                auto_regenerate_tokens: autoRegenerate
            }
        });
    }

    async deleteUser(userId) {
        return await this.request('delete_user', { user_id: userId });
    }

    // ============================================================================
    // TOKENS API
    // ============================================================================

    async listTokens(filters = {}, pagination = {}) {
        return await this.request('list_tokens', { filters, pagination });
    }

    async createToken(userId, profileId, validityPeriod = '90_days', sendEmail = false) {
        return await this.request('create_token', {
            data: {
                user_id: userId,
                application_profile_id: profileId,
                validity_period: validityPeriod,
                send_email: sendEmail
            }
        });
    }

    async validateToken(token) {
        return await this.request('validate_token', { token });
    }

    async revokeToken(tokenId, reason = 'Revoked from dashboard') {
        return await this.request('revoke_token', { 
            token_id: tokenId,
            reason 
        });
    }

    async deleteToken(tokenId) {
        return await this.request('delete_token', { token_id: tokenId });
    }

    // ============================================================================
    // PROFILES API
    // ============================================================================

    async listProfiles(filters = {}) {
        return await this.request('list_profiles', { filters });
    }

    // ============================================================================
    // GROUPS API
    // ============================================================================

    async listGroups() {
        return await this.request('list_groups');
    }

    // ============================================================================
    // USER QUOTAS API
    // ============================================================================

    async getUserQuotasToday() {
        return await this.request('get_user_quotas_today');
    }

    // ============================================================================
    // CONFIG API
    // ============================================================================

    async getConfig() {
        return await this.request('get_config');
    }

    // ============================================================================
    // CONNECTION TEST
    // ============================================================================

    async testConnection() {
        try {
            await this.getConfig();
            return true;
        } catch (error) {
            return false;
        }
    }
}

// Create global API instance
window.api = new IdentityManagerAPI();

console.log('✅ API Client initialized');
