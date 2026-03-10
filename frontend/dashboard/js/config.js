/**
 * Identity Manager Dashboard - Configuration
 * ==========================================
 * Configuration settings for the dashboard
 */

const API_CONFIG = {
    // API Gateway endpoint (secured with Cognito Authorizer)
    endpoint: 'https://flzqvv3jt4.execute-api.eu-west-1.amazonaws.com/dev',
    
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

// Cognito Configuration
const COGNITO_CONFIG = {
    region: 'eu-west-1',
    userPoolId: 'eu-west-1_UaMIbG9pD',
    userPoolWebClientId: '15b1ub3navqgh0ushcqo2ngfsk',
};

// Wait for Cognito SDK to load
if (typeof AmazonCognitoIdentity === 'undefined') {
    console.error('❌ AmazonCognitoIdentity not loaded! Waiting...');
    // Retry after a short delay
    setTimeout(() => {
        if (typeof AmazonCognitoIdentity !== 'undefined') {
            initializeCognito();
        } else {
            console.error('❌ AmazonCognitoIdentity still not available after delay');
        }
    }, 1000);
} else {
    initializeCognito();
}

function initializeCognito() {
    console.log('🔧 Initializing Cognito...');
    
    // Configure Cognito User Pool
    const poolData = {
        UserPoolId: COGNITO_CONFIG.userPoolId,
        ClientId: COGNITO_CONFIG.userPoolWebClientId
    };

    const userPool = new AmazonCognitoIdentity.CognitoUserPool(poolData);

    // Create Auth wrapper compatible with Amplify API
    window.Auth = {
        currentSession: function() {
            return new Promise((resolve, reject) => {
                const cognitoUser = userPool.getCurrentUser();
                if (!cognitoUser) {
                    reject(new Error('No current user'));
                    return;
                }
                
                cognitoUser.getSession((err, session) => {
                    if (err) {
                        reject(err);
                        return;
                    }
                    
                    if (!session.isValid()) {
                        reject(new Error('Session is not valid'));
                        return;
                    }
                    
                    resolve({
                        getIdToken: () => ({
                            getJwtToken: () => session.getIdToken().getJwtToken()
                        }),
                        getAccessToken: () => ({
                            getJwtToken: () => session.getAccessToken().getJwtToken()
                        })
                    });
                });
            });
        },
        
        currentAuthenticatedUser: function() {
            return new Promise((resolve, reject) => {
                const cognitoUser = userPool.getCurrentUser();
                if (!cognitoUser) {
                    reject(new Error('No current user'));
                    return;
                }
                
                cognitoUser.getSession((err, session) => {
                    if (err) {
                        reject(err);
                        return;
                    }
                    
                    resolve({
                        username: cognitoUser.getUsername(),
                        attributes: session.getIdToken().payload
                    });
                });
            });
        }
    };

    console.log('✅ Cognito configured');
    console.log('✅ window.Auth is now available');
}

// Export for use in other modules
window.API_CONFIG = API_CONFIG;
window.DASHBOARD_CONFIG = DASHBOARD_CONFIG;
window.COGNITO_CONFIG = COGNITO_CONFIG;

console.log('✅ Configuration loaded');
