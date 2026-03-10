/**
 * Authentication Guard
 * ====================
 * Protects dashboard pages by checking for valid Cognito authentication
 */

(async function() {
    'use strict';
    
    console.log('🔒 Auth Guard: Checking Cognito authentication...');
    
    // Check if user is authenticated with Cognito
    async function checkAuth() {
        try {
            // Try to get current Cognito session
            const session = await Auth.currentSession();
            const idToken = session.getIdToken();
            const user = await Auth.currentAuthenticatedUser();
            
            console.log('✅ Auth Guard: User is authenticated with Cognito');
            console.log('👤 User:', user.username);
            
            // idToken might be a function or object, handle both cases
            const payload = typeof idToken.getJwtToken === 'function' 
                ? JSON.parse(atob(idToken.getJwtToken().split('.')[1]))
                : idToken.payload;
            
            if (payload && payload.email) {
                console.log('📧 Email:', payload.email);
            }
            
            return true;
        } catch (error) {
            console.warn('⚠️ Auth Guard: No valid Cognito session found');
            console.error('Auth error:', error);
            redirectToLogin();
            return false;
        }
    }
    
    // Redirect to login page
    function redirectToLogin() {
        console.log('🔄 Auth Guard: Redirecting to login...');
        const loginUrl = window.location.origin + '/login.html';
        window.location.href = loginUrl;
    }
    
    // Run auth check immediately
    const isAuthenticated = await checkAuth();
    if (!isAuthenticated) {
        // Stop page execution if not authenticated
        throw new Error('Authentication required');
    }
    
    // Optional: Check auth periodically (every 5 minutes)
    setInterval(async function() {
        try {
            await Auth.currentSession();
        } catch (error) {
            console.warn('⚠️ Auth Guard: Session expired during use');
            redirectToLogin();
        }
    }, 300000); // 5 minutes
    
})();

console.log('✅ Auth Guard loaded');
