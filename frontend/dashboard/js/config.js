/**
 * Identity Manager Dashboard - Configuration
 * ==========================================
 * Configuration settings for the dashboard
 */

const API_CONFIG = {
    // Lambda Function URL
    endpoint: 'https://vgrajswesgyujgxpw5g65tw5py0kihum.lambda-url.eu-west-1.on.aws/',
    
    // Request timeout (30 seconds)
    timeout: 30000,
    
    // Retry configuration
    maxRetries: 3,
    retryDelay: 1000,
    
    // Polling interval for auto-refresh (5 minutes)
    refreshInterval: 5 * 60 * 1000
};

// Dashboard configuration
const DASHBOARD_CONFIG = {
    // Default pagination
    defaultPageSize: 50,
    
    // Auto-refresh enabled
    autoRefresh: false,
    
    // Date format
    dateFormat: 'YYYY-MM-DD HH:mm:ss',
    
    // Theme colors (matching AWS design)
    colors: {
        primary: '#319795',
        secondary: '#2c7a7b',
        success: '#38b2ac',
        warning: '#ed8936',
        error: '#e53e3e',
        info: '#4299e1'
    }
};

// Export for use in other modules
window.API_CONFIG = API_CONFIG;
window.DASHBOARD_CONFIG = DASHBOARD_CONFIG;

console.log('✅ Configuration loaded');
