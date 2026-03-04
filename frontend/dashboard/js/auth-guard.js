/**
 * Authentication Guard
 * ====================
 * Protects dashboard pages by checking for valid authentication token
 */

(function() {
    'use strict';
    
    console.log('🔒 Auth Guard: Checking authentication...');
    
    // Check if user is authenticated
    function checkAuth() {
        const token = localStorage.getItem('auth_token');
        const userData = localStorage.getItem('user_data');
        const expiresAt = localStorage.getItem('token_expires_at');
        
        // If no token, redirect to login
        if (!token || !userData) {
            console.warn('⚠️ Auth Guard: No authentication token found');
            redirectToLogin();
            return false;
        }
        
        // Check if token is expired
        if (expiresAt) {
            const expiryDate = new Date(expiresAt);
            const now = new Date();
            
            if (now >= expiryDate) {
                console.warn('⚠️ Auth Guard: Token has expired');
                clearAuth();
                redirectToLogin();
                return false;
            }
        }
        
        console.log('✅ Auth Guard: User is authenticated');
        return true;
    }
    
    // Clear authentication data
    function clearAuth() {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_data');
        localStorage.removeItem('token_expires_at');
    }
    
    // Redirect to login page
    function redirectToLogin() {
        console.log('🔄 Auth Guard: Redirecting to login...');
        window.location.href = '/frontend/login.html';
    }
    
    // Run auth check immediately
    if (!checkAuth()) {
        // Stop page execution if not authenticated
        throw new Error('Authentication required');
    }
    
    // Optional: Check auth periodically (every 30 seconds)
    setInterval(function() {
        if (!checkAuth()) {
            console.warn('⚠️ Auth Guard: Session expired during use');
        }
    }, 30000); // 30 seconds
    
})();

console.log('✅ Auth Guard loaded');