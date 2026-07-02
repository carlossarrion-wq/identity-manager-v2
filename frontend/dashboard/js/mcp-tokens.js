/**
 * MCP Tokens & Monitoring
 * =======================
 * Gestión de tokens del servidor MCP de Remedy F1 y pestaña de monitorización.
 * Flujo SEPARADO de los tokens del proxy Bedrock. Reutiliza helpers globales
 * (formatDate, showAlert) definidos en dashboard.js.
 */

let mcpTokensState = [];

// ----------------------------------------------------------------------------
// MCP TOKENS
// ----------------------------------------------------------------------------
async function loadMcpTokens() {
    try {
        const data = await api.listMcpTokens({ status: 'all' });
        mcpTokensState = data.tokens || [];
        renderMcpTokensTable(mcpTokensState);
    } catch (error) {
        console.error('Error loading MCP tokens:', error);
        showAlert('error', `Error loading MCP tokens: ${error.message}`);
    }
}

function renderMcpTokensTable(tokens) {
    const tbody = document.querySelector('#mcp-tokens-table tbody');
    if (!tokens || tokens.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align: center;">No MCP tokens found</td></tr>';
        return;
    }

    tbody.innerHTML = tokens.map(token => `
        <tr>
            <td><code>${token.token_id ? String(token.token_id).substring(0, 8) + '...' : '-'}</code></td>
            <td><code>${token.user_id ? String(token.user_id).substring(0, 8) + '...' : '-'}</code></td>
            <td>${token.email || '-'}</td>
            <td>${token.naturgy_user_900 || '-'}</td>
            <td>${(token.allowed_groups && token.allowed_groups.length) ? token.allowed_groups.join(', ') : '-'}</td>
            <td>${formatDate(token.created_at)}</td>
            <td>${formatDate(token.expires_at)}</td>
            <td><span class="status-badge status-${token.status}">${token.status.charAt(0).toUpperCase() + token.status.slice(1)}</span></td>
            <td>
                ${token.status !== 'revoked' ? `
                <button class="btn-action btn-warning" onclick="confirmRevokeMcpToken('${token.token_id}')" title="Revoke MCP Token">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width: 16px; height: 16px;">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                    </svg>
                </button>` : '-'}
            </td>
        </tr>
    `).join('');
}

function filterMcpTokensTable() {
    const term = (document.getElementById('mcp-tokens-search').value || '').toLowerCase();
    const filtered = mcpTokensState.filter(t =>
        (t.email || '').toLowerCase().includes(term) ||
        (t.naturgy_user_900 || '').toLowerCase().includes(term) ||
        (t.user_id || '').toLowerCase().includes(term)
    );
    renderMcpTokensTable(filtered);
}

async function showCreateMcpTokenModal() {
    document.getElementById('create-mcp-token-modal').classList.add('show');
    document.getElementById('create-mcp-token-form').reset();
    document.getElementById('mcp-token-result').style.display = 'none';
    document.getElementById('create-mcp-token-form').style.display = 'block';

    try {
        const [usersData, groupsData] = await Promise.all([
            api.listUsersLight(),
            api.listMcpGroups()
        ]);

        const userSelect = document.getElementById('mcp-token-user');
        userSelect.innerHTML = '<option value="">Select a user...</option>' +
            usersData.users.map(u => `<option value="${u.user_id}">${u.email} (${u.person || 'No name'})</option>`).join('');

        const groupSelect = document.getElementById('mcp-token-groups');
        groupSelect.innerHTML = (groupsData.groups || [])
            .map(g => `<option value="${g}">${g}</option>`).join('');
    } catch (error) {
        console.error('Error loading data for MCP token:', error);
        showAlert('error', 'Error loading form data');
    }
}

function closeCreateMcpTokenModal() {
    document.getElementById('create-mcp-token-modal').classList.remove('show');
}

function copyMcpToken() {
    const textarea = document.getElementById('mcp-token-jwt');
    textarea.select();
    document.execCommand('copy');
    showAlert('success', 'MCP token copied to clipboard');
}

async function confirmRevokeMcpToken(tokenId) {
    if (!confirm('¿Revocar este token MCP? El usuario perderá acceso al servidor MCP.')) return;
    try {
        await api.revokeMcpToken(tokenId);
        showAlert('success', 'MCP token revoked');
        loadMcpTokens();
    } catch (error) {
        showAlert('error', `Error revoking MCP token: ${error.message}`);
    }
}

document.getElementById('create-mcp-token-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const userId = document.getElementById('mcp-token-user').value;
    const naturgy900 = document.getElementById('mcp-token-900').value.trim() || null;
    const groupsSelect = document.getElementById('mcp-token-groups');
    const allowedGroups = Array.from(groupsSelect.selectedOptions).map(o => o.value);
    const validity = document.getElementById('mcp-token-validity').value;
    const sendEmail = document.getElementById('mcp-token-send-email').checked;

    try {
        const result = await api.createMcpToken(userId, naturgy900, allowedGroups, validity, sendEmail);
        document.getElementById('create-mcp-token-form').style.display = 'none';
        document.getElementById('mcp-token-result').style.display = 'block';
        document.getElementById('mcp-token-jwt').value = result.token.jwt;
        document.getElementById('mcp-token-id-display').textContent = result.token.token_id;
        document.getElementById('mcp-token-expires-display').textContent = result.token.expires_at;
        document.getElementById('mcp-token-900-display').textContent = result.token.naturgy_user_900 || '-';
        document.getElementById('mcp-token-groups-display').textContent =
            (result.token.allowed_groups && result.token.allowed_groups.length) ? result.token.allowed_groups.join(', ') : '-';
    } catch (error) {
        showAlert('error', `Error creating MCP token: ${error.message}`);
    }
});

// ----------------------------------------------------------------------------
// MCP MONITORING
// ----------------------------------------------------------------------------
async function loadMcpMonitoring() {
    const hours = parseInt(document.getElementById('mcp-monitoring-range')?.value || '24', 10);
    try {
        const [summary, byUser, activeTokens] = await Promise.all([
            api.getMcpUsageSummary(hours),
            api.getMcpUsageByUser(hours),
            api.listMcpTokens({ status: 'active' })
        ]);

        document.getElementById('mcp-total-invocations').textContent = summary.total_invocations ?? 0;
        document.getElementById('mcp-total-errors').textContent = summary.total_errors ?? 0;
        document.getElementById('mcp-active-tokens').textContent = (activeTokens.tokens || []).length;

        renderKeyValueTable('#mcp-by-tool-table', summary.by_tool, 'tool', 'invocations');
        renderKeyValueTable('#mcp-by-user-table', byUser.by_user, 'user', 'invocations');
    } catch (error) {
        console.error('Error loading MCP monitoring:', error);
        showAlert('error', `Error loading MCP monitoring: ${error.message}`);
    }
}

function renderKeyValueTable(selector, rows, keyField, valueField) {
    const tbody = document.querySelector(`${selector} tbody`);
    if (!rows || rows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="2" style="text-align:center;">No data in selected period</td></tr>';
        return;
    }
    tbody.innerHTML = rows.map(r =>
        `<tr><td>${r[keyField] || '-'}</td><td>${r[valueField] || 0}</td></tr>`
    ).join('');
}
