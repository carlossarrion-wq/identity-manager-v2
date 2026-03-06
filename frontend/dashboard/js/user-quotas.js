// ============================================================================
// USER QUOTAS MANAGEMENT
// ============================================================================

// Global variables for quotas
let quotasData = [];
let filteredQuotasData = [];
let quotasCurrentPage = 1;
const quotasItemsPerPage = 10;

// Selected user for modal operations
let selectedQuotaUser = null;

// ============================================================================
// LOAD USER QUOTAS DATA
// ============================================================================

async function loadUserQuotas() {
    console.log('📊 Loading user quotas data...');
    
    try {
        // Show loading state
        const tbody = document.querySelector('#quotas-table tbody');
        tbody.innerHTML = `
            <tr>
                <td colspan="10" style="text-align: center; padding: 2rem;">
                    <div class="loading-spinner"></div>
                    Loading quota data...
                </td>
            </tr>
        `;
        
        // Get today's date in YYYY-MM-DD format
        const today = new Date().toISOString().split('T')[0];
        
        // Fetch quotas data from API
        const data = await api.getUserQuotasToday();
        
        console.log('🔍 DEBUG: Raw data from API:', data);
        console.log('🔍 DEBUG: Is array?', Array.isArray(data));
        console.log('🔍 DEBUG: Data type:', typeof data);
        console.log('🔍 DEBUG: Data length:', data?.length);
        
        // Ensure data is an array
        quotasData = Array.isArray(data) ? data : [];
        filteredQuotasData = [...quotasData];
        
        console.log('🔍 DEBUG: quotasData after assignment:', quotasData);
        console.log('🔍 DEBUG: quotasData length:', quotasData.length);
        
        // Update summary cards
        updateQuotasSummary();
        
        // Display table
        quotasCurrentPage = 1;
        displayQuotasTable();
        
        console.log(`✅ Loaded ${quotasData.length} user quotas`);
        
    } catch (error) {
        console.error('❌ Error loading quotas:', error);
        
        const tbody = document.querySelector('#quotas-table tbody');
        tbody.innerHTML = `
            <tr>
                <td colspan="10" style="text-align: center; padding: 2rem; color: #e53e3e;">
                    <strong>Error loading quota data</strong><br>
                    <small>${error.message}</small>
                </td>
            </tr>
        `;
        
        showNotification('Failed to load quota data: ' + error.message, 'error');
    }
}

// ============================================================================
// UPDATE SUMMARY CARDS
// ============================================================================

function updateQuotasSummary() {
    // Calculate metrics
    const activeUsers = quotasData.filter(q => q.requests_today > 0).length;
    const blockedUsers = quotasData.filter(q => q.status === 'BLOCKED').length;
    const adminSafeUsers = quotasData.filter(q => q.status === 'ADMIN_SAFE').length;
    
    const totalRequests = quotasData.reduce((sum, q) => sum + (q.requests_today || 0), 0);
    const avgUsage = activeUsers > 0 ? Math.round(totalRequests / activeUsers) : 0;
    
    // Update DOM
    document.getElementById('quotas-active-users').textContent = activeUsers;
    document.getElementById('quotas-blocked-users').textContent = blockedUsers;
    document.getElementById('quotas-admin-safe-users').textContent = adminSafeUsers;
    document.getElementById('quotas-avg-usage').textContent = avgUsage;
}

// ============================================================================
// DISPLAY QUOTAS TABLE
// ============================================================================

function displayQuotasTable() {
    const tbody = document.querySelector('#quotas-table tbody');
    const start = (quotasCurrentPage - 1) * quotasItemsPerPage;
    const end = start + quotasItemsPerPage;
    const pageData = filteredQuotasData.slice(start, end);
    
    if (pageData.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="10" style="text-align: center; padding: 2rem;">
                    No quota data found for today
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = pageData.map(quota => {
        const usagePercent = quota.daily_limit > 0 
            ? Math.round((quota.requests_today / quota.daily_limit) * 100) 
            : 0;
        
        const statusBadge = getStatusBadge(quota.status);
        const usageBar = getUsageBar(usagePercent, quota.status);
        const blockedUntil = quota.blocked_until ? formatDateTime(quota.blocked_until) : '-';
        const actionButtons = getActionButtons(quota);
        
        return `
            <tr>
                <td><code>${quota.cognito_user_id.substring(0, 8)}...</code></td>
                <td>${quota.cognito_email}</td>
                <td>${quota.person || '-'}</td>
                <td>${quota.team || '-'}</td>
                <td style="text-align: right; font-weight: 600;">${quota.requests_today.toLocaleString()}</td>
                <td style="text-align: right;">${quota.daily_limit.toLocaleString()}</td>
                <td style="text-align: center;">
                    ${usageBar}
                </td>
                <td style="text-align: center;">${statusBadge}</td>
                <td style="text-align: center; font-size: 0.85rem;">${blockedUntil}</td>
                <td style="text-align: center;">
                    ${actionButtons}
                </td>
            </tr>
        `;
    }).join('');
    
    updateQuotasPagination();
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function getStatusBadge(status) {
    const badges = {
        'ACTIVE': '<span class="status-badge active">ACTIVE</span>',
        'BLOCKED': '<span class="status-badge revoked">BLOCKED</span>',
        'ADMIN_SAFE': '<span class="status-badge admin-safe">ADMIN SAFE</span>'
    };
    return badges[status] || '<span class="status-badge">UNKNOWN</span>';
}

function getUsageBar(percent, status) {
    let color = '#38a169'; // Green
    if (percent >= 90) color = '#e53e3e'; // Red
    else if (percent >= 75) color = '#dd6b20'; // Orange
    else if (percent >= 50) color = '#d69e2e'; // Yellow
    
    if (status === 'ADMIN_SAFE') {
        color = '#805ad5'; // Purple for admin safe
    }
    
    return `
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <div style="flex: 1; background: #e2e8f0; border-radius: 4px; height: 8px; overflow: hidden;">
                <div style="width: ${Math.min(percent, 100)}%; height: 100%; background: ${color}; transition: width 0.3s;"></div>
            </div>
            <span style="font-weight: 600; min-width: 45px; text-align: right;">${percent}%</span>
        </div>
    `;
}

function getActionButtons(quota) {
    const userId = quota.cognito_user_id;
    const status = quota.status;
    
    let buttons = '<div style="display: flex; gap: 0.5rem; justify-content: center;">';
    
    if (status === 'ACTIVE') {
        // Active users can be blocked or set to admin-safe
        buttons += `
            <button class="btn-action btn-block" onclick="showBlockUserModal('${userId}')" title="Block User">
                🔒 Block
            </button>
            <button class="btn-action btn-admin-safe" onclick="showSetAdminSafeModal('${userId}')" title="Set Admin-Safe">
                🛡️ Protect
            </button>
        `;
    } else if (status === 'BLOCKED') {
        // Blocked users can be unblocked or set to admin-safe
        buttons += `
            <button class="btn-action btn-unblock" onclick="showUnblockUserModal('${userId}')" title="Unblock User">
                🔓 Unblock
            </button>
            <button class="btn-action btn-admin-safe" onclick="showSetAdminSafeModal('${userId}')" title="Set Admin-Safe">
                🛡️ Protect
            </button>
        `;
    } else if (status === 'ADMIN_SAFE') {
        // Admin-safe users can only be unprotected
        buttons += `
            <button class="btn-action btn-unblock" onclick="showUnblockUserModal('${userId}')" title="Remove Protection">
                🔓 Remove Protection
            </button>
        `;
    }
    
    buttons += '</div>';
    return buttons;
}

function formatDateTime(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString('en-GB', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// ============================================================================
// MODAL FUNCTIONS
// ============================================================================

function showBlockUserModal(userId) {
    selectedQuotaUser = quotasData.find(q => q.cognito_user_id === userId);
    if (!selectedQuotaUser) return;
    
    // Set default block until date (24 hours from now)
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const defaultDate = tomorrow.toISOString().slice(0, 16);
    
    document.getElementById('block-user-email').textContent = selectedQuotaUser.cognito_email;
    document.getElementById('block-user-person').textContent = selectedQuotaUser.person || '-';
    document.getElementById('block-user-team').textContent = selectedQuotaUser.team || '-';
    document.getElementById('block-until-datetime').value = defaultDate;
    document.getElementById('block-reason').value = '';
    
    document.getElementById('block-user-modal').style.display = 'flex';
}

function showUnblockUserModal(userId) {
    selectedQuotaUser = quotasData.find(q => q.cognito_user_id === userId);
    if (!selectedQuotaUser) return;
    
    // Update modal title and button based on status
    const modalTitle = document.querySelector('#unblock-user-modal .modal-header h2');
    const submitButton = document.querySelector('#unblock-user-modal button[type="submit"]');
    const reasonLabel = document.querySelector('#unblock-user-modal label[for="unblock-reason"]');
    const alertMessage = document.querySelector('#unblock-user-modal .alert');
    
    if (selectedQuotaUser.status === 'ADMIN_SAFE') {
        // Admin-Safe user - change to "Remove Admin Protection"
        modalTitle.innerHTML = '🛡️ Remove Admin Protection';
        submitButton.textContent = 'Remove Protection';
        submitButton.style.background = '#805ad5'; // Purple
        reasonLabel.textContent = 'Reason for removing protection: *';
        alertMessage.className = 'alert info';
        alertMessage.innerHTML = '<strong>ℹ️ Note:</strong> User will lose Admin-Safe protection and return to normal quota limits.';
    } else {
        // Blocked user - standard unblock
        modalTitle.innerHTML = '🔓 Unblock User';
        submitButton.textContent = 'Unblock User';
        submitButton.style.background = '#38a169'; // Green
        reasonLabel.textContent = 'Unblock Reason: *';
        alertMessage.className = 'alert success';
        alertMessage.innerHTML = '<strong>✅ Note:</strong> User will regain access immediately after unblocking.';
    }
    
    document.getElementById('unblock-user-email').textContent = selectedQuotaUser.cognito_email;
    document.getElementById('unblock-user-person').textContent = selectedQuotaUser.person || '-';
    document.getElementById('unblock-user-team').textContent = selectedQuotaUser.team || '-';
    document.getElementById('unblock-user-status').textContent = selectedQuotaUser.status;
    
    // Show additional info if blocked
    const blockedInfo = document.getElementById('unblock-blocked-info');
    if (selectedQuotaUser.status === 'BLOCKED') {
        blockedInfo.style.display = 'block';
        document.getElementById('unblock-blocked-until').textContent = 
            selectedQuotaUser.blocked_until ? formatDateTime(selectedQuotaUser.blocked_until) : '-';
        document.getElementById('unblock-block-reason').textContent = 
            selectedQuotaUser.block_reason || '-';
    } else {
        blockedInfo.style.display = 'none';
    }
    
    document.getElementById('unblock-reason').value = '';
    
    document.getElementById('unblock-user-modal').style.display = 'flex';
}

function showSetAdminSafeModal(userId) {
    selectedQuotaUser = quotasData.find(q => q.cognito_user_id === userId);
    if (!selectedQuotaUser) return;
    
    document.getElementById('admin-safe-user-email').textContent = selectedQuotaUser.cognito_email;
    document.getElementById('admin-safe-user-person').textContent = selectedQuotaUser.person || '-';
    document.getElementById('admin-safe-user-team').textContent = selectedQuotaUser.team || '-';
    document.getElementById('admin-safe-user-status').textContent = selectedQuotaUser.status;
    document.getElementById('admin-safe-reason').value = '';
    
    document.getElementById('admin-safe-modal').style.display = 'flex';
}

function closeBlockUserModal() {
    document.getElementById('block-user-modal').style.display = 'none';
    selectedQuotaUser = null;
}

function closeUnblockUserModal() {
    document.getElementById('unblock-user-modal').style.display = 'none';
    selectedQuotaUser = null;
}

function closeAdminSafeModal() {
    document.getElementById('admin-safe-modal').style.display = 'none';
    selectedQuotaUser = null;
}

// ============================================================================
// HELPER: GET CURRENT USER EMAIL
// ============================================================================

function getCurrentUserEmail() {
    // Try to get from Cognito session if available
    // For now, return a placeholder - this should be replaced with actual Cognito user info
    return 'admin@example.com'; // TODO: Get from Cognito session
}

// ============================================================================
// MODAL ACTIONS
// ============================================================================

async function blockUser() {
    if (!selectedQuotaUser) return;
    
    const blockedUntil = document.getElementById('block-until-datetime').value;
    const reason = document.getElementById('block-reason').value.trim();
    
    // Validation
    if (!blockedUntil) {
        showNotification('Please select a block until date/time', 'error');
        return;
    }
    
    if (!reason) {
        showNotification('Please provide a reason for blocking', 'error');
        return;
    }
    
    // Check if date is in the future
    const blockDate = new Date(blockedUntil);
    if (blockDate <= new Date()) {
        showNotification('Block until date must be in the future', 'error');
        return;
    }
    
    try {
        console.log('🔒 Blocking user:', {
            userId: selectedQuotaUser.cognito_user_id,
            email: selectedQuotaUser.cognito_email,
            blockedUntil,
            reason
        });
        
        // Convert to ISO 8601 format
        const blockedUntilISO = new Date(blockedUntil).toISOString();
        const performedBy = getCurrentUserEmail();
        
        // Call API
        const result = await api.blockUser(
            selectedQuotaUser.cognito_user_id,
            blockedUntilISO,
            reason,
            performedBy
        );
        
        console.log('✅ User blocked successfully:', result);
        showNotification(`User ${selectedQuotaUser.cognito_email} blocked successfully`, 'success');
        
        // Close modal and reload data
        closeBlockUserModal();
        await loadUserQuotas();
        
    } catch (error) {
        console.error('❌ Error blocking user:', error);
        showNotification('Failed to block user: ' + error.message, 'error');
    }
}

async function unblockUser() {
    if (!selectedQuotaUser) return;
    
    const reason = document.getElementById('unblock-reason').value.trim();
    
    // Validation
    if (!reason) {
        showNotification('Please provide a reason for unblocking', 'error');
        return;
    }
    
    try {
        console.log('🔓 Unblocking user:', {
            userId: selectedQuotaUser.cognito_user_id,
            email: selectedQuotaUser.cognito_email,
            currentStatus: selectedQuotaUser.status,
            reason
        });
        
        const performedBy = getCurrentUserEmail();
        
        // Call API
        const result = await api.unblockUser(
            selectedQuotaUser.cognito_user_id,
            reason,
            performedBy
        );
        
        console.log('✅ User unblocked successfully:', result);
        
        const action = selectedQuotaUser.status === 'ADMIN_SAFE' ? 'unprotected' : 'unblocked';
        showNotification(`User ${selectedQuotaUser.cognito_email} ${action} successfully`, 'success');
        
        // Close modal and reload data
        closeUnblockUserModal();
        await loadUserQuotas();
        
    } catch (error) {
        console.error('❌ Error unblocking user:', error);
        showNotification('Failed to unblock user: ' + error.message, 'error');
    }
}

async function setAdminSafe() {
    if (!selectedQuotaUser) return;
    
    const reason = document.getElementById('admin-safe-reason').value.trim();
    
    // Validation
    if (!reason) {
        showNotification('Please provide a reason for setting Admin-Safe', 'error');
        return;
    }
    
    try {
        console.log('🛡️ Setting Admin-Safe:', {
            userId: selectedQuotaUser.cognito_user_id,
            email: selectedQuotaUser.cognito_email,
            currentStatus: selectedQuotaUser.status,
            reason
        });
        
        const performedBy = getCurrentUserEmail();
        
        // Call API
        const result = await api.setAdminSafe(
            selectedQuotaUser.cognito_user_id,
            reason,
            performedBy
        );
        
        console.log('✅ Admin-Safe set successfully:', result);
        showNotification(`User ${selectedQuotaUser.cognito_email} set to Admin-Safe successfully`, 'success');
        
        // Close modal and reload data
        closeAdminSafeModal();
        await loadUserQuotas();
        
    } catch (error) {
        console.error('❌ Error setting Admin-Safe:', error);
        showNotification('Failed to set Admin-Safe: ' + error.message, 'error');
    }
}

// ============================================================================
// FILTER AND SEARCH
// ============================================================================

function filterQuotasTable() {
    const searchTerm = document.getElementById('quotas-search').value.toLowerCase();
    
    filteredQuotasData = quotasData.filter(quota => {
        return (
            quota.cognito_user_id.toLowerCase().includes(searchTerm) ||
            quota.cognito_email.toLowerCase().includes(searchTerm) ||
            (quota.person && quota.person.toLowerCase().includes(searchTerm)) ||
            (quota.team && quota.team.toLowerCase().includes(searchTerm)) ||
            quota.status.toLowerCase().includes(searchTerm)
        );
    });
    
    quotasCurrentPage = 1;
    displayQuotasTable();
}

// ============================================================================
// PAGINATION
// ============================================================================

function updateQuotasPagination() {
    const totalPages = Math.ceil(filteredQuotasData.length / quotasItemsPerPage);
    const start = (quotasCurrentPage - 1) * quotasItemsPerPage + 1;
    const end = Math.min(quotasCurrentPage * quotasItemsPerPage, filteredQuotasData.length);
    
    document.getElementById('quotas-pagination-info').textContent = 
        `Showing ${start}-${end} of ${filteredQuotasData.length} users`;
    document.getElementById('quotas-current-page').textContent = quotasCurrentPage;
    document.getElementById('quotas-total-pages').textContent = totalPages;
    
    document.getElementById('quotas-prev-page').disabled = quotasCurrentPage === 1;
    document.getElementById('quotas-next-page').disabled = quotasCurrentPage === totalPages || totalPages === 0;
}

function previousQuotasPage() {
    if (quotasCurrentPage > 1) {
        quotasCurrentPage--;
        displayQuotasTable();
    }
}

function nextQuotasPage() {
    const totalPages = Math.ceil(filteredQuotasData.length / quotasItemsPerPage);
    if (quotasCurrentPage < totalPages) {
        quotasCurrentPage++;
        displayQuotasTable();
    }
}

// ============================================================================
// EXPORT TO CSV
// ============================================================================

function exportQuotasToCSV() {
    console.log('📥 Exporting quotas to CSV...');
    
    try {
        // CSV headers
        const headers = [
            'User ID',
            'Email',
            'Person',
            'Team',
            'Requests Today',
            'Daily Limit',
            'Usage %',
            'Status',
            'Blocked Until'
        ];
        
        // CSV rows
        const rows = filteredQuotasData.map(quota => {
            const usagePercent = quota.daily_limit > 0 
                ? Math.round((quota.requests_today / quota.daily_limit) * 100) 
                : 0;
            
            return [
                quota.cognito_user_id,
                quota.cognito_email,
                quota.person || '',
                quota.team || '',
                quota.requests_today,
                quota.daily_limit,
                usagePercent,
                quota.status,
                quota.blocked_until || ''
            ];
        });
        
        // Create CSV content
        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
        ].join('\n');
        
        // Create download link
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        
        const today = new Date().toISOString().split('T')[0];
        link.setAttribute('href', url);
        link.setAttribute('download', `user-quotas-${today}.csv`);
        link.style.visibility = 'hidden';
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        showNotification('Quotas data exported successfully', 'success');
        console.log('✅ CSV exported successfully');
        
    } catch (error) {
        console.error('❌ Error exporting CSV:', error);
        showNotification('Failed to export CSV: ' + error.message, 'error');
    }
}

// ============================================================================
// NOTIFICATIONS
// ============================================================================

function showNotification(message, type) {
    // Use the showAlert function from dashboard.js if available
    if (typeof showAlert === 'function') {
        showAlert(type, message);
    } else {
        // Fallback to console
        console.log(`[${type.toUpperCase()}] ${message}`);
    }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

console.log('✅ User Quotas module loaded');