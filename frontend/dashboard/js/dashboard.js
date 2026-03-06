/**
 * Identity Manager Dashboard - Main Logic
 * ========================================
 * Dashboard functionality and UI interactions
 */

// Global state
let dashboardState = {
    users: [],
    tokens: [],
    profiles: [],
    groups: [],
    currentTab: 'users-tab',
    selectedUser: null,
    selectedToken: null
};

// ============================================================================
// INITIALIZATION
// ============================================================================

async function initDashboard() {
    console.log('🚀 Initializing dashboard...');
    
    // Test API connection
    updateConnectionStatus('connecting');
    const connected = await api.testConnection();
    
    if (connected) {
        updateConnectionStatus('connected');
        console.log('✅ Connected to API');
        
        // Load initial data
        await loadDashboardData();
    } else {
        updateConnectionStatus('disconnected');
        console.error('❌ Failed to connect to API');
        showAlert('error', 'Failed to connect to API. Please check your connection.');
    }
}

async function loadDashboardData() {
    try {
        // Load data for current tab
        switch (dashboardState.currentTab) {
            case 'users-tab':
                await loadUsers();
                break;
            case 'tokens-tab':
                await loadTokens();
                break;
            case 'profiles-tab':
                await loadProfiles();
                break;
            case 'groups-tab':
                await loadGroups();
                break;
            case 'permissions-tab':
                if (typeof loadAllPermissions === 'function') {
                    await loadAllPermissions();
                }
                break;
        }
        
        // Load statistics
        await loadStatistics();
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        showAlert('error', `Error loading data: ${error.message}`);
    }
}

// ============================================================================
// CONNECTION STATUS
// ============================================================================

function updateConnectionStatus(status) {
    const statusEl = document.getElementById('connection-status');
    
    statusEl.classList.remove('connected', 'disconnected', 'connecting');
    
    switch (status) {
        case 'connected':
            statusEl.classList.add('connected');
            statusEl.innerHTML = '🟢 Connected to API';
            break;
        case 'disconnected':
            statusEl.classList.add('disconnected');
            statusEl.innerHTML = '🔴 Disconnected from API';
            break;
        case 'connecting':
            statusEl.classList.add('disconnected');
            statusEl.innerHTML = '🟡 Connecting...';
            break;
    }
}

// ============================================================================
// TAB NAVIGATION
// ============================================================================

function showTab(tabId) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active class from all buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(tabId).classList.add('active');
    
    // Add active class to clicked button
    event.target.closest('.tab-button').classList.add('active');
    
    // Update state
    dashboardState.currentTab = tabId;
    
    // Initialize Proxy Usage tab if selected
    if (tabId === 'proxy-usage-tab' && typeof initProxyUsage === 'function') {
        initProxyUsage();
    } else if (tabId === 'user-quotas-tab' && typeof loadUserQuotas === 'function') {
        // Load User Quotas data
        loadUserQuotas();
    } else {
        // Load data for other tabs
        loadDashboardData();
    }
}

// ============================================================================
// STATISTICS
// ============================================================================

async function loadStatistics() {
    try {
        const [usersData, tokensData, profilesData, groupsData] = await Promise.all([
            api.listUsers(),
            api.listTokens({ status: 'active' }),
            api.listProfiles({ is_active: true }),
            api.listGroups()
        ]);
        
        document.getElementById('total-users').textContent = usersData.users?.length || 0;
        document.getElementById('active-tokens').textContent = tokensData.tokens?.length || 0;
        document.getElementById('active-profiles').textContent = profilesData.profiles?.length || 0;
        document.getElementById('total-groups').textContent = groupsData.groups?.length || 0;
        
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

// ============================================================================
// USERS MANAGEMENT
// ============================================================================

async function loadUsers() {
    try {
        const data = await api.listUsers();
        dashboardState.users = data.users || [];
        
        // Initialize pagination data
        usersPagination.allData = dashboardState.users;
        usersPagination.filteredData = dashboardState.users;
        usersPagination.currentPage = 1;
        
        // Render with pagination
        renderUsersPaginatedTable();
        
    } catch (error) {
        console.error('Error loading users:', error);
        showAlert('error', `Error loading users: ${error.message}`);
    }
}

function renderUsersTable(users) {
    const tbody = document.querySelector('#users-table tbody');
    
    if (!users || users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">No users found</td></tr>';
        return;
    }
    
    tbody.innerHTML = users.map(user => {
        // Determine auto_regenerate_tokens status
        const autoGenerate = user.auto_regenerate_tokens !== undefined ? user.auto_regenerate_tokens : true;
        const autoGenerateIcon = autoGenerate 
            ? '<span style="color: #28a745; font-size: 1.2em;" title="Auto-regenerate enabled">✓</span>'
            : '<span style="color: #dc3545; font-size: 1.2em;" title="Auto-regenerate disabled">✗</span>';
        
        return `
        <tr>
            <td><code>${user.user_id}</code></td>
            <td>${user.email}</td>
            <td>${user.person || '-'}</td>
            <td><span class="status-badge status-${user.status.toLowerCase()}">${user.status}</span></td>
            <td>${user.groups?.join(', ') || '-'}</td>
            <td style="text-align: center;">${autoGenerateIcon}</td>
            <td>${formatDate(user.created_date)}</td>
            <td>
                <button class="btn-action btn-danger" onclick="confirmDeleteUser('${user.user_id}', '${user.email}')" title="Delete User">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width: 16px; height: 16px;">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                    </svg>
                </button>
            </td>
        </tr>
        `;
    }).join('');
}

function showCreateUserModal() {
    // Load groups for dropdown
    loadGroupsForDropdown();
    
    document.getElementById('create-user-modal').classList.add('show');
    document.getElementById('create-user-form').reset();
}

function closeCreateUserModal() {
    document.getElementById('create-user-modal').classList.remove('show');
}

async function loadGroupsForDropdown() {
    try {
        const data = await api.listGroups();
        const select = document.getElementById('user-group');
        
        select.innerHTML = '<option value="">Select a group...</option>' +
            data.groups.map(g => `<option value="${g.group_name}">${g.group_name}</option>`).join('');
            
    } catch (error) {
        console.error('Error loading groups:', error);
    }
}

// Handle create user form submission
document.getElementById('create-user-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const email = document.getElementById('user-email').value;
    const person = document.getElementById('user-person').value;
    const group = document.getElementById('user-group').value;
    const password = document.getElementById('user-password').value || null;
    const sendEmail = document.getElementById('user-send-email').checked;
    const autoRegenerate = document.getElementById('user-auto-regenerate').checked;
    
    // Validate password if provided
    if (password) {
        const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*_\-])[A-Za-z\d!@#$%^&*_\-]{8,}$/;
        if (!passwordRegex.test(password)) {
            showAlert('error', 'Password must be at least 8 characters and contain: uppercase, lowercase, number, and special character (!@#$%^&*_-)');
            return;
        }
    }
    
    try {
        await api.createUser(email, person, group, password, sendEmail, autoRegenerate);
        showAlert('success', `User ${email} created successfully!`);
        closeCreateUserModal();
        loadUsers();
        loadStatistics();
    } catch (error) {
        showAlert('error', `Error creating user: ${error.message}`);
    }
});

function confirmDeleteUser(userId, email) {
    if (confirm(`Are you sure you want to delete user ${email}?\n\nThis will also delete all associated tokens and data.`)) {
        deleteUser(userId);
    }
}

async function deleteUser(userId) {
    try {
        await api.deleteUser(userId);
        showAlert('success', 'User deleted successfully!');
        loadUsers();
        loadStatistics();
    } catch (error) {
        showAlert('error', `Error deleting user: ${error.message}`);
    }
}

// ============================================================================
// TOKENS MANAGEMENT
// ============================================================================

async function loadTokens() {
    try {
        const data = await api.listTokens({ status: 'all' });
        dashboardState.tokens = data.tokens || [];
        
        // Initialize pagination data
        tokensPagination.allData = dashboardState.tokens;
        tokensPagination.filteredData = dashboardState.tokens;
        tokensPagination.currentPage = 1;
        
        // Render with pagination
        renderTokensPaginatedTable();
        
    } catch (error) {
        console.error('Error loading tokens:', error);
        showAlert('error', `Error loading tokens: ${error.message}`);
    }
}

function renderTokensTable(tokens) {
    const tbody = document.querySelector('#tokens-table tbody');
    
    if (!tokens || tokens.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">No tokens found</td></tr>';
        return;
    }
    
    tbody.innerHTML = tokens.map(token => `
        <tr>
            <td><code>${token.token_id ? token.token_id.substring(0, 8) + '...' : '-'}</code></td>
            <td><code>${token.user_id ? token.user_id.substring(0, 8) + '...' : '-'}</code></td>
            <td>${token.email || '-'}</td>
            <td>${token.profile_name || '-'}</td>
            <td>${formatDate(token.created_at)}</td>
            <td>${formatDate(token.expires_at)}</td>
            <td><span class="status-badge status-${token.status}">${token.status.charAt(0).toUpperCase() + token.status.slice(1)}</span></td>
            <td>
                <button class="btn-action btn-info" onclick="viewToken('${token.token_id}')" title="View Details">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width: 16px; height: 16px;">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                        <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                </button>
                ${token.status === 'revoked' ? `
                <button class="btn-action btn-info" onclick="confirmRestoreToken('${token.token_id}')" title="Restore Token">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width: 16px; height: 16px;">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M9 15L3 9m0 0l6-6M3 9h12a6 6 0 010 12h-3" />
                    </svg>
                </button>
                ` : `
                <button class="btn-action btn-warning" onclick="confirmRevokeToken('${token.token_id}')" title="Revoke Token">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width: 16px; height: 16px;">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                    </svg>
                </button>
                `}
            </td>
        </tr>
    `).join('');
}

async function showCreateTokenModal() {
    // Load users and profiles for dropdowns
    await Promise.all([
        loadUsersForDropdown(),
        loadProfilesForDropdown()
    ]);
    
    document.getElementById('create-token-modal').classList.add('show');
    document.getElementById('create-token-form').reset();
    document.getElementById('token-result').style.display = 'none';
    document.getElementById('create-token-form').style.display = 'block';
}

function closeCreateTokenModal() {
    document.getElementById('create-token-modal').classList.remove('show');
}

async function loadUsersForDropdown() {
    try {
        const data = await api.listUsers();
        const select = document.getElementById('token-user');
        
        select.innerHTML = '<option value="">Select a user...</option>' +
            data.users.map(u => `<option value="${u.user_id}">${u.email} (${u.person || 'No name'})</option>`).join('');
            
    } catch (error) {
        console.error('Error loading users:', error);
    }
}

async function loadProfilesForDropdown() {
    try {
        const data = await api.listProfiles({ is_active: true });
        const select = document.getElementById('token-profile');
        
        select.innerHTML = '<option value="">Select a profile...</option>' +
            data.profiles.map(p => `<option value="${p.profile_id}">${p.profile_name} (${p.model_id})</option>`).join('');
            
    } catch (error) {
        console.error('Error loading profiles:', error);
    }
}

// Handle create token form submission
document.getElementById('create-token-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const userId = document.getElementById('token-user').value;
    const profileId = document.getElementById('token-profile').value;
    const validity = document.getElementById('token-validity').value;
    const sendEmail = document.getElementById('token-send-email').checked;

    try {
        const result = await api.createToken(userId, profileId, validity, sendEmail);
        
        // Show token result
        document.getElementById('create-token-form').style.display = 'none';
        document.getElementById('token-result').style.display = 'block';
        document.getElementById('token-jwt').value = result.token.jwt;
        document.getElementById('token-id-display').textContent = result.token.token_id;
        document.getElementById('token-expires-display').textContent = result.token.expires_at;
        document.getElementById('token-validity-display').textContent = result.token.validity_days;
        
    } catch (error) {
        showAlert('error', `Error creating token: ${error.message}`);
    }
});

function copyToken() {
    const textarea = document.getElementById('token-jwt');
    textarea.select();
    document.execCommand('copy');
    showAlert('success', 'Token copied to clipboard!');
}

function viewToken(tokenId) {
    const token = dashboardState.tokens.find(t => t.token_id === tokenId);
    if (!token) return;
    
    document.getElementById('view-token-id').textContent = token.token_id;
    document.getElementById('view-token-jti').textContent = token.jti;
    document.getElementById('view-token-user-id').textContent = token.user_id;
    document.getElementById('view-token-email').textContent = token.email;
    document.getElementById('view-token-profile').textContent = token.profile_name || '-';
    document.getElementById('view-token-created').textContent = formatDate(token.created_at);
    document.getElementById('view-token-expires').textContent = formatDate(token.expires_at);
    document.getElementById('view-token-status').innerHTML = `<span class="status-badge status-${token.status}">${token.status.charAt(0).toUpperCase() + token.status.slice(1)}</span>`;
    
    document.getElementById('view-token-modal').classList.add('show');
}

function closeViewTokenModal() {
    document.getElementById('view-token-modal').classList.remove('show');
}

function confirmRevokeToken(tokenId) {
    if (confirm('Are you sure you want to revoke this token?')) {
        revokeToken(tokenId);
    }
}

async function revokeToken(tokenId) {
    try {
        await api.revokeToken(tokenId);
        showAlert('success', 'Token revoked successfully!');
        loadTokens();
        loadStatistics();
    } catch (error) {
        showAlert('error', `Error revoking token: ${error.message}`);
    }
}

function confirmRestoreToken(tokenId) {
    if (confirm('Are you sure you want to restore this token?\n\nThis will reactivate the token.')) {
        restoreToken(tokenId);
    }
}

async function restoreToken(tokenId) {
    try {
        await api.request('restore_token', { token_id: tokenId });
        showAlert('success', 'Token restored successfully!');
        loadTokens();
        loadStatistics();
    } catch (error) {
        showAlert('error', `Error restoring token: ${error.message}`);
    }
}

// ============================================================================
// PROFILES MANAGEMENT
// ============================================================================

async function loadProfiles() {
    try {
        const data = await api.listProfiles();
        dashboardState.profiles = data.profiles || [];
        
        renderProfilesTable(dashboardState.profiles);
        
    } catch (error) {
        console.error('Error loading profiles:', error);
        showAlert('error', `Error loading profiles: ${error.message}`);
    }
}

function renderProfilesTable(profiles) {
    const tbody = document.querySelector('#profiles-table tbody');
    
    if (!profiles || profiles.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">No profiles found</td></tr>';
        return;
    }
    
    tbody.innerHTML = profiles.map(profile => `
        <tr>
            <td><code>${profile.profile_id}</code></td>
            <td>${profile.profile_name}</td>
            <td>${profile.application_name || '-'}</td>
            <td><code>${profile.model_id}</code></td>
            <td>${profile.cognito_group_name || '-'}</td>
            <td><span class="status-badge status-${profile.is_active ? 'active' : 'inactive'}">${profile.is_active ? 'Active' : 'Inactive'}</span></td>
            <td>${formatDate(profile.created_at)}</td>
        </tr>
    `).join('');
}

// ============================================================================
// GROUPS MANAGEMENT
// ============================================================================

async function loadGroups() {
    try {
        const data = await api.listGroups();
        dashboardState.groups = data.groups || [];
        
        renderGroupsTable(dashboardState.groups);
        
    } catch (error) {
        console.error('Error loading groups:', error);
        showAlert('error', `Error loading groups: ${error.message}`);
    }
}

function renderGroupsTable(groups) {
    const tbody = document.querySelector('#groups-table tbody');
    
    if (!groups || groups.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center;">No groups found</td></tr>';
        return;
    }
    
    tbody.innerHTML = groups.map(group => `
        <tr>
            <td><strong>${group.group_name}</strong></td>
            <td>${group.description || '-'}</td>
            <td>${group.precedence || '-'}</td>
            <td>${group.user_count || 0}</td>
        </tr>
    `).join('');
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function formatDate(dateString) {
    if (!dateString) return '-';
    return moment(dateString).format(DASHBOARD_CONFIG.dateFormat);
}

function showAlert(type, message) {
    // Create alert element
    const alert = document.createElement('div');
    alert.className = `alert ${type}`;
    alert.innerHTML = `<strong>${type === 'success' ? '✓' : '✗'}</strong> ${message}`;
    alert.style.position = 'fixed';
    alert.style.top = '100px';
    alert.style.right = '20px';
    alert.style.zIndex = '9999';
    alert.style.minWidth = '300px';
    alert.style.animation = 'slideIn 0.3s ease';
    
    document.body.appendChild(alert);
    
    // Remove after 5 seconds
    setTimeout(() => {
        alert.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => alert.remove(), 300);
    }, 5000);
}

function logout() {
    // Show logout confirmation modal
    document.getElementById('logout-modal').style.display = 'flex';
}

function closeLogoutModal() {
    document.getElementById('logout-modal').style.display = 'none';
}

function confirmLogout() {
    // Clear authentication token
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_data');
    
    // Redirect to login page
    window.location.href = 'login.html';
}

// ============================================================================
// PASSWORD VISIBILITY TOGGLE
// ============================================================================

function togglePasswordVisibility() {
    const passwordInput = document.getElementById('user-password');
    const eyeIcon = document.getElementById('eye-icon');
    
    if (passwordInput.type === 'password') {
        // Show password
        passwordInput.type = 'text';
        // Change icon to "eye-slash" (crossed eye)
        eyeIcon.innerHTML = `
            <path stroke-linecap="round" stroke-linejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
        `;
    } else {
        // Hide password
        passwordInput.type = 'password';
        // Change icon back to "eye"
        eyeIcon.innerHTML = `
            <path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        `;
    }
}

// ============================================================================
// MODAL CLOSE ON OUTSIDE CLICK
// ============================================================================

window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.classList.remove('show');
    }
};

// ============================================================================
// PAGINATION AND FILTERING
// ============================================================================

// Users pagination state
let usersPagination = {
    currentPage: 1,
    pageSize: 10,
    filteredData: [],
    allData: []
};

// Tokens pagination state
let tokensPagination = {
    currentPage: 1,
    pageSize: 10,
    filteredData: [],
    allData: []
};

// Permissions pagination state
let permissionsPagination = {
    currentPage: 1,
    pageSize: 10,
    filteredData: [],
    allData: []
};

// ============================================================================
// USERS TABLE FILTERING AND PAGINATION
// ============================================================================

function filterUsersTable() {
    const searchTerm = document.getElementById('users-search').value.toLowerCase();
    
    if (!searchTerm) {
        usersPagination.filteredData = usersPagination.allData;
    } else {
        usersPagination.filteredData = usersPagination.allData.filter(user => {
            return (
                user.email?.toLowerCase().includes(searchTerm) ||
                user.person?.toLowerCase().includes(searchTerm) ||
                user.user_id?.toLowerCase().includes(searchTerm) ||
                user.groups?.some(g => g.toLowerCase().includes(searchTerm)) ||
                user.status?.toLowerCase().includes(searchTerm)
            );
        });
    }
    
    usersPagination.currentPage = 1;
    renderUsersPaginatedTable();
}

function renderUsersPaginatedTable() {
    const tbody = document.querySelector('#users-table tbody');
    const start = (usersPagination.currentPage - 1) * usersPagination.pageSize;
    const end = start + usersPagination.pageSize;
    const pageData = usersPagination.filteredData.slice(start, end);
    
    if (pageData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">No users found</td></tr>';
        updateUsersPaginationControls();
        return;
    }
    
    tbody.innerHTML = pageData.map(user => {
        const autoGenerate = user.auto_regenerate_tokens !== undefined ? user.auto_regenerate_tokens : true;
        const autoGenerateIcon = autoGenerate 
            ? '<span style="color: #28a745; font-size: 1.2em;" title="Auto-regenerate enabled">✓</span>'
            : '<span style="color: #dc3545; font-size: 1.2em;" title="Auto-regenerate disabled">✗</span>';
        
        return `
        <tr>
            <td><code>${user.user_id}</code></td>
            <td>${user.email}</td>
            <td>${user.person || '-'}</td>
            <td><span class="status-badge status-${user.status.toLowerCase()}">${user.status}</span></td>
            <td>${user.groups?.join(', ') || '-'}</td>
            <td style="text-align: center;">${autoGenerateIcon}</td>
            <td>${formatDate(user.created_date)}</td>
            <td>
                <button class="btn-action btn-danger" onclick="confirmDeleteUser('${user.user_id}', '${user.email}')" title="Delete User">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width: 16px; height: 16px;">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                    </svg>
                </button>
            </td>
        </tr>
        `;
    }).join('');
    
    updateUsersPaginationControls();
}

function updateUsersPaginationControls() {
    const total = usersPagination.filteredData.length;
    const totalPages = Math.ceil(total / usersPagination.pageSize);
    const start = total === 0 ? 0 : (usersPagination.currentPage - 1) * usersPagination.pageSize + 1;
    const end = Math.min(usersPagination.currentPage * usersPagination.pageSize, total);
    
    document.getElementById('users-pagination-info').textContent = `Showing ${start}-${end} of ${total} users`;
    document.getElementById('users-current-page').textContent = usersPagination.currentPage;
    document.getElementById('users-total-pages').textContent = totalPages || 1;
    document.getElementById('users-prev-page').disabled = usersPagination.currentPage === 1;
    document.getElementById('users-next-page').disabled = usersPagination.currentPage >= totalPages;
}

function previousUsersPage() {
    if (usersPagination.currentPage > 1) {
        usersPagination.currentPage--;
        renderUsersPaginatedTable();
    }
}

function nextUsersPage() {
    const totalPages = Math.ceil(usersPagination.filteredData.length / usersPagination.pageSize);
    if (usersPagination.currentPage < totalPages) {
        usersPagination.currentPage++;
        renderUsersPaginatedTable();
    }
}

// ============================================================================
// TOKENS TABLE FILTERING AND PAGINATION
// ============================================================================

function filterTokensTable() {
    const searchTerm = document.getElementById('tokens-search').value.toLowerCase();
    
    if (!searchTerm) {
        tokensPagination.filteredData = tokensPagination.allData;
    } else {
        tokensPagination.filteredData = tokensPagination.allData.filter(token => {
            return (
                token.email?.toLowerCase().includes(searchTerm) ||
                token.token_id?.toLowerCase().includes(searchTerm) ||
                token.user_id?.toLowerCase().includes(searchTerm) ||
                token.profile_name?.toLowerCase().includes(searchTerm) ||
                token.status?.toLowerCase().includes(searchTerm)
            );
        });
    }
    
    tokensPagination.currentPage = 1;
    renderTokensPaginatedTable();
}

function renderTokensPaginatedTable() {
    const tbody = document.querySelector('#tokens-table tbody');
    const start = (tokensPagination.currentPage - 1) * tokensPagination.pageSize;
    const end = start + tokensPagination.pageSize;
    const pageData = tokensPagination.filteredData.slice(start, end);
    
    if (pageData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">No tokens found</td></tr>';
        updateTokensPaginationControls();
        return;
    }
    
    tbody.innerHTML = pageData.map(token => {
        // Determinar si el token fue regenerado o es una regeneración
        const isRegenerated = token.regenerated_at != null; // Token viejo que fue regenerado
        const isRegeneratedFrom = token.regenerated_from_jti != null; // Token nuevo que reemplazó a otro
        
        let statusBadge = `<span class="status-badge status-${token.status}">${token.status.charAt(0).toUpperCase() + token.status.slice(1)}</span>`;
        
        // Añadir badge adicional si fue regenerado
        if (isRegenerated) {
            statusBadge += ' <span class="status-badge" style="background-color: #6c757d; font-size: 0.75em;" title="This token was regenerated on ' + formatDate(token.regenerated_at) + '">🔄 Regenerated</span>';
        }
        
        // Añadir badge si es una regeneración de otro token
        if (isRegeneratedFrom) {
            statusBadge += ' <span class="status-badge" style="background-color: #17a2b8; font-size: 0.75em;" title="Auto-generated from expired token">✨ Auto-generated</span>';
        }
        
        return `
        <tr>
            <td><code>${token.token_id ? token.token_id.substring(0, 8) + '...' : '-'}</code></td>
            <td><code>${token.user_id ? token.user_id.substring(0, 8) + '...' : '-'}</code></td>
            <td>${token.email || '-'}</td>
            <td>${token.profile_name || '-'}</td>
            <td>${formatDate(token.created_at)}</td>
            <td>${formatDate(token.expires_at)}</td>
            <td>${token.last_used_at ? formatDate(token.last_used_at) : '<span style="color: #999;">Never</span>'}</td>
            <td>${statusBadge}</td>
            <td>
                <button class="btn-action btn-info" onclick="viewToken('${token.token_id}')" title="View Details">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width: 16px; height: 16px;">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                        <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                </button>
                ${token.status === 'revoked' ? `
                <button class="btn-action btn-info" onclick="confirmRestoreToken('${token.token_id}')" title="Restore Token">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width: 16px; height: 16px;">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M9 15L3 9m0 0l6-6M3 9h12a6 6 0 010 12h-3" />
                    </svg>
                </button>
                ` : `
                <button class="btn-action btn-warning" onclick="confirmRevokeToken('${token.token_id}')" title="Revoke Token">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width: 16px; height: 16px;">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                    </svg>
                </button>
                `}
            </td>
        </tr>
    `;
    }).join('');

    updateTokensPaginationControls();
}

function updateTokensPaginationControls() {
    const total = tokensPagination.filteredData.length;
    const totalPages = Math.ceil(total / tokensPagination.pageSize);
    const start = total === 0 ? 0 : (tokensPagination.currentPage - 1) * tokensPagination.pageSize + 1;
    const end = Math.min(tokensPagination.currentPage * tokensPagination.pageSize, total);
    
    document.getElementById('tokens-pagination-info').textContent = `Showing ${start}-${end} of ${total} tokens`;
    document.getElementById('tokens-current-page').textContent = tokensPagination.currentPage;
    document.getElementById('tokens-total-pages').textContent = totalPages || 1;
    document.getElementById('tokens-prev-page').disabled = tokensPagination.currentPage === 1;
    document.getElementById('tokens-next-page').disabled = tokensPagination.currentPage >= totalPages;
}

function previousTokensPage() {
    if (tokensPagination.currentPage > 1) {
        tokensPagination.currentPage--;
        renderTokensPaginatedTable();
    }
}

function nextTokensPage() {
    const totalPages = Math.ceil(tokensPagination.filteredData.length / tokensPagination.pageSize);
    if (tokensPagination.currentPage < totalPages) {
        tokensPagination.currentPage++;
        renderTokensPaginatedTable();
    }
}

// ============================================================================
// PERMISSIONS TABLE FILTERING AND PAGINATION
// ============================================================================

function filterPermissionsTable() {
    const searchTerm = document.getElementById('permissions-search').value.toLowerCase();
    
    if (!searchTerm) {
        permissionsPagination.filteredData = permissionsPagination.allData;
    } else {
        permissionsPagination.filteredData = permissionsPagination.allData.filter(perm => {
            return (
                perm.user_id?.toLowerCase().includes(searchTerm) ||
                perm.email?.toLowerCase().includes(searchTerm) ||
                perm.scope?.toLowerCase().includes(searchTerm) ||
                perm.resource_name?.toLowerCase().includes(searchTerm) ||
                perm.permission_type?.toLowerCase().includes(searchTerm) ||
                perm.status?.toLowerCase().includes(searchTerm)
            );
        });
    }
    
    permissionsPagination.currentPage = 1;
    renderPermissionsPaginatedTable();
}

function renderPermissionsPaginatedTable() {
    const tbody = document.querySelector('#permissions-table tbody');
    const start = (permissionsPagination.currentPage - 1) * permissionsPagination.pageSize;
    const end = start + permissionsPagination.pageSize;
    const pageData = permissionsPagination.filteredData.slice(start, end);
    
    if (pageData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" style="text-align: center;">No permissions found</td></tr>';
        updatePermissionsPaginationControls();
        return;
    }
    
    tbody.innerHTML = pageData.map(perm => {
        const expiresText = perm.expires_at ? formatDate(perm.expires_at) : 'Never';
        const statusText = perm.status.charAt(0).toUpperCase() + perm.status.slice(1);
        
        return `
        <tr>
            <td><code>${perm.user_id ? perm.user_id.substring(0, 8) + '...' : '-'}</code></td>
            <td>${perm.email || '-'}</td>
            <td><span class="status-badge status-${perm.scope}">${perm.scope}</span></td>
            <td>${perm.resource_name || '-'}</td>
            <td>${perm.permission_type || '-'}</td>
            <td>${perm.permission_level || '-'}</td>
            <td>${formatDate(perm.granted_at)}</td>
            <td>${expiresText}</td>
            <td><span class="status-badge status-${perm.status}">${statusText}</span></td>
            <td>
                ${perm.status === 'revoked' ? `
                    <button class="btn-action btn-info" onclick="restorePermission('${perm.permission_id}', '${perm.scope}', '${perm.user_id}', '${perm.resource_id}')" title="Restore Permission">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width: 16px; height: 16px;">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M9 15L3 9m0 0l6-6M3 9h12a6 6 0 010 12h-3" />
                        </svg>
                    </button>
                ` : `
                    <button class="btn-action btn-warning" onclick="revokePermission('${perm.permission_id}', '${perm.scope}', '${perm.user_id}', '${perm.resource_id}')" title="Revoke Permission">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width: 16px; height: 16px;">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                        </svg>
                    </button>
                `}
            </td>
        </tr>
        `;
    }).join('');
    
    updatePermissionsPaginationControls();
}

function updatePermissionsPaginationControls() {
    const total = permissionsPagination.filteredData.length;
    const totalPages = Math.ceil(total / permissionsPagination.pageSize);
    const start = total === 0 ? 0 : (permissionsPagination.currentPage - 1) * permissionsPagination.pageSize + 1;
    const end = Math.min(permissionsPagination.currentPage * permissionsPagination.pageSize, total);
    
    document.getElementById('permissions-pagination-info').textContent = `Showing ${start}-${end} of ${total} permissions`;
    document.getElementById('permissions-current-page').textContent = permissionsPagination.currentPage;
    document.getElementById('permissions-total-pages').textContent = totalPages || 1;
    document.getElementById('permissions-prev-page').disabled = permissionsPagination.currentPage === 1;
    document.getElementById('permissions-next-page').disabled = permissionsPagination.currentPage >= totalPages;
}

function previousPermissionsPage() {
    if (permissionsPagination.currentPage > 1) {
        permissionsPagination.currentPage--;
        renderPermissionsPaginatedTable();
    }
}

function nextPermissionsPage() {
    const totalPages = Math.ceil(permissionsPagination.filteredData.length / permissionsPagination.pageSize);
    if (permissionsPagination.currentPage < totalPages) {
        permissionsPagination.currentPage++;
        renderPermissionsPaginatedTable();
    }
}

console.log('✅ Dashboard logic loaded');
