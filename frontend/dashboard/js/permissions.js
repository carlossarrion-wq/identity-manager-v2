/**
 * Permissions Management Module
 * =============================
 * Handles all permissions-related functionality in the dashboard
 */

// Global state for permissions
let permissionsCache = {
    applications: [],
    modules: [],
    permissionTypes: [],
    allPermissions: []
};

/**
 * Initialize permissions module
 */
async function initPermissions() {
    console.log('🔐 Initializing Permissions module...');
    
    try {
        // Load catalogs
        await Promise.all([
            loadPermissionTypes(),
            loadModules()
        ]);
        
        console.log('✓ Permissions module initialized');
    } catch (error) {
        console.error('Error initializing permissions:', error);
    }
}

/**
 * Load permission types catalog
 */
async function loadPermissionTypes() {
    try {
        const response = await api.request('list_permission_types', {});
        
        if (response.permission_types) {
            permissionsCache.permissionTypes = response.permission_types;
            console.log(`✓ Loaded ${permissionsCache.permissionTypes.length} permission types`);
            
            // Populate permission type select
            const select = document.getElementById('perm-type');
            if (select) {
                select.innerHTML = '<option value="">Select permission type...</option>';
                permissionsCache.permissionTypes.forEach(type => {
                    const option = document.createElement('option');
                    option.value = type.id;
                    option.textContent = `${type.name} (Level ${type.level})`;
                    option.dataset.level = type.level;
                    select.appendChild(option);
                });
            }
        }
    } catch (error) {
        console.error('Error loading permission types:', error);
        showAlert('error', 'Error loading permission types');
    }
}

/**
 * Load modules catalog and applications
 */
async function loadModules() {
    try {
        // Load applications directly from the database
        const appsResponse = await api.request('list_applications', {});
        
        if (appsResponse.applications) {
            permissionsCache.applications = appsResponse.applications;
            console.log(`✓ Loaded ${permissionsCache.applications.length} applications`);
            
            // Populate application select
            const appSelect = document.getElementById('perm-application');
            if (appSelect) {
                appSelect.innerHTML = '<option value="">Select application...</option>';
                permissionsCache.applications.forEach(app => {
                    const option = document.createElement('option');
                    option.value = app.application_id;
                    option.textContent = app.application_name;
                    appSelect.appendChild(option);
                });
            }
        }
        
        // Load modules
        const modulesResponse = await api.request('list_modules', {});
        
        if (modulesResponse.modules) {
            permissionsCache.modules = modulesResponse.modules;
            console.log(`✓ Loaded ${permissionsCache.modules.length} modules`);
            
            // Populate module select
            const moduleSelect = document.getElementById('perm-module');
            if (moduleSelect) {
                moduleSelect.innerHTML = '<option value="">Select module...</option>';
                permissionsCache.modules.forEach(module => {
                    const option = document.createElement('option');
                    option.value = module.module_id;
                    option.textContent = `${module.module_name} (${module.application_name})`;
                    moduleSelect.appendChild(option);
                });
            }
        }
    } catch (error) {
        console.error('Error loading modules/applications:', error);
        showAlert('error', 'Error loading modules and applications');
    }
}

/**
 * Load all permissions
 */
async function loadAllPermissions() {
    const tbody = document.querySelector('#permissions-table tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '<tr><td colspan="10"><div class="loading-spinner"></div>Loading permissions...</td></tr>';
    
    try {
        const response = await api.request('list_all_permissions', {});
        
        // La respuesta viene en response.permissions directamente desde api.request
        if (response && response.permissions) {
            permissionsCache.allPermissions = response.permissions;
            renderPermissionsTable(permissionsCache.allPermissions);
            console.log(`✓ Loaded ${response.permissions.length} permissions`);
        } else {
            tbody.innerHTML = '<tr><td colspan="10">No permissions found</td></tr>';
        }
    } catch (error) {
        console.error('Error loading permissions:', error);
        tbody.innerHTML = '<tr><td colspan="10">Error loading permissions</td></tr>';
        showAlert('error', 'Error loading permissions');
    }
}

/**
 * Search user permissions
 */
async function searchUserPermissions() {
    const userInput = document.getElementById('permission-search-user').value.trim();
    const scopeFilter = document.getElementById('permission-filter-scope').value;
    const statusFilter = document.getElementById('permission-filter-status').value;
    
    const tbody = document.querySelector('#permissions-table tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '<tr><td colspan="10"><div class="loading-spinner"></div>Searching permissions...</td></tr>';
    
    try {
        let permissions = [];
        
        // If user input is provided, search by user
        if (userInput) {
            const response = await api.request('get_user_permissions', { user_id: userInput });
            
            if (response.permissions) {
                permissions = response.permissions;
            }
        } else {
            // If no user input, load all permissions
            const response = await api.request('list_all_permissions', {});
            
            if (response.permissions) {
                permissions = response.permissions;
            }
        }
        
        // Apply filters
        let filteredPermissions = permissions;
        
        if (scopeFilter) {
            filteredPermissions = filteredPermissions.filter(p => p.scope === scopeFilter);
        }
        
        if (statusFilter) {
            filteredPermissions = filteredPermissions.filter(p => p.status === statusFilter);
        }
        
        // Render results
        if (filteredPermissions.length > 0) {
            renderPermissionsTable(filteredPermissions);
            const message = userInput 
                ? `Found ${filteredPermissions.length} permission(s) for user` 
                : `Showing ${filteredPermissions.length} permission(s)`;
            showAlert('success', message);
        } else {
            tbody.innerHTML = '<tr><td colspan="10">No permissions found</td></tr>';
        }
    } catch (error) {
        console.error('Error searching permissions:', error);
        tbody.innerHTML = '<tr><td colspan="10">Error searching permissions</td></tr>';
        showAlert('error', 'Error searching permissions');
    }
}

/**
 * Render permissions table
 */
function renderPermissionsTable(permissions) {
    const tbody = document.querySelector('#permissions-table tbody');
    if (!tbody) return;
    
    if (!permissions || permissions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10">No permissions found</td></tr>';
        return;
    }
    
    tbody.innerHTML = permissions.map(perm => {
        const expiresText = perm.expires_at ? formatDate(perm.expires_at) : 'Never';
        const statusText = perm.status.charAt(0).toUpperCase() + perm.status.slice(1);
        
        return `
            <tr>
                <td>${escapeHtml(perm.user_id)}</td>
                <td>${escapeHtml(perm.email || '-')}</td>
                <td><span class="status-badge status-${perm.scope}">${perm.scope}</span></td>
                <td>${escapeHtml(perm.resource_name)}</td>
                <td>${escapeHtml(perm.permission_type)}</td>
                <td>${perm.permission_level}</td>
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
}

/**
 * Show assign permission modal
 */
async function showAssignPermissionModal() {
    const modal = document.getElementById('assign-permission-modal');
    if (modal) {
        modal.classList.add('show');
        
        // Reset form
        document.getElementById('assign-permission-form').reset();
        document.getElementById('app-permission-fields').style.display = 'none';
        document.getElementById('module-permission-fields').style.display = 'none';
        
        // Load users for dropdown
        await loadUsersForPermissionDropdown();
    }
}

/**
 * Load users for permission dropdown
 */
async function loadUsersForPermissionDropdown() {
    try {
        const data = await api.listUsers();
        const select = document.getElementById('perm-user');
        
        if (select) {
            select.innerHTML = '<option value="">Select a user...</option>' +
                data.users.map(u => `<option value="${u.user_id}" data-email="${u.email}">${u.email} (${u.person || 'No name'})</option>`).join('');
        }
    } catch (error) {
        console.error('Error loading users for dropdown:', error);
        showAlert('error', 'Error loading users');
    }
}

/**
 * Close assign permission modal
 */
function closeAssignPermissionModal() {
    const modal = document.getElementById('assign-permission-modal');
    if (modal) {
        modal.classList.remove('show');
    }
}

/**
 * Update permission form based on scope selection
 */
function updatePermissionForm() {
    const scope = document.getElementById('perm-scope').value;
    const appFields = document.getElementById('app-permission-fields');
    const moduleFields = document.getElementById('module-permission-fields');
    
    if (scope === 'application') {
        appFields.style.display = 'block';
        moduleFields.style.display = 'none';
        document.getElementById('perm-application').required = true;
        document.getElementById('perm-module').required = false;
    } else if (scope === 'module') {
        appFields.style.display = 'none';
        moduleFields.style.display = 'block';
        document.getElementById('perm-application').required = false;
        document.getElementById('perm-module').required = true;
    } else {
        appFields.style.display = 'none';
        moduleFields.style.display = 'none';
        document.getElementById('perm-application').required = false;
        document.getElementById('perm-module').required = false;
    }
}

/**
 * Handle assign permission form submission
 */
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('assign-permission-form');
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Get user from selector
            const userSelect = document.getElementById('perm-user');
            const userId = userSelect.value;
            const selectedOption = userSelect.options[userSelect.selectedIndex];
            const userEmail = selectedOption ? selectedOption.getAttribute('data-email') : '';
            
            const scope = document.getElementById('perm-scope').value;
            const permissionTypeId = document.getElementById('perm-type').value;
            const durationDays = document.getElementById('perm-duration').value;
            
            console.log('Form data:', { userId, userEmail, scope, permissionTypeId, durationDays });
            
            if (!userId) {
                showAlert('warning', 'Please select a user');
                return;
            }
            
            if (!scope) {
                showAlert('warning', 'Please select a permission scope');
                return;
            }
            
            if (!permissionTypeId) {
                showAlert('warning', 'Please select a permission type');
                return;
            }
            
            let operation, data;
            
            if (scope === 'application') {
                const applicationId = document.getElementById('perm-application').value;
                if (!applicationId) {
                    showAlert('warning', 'Please select an application');
                    return;
                }
                
                operation = 'assign_app_permission';
                data = {
                    data: {
                        user_id: userId,
                        user_email: userEmail,
                        application_id: applicationId,
                        permission_type_id: permissionTypeId,
                        duration_days: durationDays ? parseInt(durationDays) : null
                    }
                };
            } else if (scope === 'module') {
                const moduleId = document.getElementById('perm-module').value;
                if (!moduleId) {
                    showAlert('warning', 'Please select a module');
                    return;
                }
                
                operation = 'assign_module_permission';
                data = {
                    data: {
                        user_id: userId,
                        user_email: userEmail,
                        module_id: moduleId,
                        permission_type_id: permissionTypeId,
                        duration_days: durationDays ? parseInt(durationDays) : null
                    }
                };
            } else {
                showAlert('error', 'Invalid permission scope');
                return;
            }
            
            console.log('Sending request:', { operation, data });
            
            try {
                await api.request(operation, data);
                showAlert('success', 'Permission assigned successfully');
                closeAssignPermissionModal();
                loadAllPermissions();
            } catch (error) {
                console.error('Error assigning permission:', error);
                showAlert('error', `Error assigning permission: ${error.message}`);
            }
        });
    }
});

/**
 * Revoke permission
 */
async function revokePermission(permissionId, scope, userId, resourceId) {
    if (!confirm('Are you sure you want to revoke this permission?')) {
        return;
    }
    
    try {
        let operation, data;
        
        if (scope === 'application') {
            operation = 'revoke_app_permission';
            data = {
                user_id: userId,
                application_id: resourceId
            };
        } else if (scope === 'module') {
            operation = 'revoke_module_permission';
            data = {
                user_id: userId,
                module_id: resourceId
            };
        } else {
            showAlert('error', 'Invalid permission scope');
            return;
        }
        
        await api.request(operation, data);
        showAlert('success', 'Permission revoked successfully');
        loadAllPermissions();
    } catch (error) {
        console.error('Error revoking permission:', error);
        showAlert('error', `Error revoking permission: ${error.message}`);
    }
}

/**
 * Restore permission (re-assign with same settings)
 */
async function restorePermission(permissionId, scope, userId, resourceId) {
    if (!confirm('Are you sure you want to restore this permission?')) {
        return;
    }
    
    try {
        // Find the permission in cache to get user email and permission type
        const permission = permissionsCache.allPermissions.find(p => 
            p.user_id === userId && p.resource_id === resourceId && p.scope === scope
        );
        
        if (!permission) {
            showAlert('error', 'Permission not found in cache. Please refresh and try again.');
            return;
        }
        
        // Get permission type ID from the permission types cache
        const permType = permissionsCache.permissionTypes.find(pt => pt.name === permission.permission_type);
        const permissionTypeId = permType ? permType.id : null;
        
        if (!permissionTypeId) {
            showAlert('error', 'Permission type not found. Please refresh and try again.');
            return;
        }
        
        // Restoring is the same as assigning again - it will reactivate the permission
        let operation, data;
        
        if (scope === 'application') {
            operation = 'assign_app_permission';
            data = {
                data: {
                    user_id: userId,
                    user_email: permission.email || '',
                    application_id: resourceId,
                    permission_type_id: permissionTypeId,
                    duration_days: null // Keep indefinite
                }
            };
        } else if (scope === 'module') {
            operation = 'assign_module_permission';
            data = {
                data: {
                    user_id: userId,
                    user_email: permission.email || '',
                    module_id: resourceId,
                    permission_type_id: permissionTypeId,
                    duration_days: null // Keep indefinite
                }
            };
        } else {
            showAlert('error', 'Invalid permission scope');
            return;
        }
        
        await api.request(operation, data);
        showAlert('success', 'Permission restored successfully');
        loadAllPermissions();
    } catch (error) {
        console.error('Error restoring permission:', error);
        showAlert('error', `Error restoring permission: ${error.message}`);
    }
}

/**
 * Format date helper
 */
function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Escape HTML helper
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize permissions when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPermissions);
} else {
    initPermissions();
}
