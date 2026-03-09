/**
 * JWT Permissions Module
 * ======================
 * Handles permissions based on JWT token instead of database queries
 */

class JWTPermissionsManager {
    constructor() {
        this.token = null;
        this.decodedToken = null;
        this.appPermissions = [];
        this.modulePermissions = [];
        this.userInfo = null;
    }

    /**
     * Initialize by loading and decoding the JWT token
     */
    init() {
        console.log('🔐 Initializing JWT Permissions Manager...');
        
        try {
            // Get token from localStorage
            this.token = localStorage.getItem('auth_token');
            
            if (!this.token) {
                console.warn('⚠️ No auth token found');
                return false;
            }
            
            // Decode token
            this.decodedToken = this.decodeJWT(this.token);
            
            if (!this.decodedToken) {
                console.error('❌ Failed to decode JWT');
                return false;
            }
            
            // Extract permissions
            this.appPermissions = this.decodedToken.app_permissions || [];
            this.modulePermissions = this.decodedToken.module_permissions || [];
            
            // Extract user info
            this.userInfo = {
                userId: this.decodedToken.sub,
                email: this.decodedToken.email,
                name: this.decodedToken.name,
                groups: this.decodedToken.groups || []
            };
            
            console.log(`✅ JWT Permissions loaded:`);
            console.log(`   - User: ${this.userInfo.email}`);
            console.log(`   - App Permissions: ${this.appPermissions.length}`);
            console.log(`   - Module Permissions: ${this.modulePermissions.length}`);
            console.log(`   - Groups: ${this.userInfo.groups.join(', ')}`);
            
            return true;
        } catch (error) {
            console.error('❌ Error initializing JWT Permissions:', error);
            return false;
        }
    }

    /**
     * Decode JWT token (without validation - just reading)
     * Note: This is safe because the token was already validated by the backend
     */
    decodeJWT(token) {
        try {
            // JWT structure: header.payload.signature
            const parts = token.split('.');
            if (parts.length !== 3) {
                throw new Error('Invalid JWT format');
            }
            
            // Decode payload (base64url)
            const payload = parts[1];
            const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(
                atob(base64)
                    .split('')
                    .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
                    .join('')
            );
            
            return JSON.parse(jsonPayload);
        } catch (error) {
            console.error('Error decoding JWT:', error);
            return null;
        }
    }

    /**
     * Check if token is expired
     */
    isTokenExpired() {
        if (!this.decodedToken || !this.decodedToken.exp) {
            return true;
        }
        
        const now = Math.floor(Date.now() / 1000);
        return now >= this.decodedToken.exp;
    }

    /**
     * Get user information
     */
    getUserInfo() {
        return this.userInfo;
    }

    /**
     * Get all application permissions
     */
    getAppPermissions() {
        return this.appPermissions;
    }

    /**
     * Get all module permissions
     */
    getModulePermissions() {
        return this.modulePermissions;
    }

    /**
     * Check if user has permission for a specific application
     */
    hasAppPermission(appId, minLevel = 0) {
        return this.appPermissions.some(perm => 
            perm.app_id === appId && perm.permission_level >= minLevel
        );
    }

    /**
     * Check if user has permission for a specific application by name
     */
    hasAppPermissionByName(appName, minLevel = 0) {
        return this.appPermissions.some(perm => 
            perm.app_name === appName && perm.permission_level >= minLevel
        );
    }

    /**
     * Get permission level for a specific application
     */
    getAppPermissionLevel(appId) {
        const perm = this.appPermissions.find(p => p.app_id === appId);
        return perm ? perm.permission_level : 0;
    }

    /**
     * Check if user has permission for a specific module
     */
    hasModulePermission(moduleId, minLevel = 0) {
        return this.modulePermissions.some(perm => 
            perm.module_id === moduleId && perm.permission_level >= minLevel
        );
    }

    /**
     * Check if user has permission for a specific module by name
     */
    hasModulePermissionByName(appId, moduleName, minLevel = 0) {
        return this.modulePermissions.some(perm => 
            perm.app_id === appId && 
            perm.module_name === moduleName && 
            perm.permission_level >= minLevel
        );
    }

    /**
     * Get permission level for a specific module
     */
    getModulePermissionLevel(moduleId) {
        const perm = this.modulePermissions.find(p => p.module_id === moduleId);
        return perm ? perm.permission_level : 0;
    }

    /**
     * Check if user is admin (has admin permission for identity-mgmt app)
     */
    isAdmin() {
        const identityMgmtAppId = 'e61e1af9-8992-4bdf-be65-9cad86f34da0';
        return this.appPermissions.some(perm => 
            perm.app_id === identityMgmtAppId && 
            perm.permission_type === 'admin' &&
            perm.permission_level >= 100
        );
    }

    /**
     * Check if user is in a specific group
     */
    isInGroup(groupName) {
        return this.userInfo.groups.includes(groupName);
    }

    /**
     * Get all permissions in a unified format (for display)
     */
    getAllPermissions() {
        const permissions = [];
        
        // Add application permissions
        this.appPermissions.forEach(perm => {
            permissions.push({
                scope: 'application',
                resource_id: perm.app_id,
                resource_name: perm.app_name,
                permission_type: perm.permission_type,
                permission_level: perm.permission_level,
                status: 'active',
                is_active: true,
                user_id: this.userInfo.userId,
                email: this.userInfo.email
            });
        });
        
        // Add module permissions
        this.modulePermissions.forEach(perm => {
            permissions.push({
                scope: 'module',
                resource_id: perm.module_id,
                resource_name: perm.module_name,
                parent_application_id: perm.app_id,
                parent_application_name: perm.app_name,
                permission_type: perm.permission_type,
                permission_level: perm.permission_level,
                status: 'active',
                is_active: true,
                user_id: this.userInfo.userId,
                email: this.userInfo.email
            });
        });
        
        return permissions;
    }

    /**
     * Display permissions in console (for debugging)
     */
    logPermissions() {
        console.group('🔐 JWT Permissions');
        console.log('User:', this.userInfo);
        console.log('Application Permissions:', this.appPermissions);
        console.log('Module Permissions:', this.modulePermissions);
        console.groupEnd();
    }

    /**
     * Check if user can perform an action based on permission level
     * Permission levels:
     * - 0-24: No access
     * - 25-49: Viewer (read-only)
     * - 50-74: User (read + limited write)
     * - 75-99: Power User (read + write)
     * - 100: Admin (full access)
     */
    canPerformAction(appId, action) {
        const level = this.getAppPermissionLevel(appId);
        
        const actionLevels = {
            'view': 25,
            'read': 25,
            'create': 50,
            'edit': 50,
            'update': 50,
            'delete': 75,
            'admin': 100,
            'manage': 100
        };
        
        const requiredLevel = actionLevels[action.toLowerCase()] || 0;
        return level >= requiredLevel;
    }

    /**
     * Get permission summary for display
     */
    getPermissionSummary() {
        return {
            totalPermissions: this.appPermissions.length + this.modulePermissions.length,
            appPermissions: this.appPermissions.length,
            modulePermissions: this.modulePermissions.length,
            isAdmin: this.isAdmin(),
            groups: this.userInfo.groups,
            applications: this.appPermissions.map(p => ({
                name: p.app_name,
                type: p.permission_type,
                level: p.permission_level
            }))
        };
    }
}

// Create global instance
window.jwtPermissions = new JWTPermissionsManager();

// Initialize on load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.jwtPermissions.init();
    });
} else {
    window.jwtPermissions.init();
}

console.log('✅ JWT Permissions Manager loaded');