/**
 * Proxy Bedrock Usage Dashboard JavaScript
 * Handles data loading, chart rendering, and user interactions
 */

// Global variables
let currentPage = 1;
let pageSize = 10;
let totalUsers = 0;
let usageData = [];
let charts = {};

// Usage pagination state
let usagePagination = {
    currentPage: 1,
    pageSize: 10,
    filteredData: [],
    allData: []
};

// Date range state
let dateRange = {
    start: null,
    end: null
};

/**
 * Initialize the proxy usage dashboard
 */
function initProxyUsage() {
    console.log('Initializing Proxy Usage Dashboard...');
    console.log('DOM ready, elements available');
    
    // Set default date range (today) - from 00:00:00 to 23:59:59 of current day
    const now = new Date();
    const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0, 0);
    const endOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59, 999);
    
    dateRange.start = startOfDay;
    dateRange.end = endOfDay;
    
    console.log('📅 Date range set:', {
        start: dateRange.start.toISOString(),
        end: dateRange.end.toISOString()
    });
    
    // Update date inputs (use value instead of valueAsDate to avoid timezone issues)
    const startInput = document.getElementById('start-date');
    const endInput = document.getElementById('end-date');
    if (startInput && endInput) {
        startInput.value = now.toISOString().split('T')[0]; // YYYY-MM-DD format
        endInput.value = now.toISOString().split('T')[0];
    }
    
    // Load initial data
    loadUsageData();
    
    // Check API connection
    checkConnection();
}

/**
 * Set quick filter for date range
 */
function setQuickFilter(filter) {
    const now = new Date();
    
    // Remove active class from all buttons
    document.querySelectorAll('.quick-filters button').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Set date range based on filter
    switch(filter) {
        case 'today':
            // Today: from 00:00:00 to 23:59:59 of current day
            dateRange.start = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0, 0);
            dateRange.end = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59, 999);
            break;
        case '7days':
            // Last 7 days: from 7 days ago 00:00:00 to now
            dateRange.start = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 7, 0, 0, 0, 0);
            dateRange.end = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59, 999);
            break;
        case '30days':
            // Last 30 days: from 30 days ago 00:00:00 to now
            dateRange.start = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 30, 0, 0, 0, 0);
            dateRange.end = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59, 999);
            break;
    }
    
    console.log(`📅 Filter '${filter}' applied:`, {
        start: dateRange.start.toISOString(),
        end: dateRange.end.toISOString()
    });
    
    // Add active class to the button that matches the filter (if called from button click)
    if (typeof event !== 'undefined' && event.target) {
        event.target.classList.add('active');
    }
    
    // Update date inputs if they exist (use value to avoid timezone issues)
    const startInput = document.getElementById('start-date');
    const endInput = document.getElementById('end-date');
    if (startInput && endInput) {
        // Format dates as YYYY-MM-DD for date inputs
        const formatDate = (date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        };
        startInput.value = formatDate(dateRange.start);
        endInput.value = formatDate(dateRange.end);
    }
    
    // Reload data
    loadUsageData();
}

/**
 * Apply custom date filter
 */
function applyDateFilter() {
    const startInput = document.getElementById('start-date');
    const endInput = document.getElementById('end-date');
    
    if (startInput.value && endInput.value) {
        dateRange.start = new Date(startInput.value);
        dateRange.end = new Date(endInput.value);
        
        // Remove active class from quick filter buttons
        document.querySelectorAll('.quick-filters button').forEach(btn => {
            btn.classList.remove('active');
        });
        
        // Reload data
        loadUsageData();
    } else {
        alert('Please select both start and end dates');
    }
}

/**
 * Load usage data from API
 */
async function loadUsageData() {
    try {
        console.log('Loading usage data...', dateRange);
        
        // Prepare filters - format as YYYY-MM-DD to avoid timezone issues
        const formatDateForAPI = (date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        };
        
        const filters = {
            start_date: formatDateForAPI(dateRange.start),
            end_date: formatDateForAPI(dateRange.end)
        };
        
        console.log('📅 Filters sent to API:', filters);
        
        // Load all data in parallel
        const [summary, byHour, byTeam, byDay, responseStatus, trend, byUser] = await Promise.all([
            api.request('get_proxy_usage_summary', { filters }),
            api.request('get_proxy_usage_by_hour', { filters }),
            api.request('get_proxy_usage_by_team', { filters }),
            api.request('get_proxy_usage_by_day', { filters }),
            api.request('get_proxy_usage_response_status', { filters }),
            api.request('get_proxy_usage_trend', { filters }),
            api.request('get_proxy_usage_by_user', { filters, page: currentPage, page_size: pageSize })
        ]);
        
        console.log('📊 API Response - Summary:', summary);
        console.log('📊 API Response - ByHour:', byHour);
        
        // Check if data is nested (API returns {data: {data: {...}}})
        const summaryData = summary.data || summary;
        const byHourData = byHour.data || byHour;
        const byTeamData = byTeam.data || byTeam;
        const byDayData = byDay.data || byDay;
        const responseStatusData = responseStatus.data || responseStatus;
        const trendData = trend.data || trend;
        const byUserData = byUser.data || byUser;
        
        // Update KPIs - use requestAnimationFrame to ensure DOM is ready
        requestAnimationFrame(() => {
            updateKPIs({
                totalRequests: summaryData.total_requests,
                requestsChange: summaryData.requests_change,
                totalTokens: summaryData.total_tokens,
                tokensChange: summaryData.tokens_change,
                totalCost: summaryData.total_cost,
                costChange: summaryData.cost_change,
                avgResponseTime: summaryData.avg_response_time,
                responseTimeChange: summaryData.response_time_change
            });
        });
        
        // Update charts
        updateCharts({
            byHour: {
                labels: byHourData.labels,
                data: byHourData.values,
                peakHour: `${byHourData.peak_hour.hour} (${byHourData.peak_hour.requests.toLocaleString()} requests)`
            },
            byTeam: {
                labels: byTeamData.labels,
                data: byTeamData.values,
                topTeam: `${byTeamData.top_team.name} (${byTeamData.top_team.percentage}%)`
            },
            byDay: {
                labels: byDayData.labels,
                data: byDayData.values,
                peakDay: `${byDayData.peak_day.date} (${byDayData.peak_day.requests.toLocaleString()} requests)`
            },
            responseStatus: {
                labels: responseStatusData.labels,
                data: responseStatusData.values,
                successRate: `${responseStatusData.success_rate.percentage}% (${responseStatusData.success_rate.successful_requests.toLocaleString()} successful requests)`
            },
            trend: {
                labels: trendData.labels,
                datasets: trendData.datasets
            }
        });
        
        // Update table with new pagination
        usageData = byUserData.users;
        totalUsers = byUserData.pagination.total_records;
        
        // Initialize pagination data
        usagePagination.allData = usageData;
        usagePagination.filteredData = usageData;
        usagePagination.currentPage = 1;
        
        // Render with new pagination
        renderUsagePaginatedTable();
        
        // Update connection status
        updateConnectionStatus(true);
        
    } catch (error) {
        console.error('Error loading usage data:', error);
        showError('Failed to load usage data: ' + error.message);
        updateConnectionStatus(false);
        
        // Fallback to mock data for development
        const mockData = generateMockData();
        updateKPIs(mockData.kpis);
        updateCharts(mockData.charts);
        usageData = mockData.users;
        totalUsers = usageData.length;
        
        // Initialize pagination data with mock data
        usagePagination.allData = usageData;
        usagePagination.filteredData = usageData;
        usagePagination.currentPage = 1;
        
        // Render with new pagination
        renderUsagePaginatedTable();
    }
}

/**
 * Generate mock data (to be replaced with real API calls)
 */
function generateMockData() {
    return {
        kpis: {
            totalRequests: 12458,
            requestsChange: '+15.2%',
            totalTokens: 2400000,
            tokensChange: '+12.3%',
            totalCost: 124.50,
            costChange: '+18.1%',
            avgResponseTime: 1234,
            responseTimeChange: '-5.2%'
        },
        charts: {
            byHour: {
                labels: ['00h', '01h', '02h', '03h', '04h', '05h', '06h', '07h', '08h', '09h', '10h', '11h', 
                         '12h', '13h', '14h', '15h', '16h', '17h', '18h', '19h', '20h', '21h', '22h', '23h'],
                data: [45, 23, 12, 8, 15, 34, 89, 234, 456, 678, 890, 987, 
                       1023, 1156, 1234, 1098, 987, 765, 543, 432, 321, 234, 156, 89],
                peakHour: '14:00 (1,234 requests)'
            },
            byTeam: {
                labels: ['Team Alpha', 'Team Beta', 'Team Gamma', 'Team Delta', 'Team Epsilon'],
                data: [5678, 3456, 2345, 1234, 987],
                topTeam: 'Team Alpha (45.6%)'
            },
            byDay: {
                labels: generateDateLabels(),
                data: [2345, 2678, 3567, 3234, 2987, 1234, 876],
                peakDay: '2026-03-03 (3,567 requests)'
            },
            responseStatus: {
                labels: ['Success (200)', 'Rate Limited (429)', 'Auth Error (401)', 'Server Error (500)', 'Timeout', 'Other Errors'],
                data: [12271, 98, 45, 23, 15, 6],
                successRate: '98.5% (12,271 successful requests)'
            },
            trend: {
                labels: generateDateLabels(),
                datasets: [
                    { label: 'Team Alpha', data: [1200, 1350, 1500, 1400, 1300, 600, 400] },
                    { label: 'Team Beta', data: [800, 900, 1100, 1000, 950, 400, 300] },
                    { label: 'Team Gamma', data: [500, 600, 700, 650, 600, 300, 200] },
                    { label: 'Team Delta', data: [300, 400, 500, 450, 400, 200, 150] }
                ]
            }
        },
        users: [
            { email: 'john.doe@example.com', person: 'John Doe', team: 'Team Alpha', requests: 1234, tokens: 245600, cost: 12.28 },
            { email: 'jane.smith@example.com', person: 'Jane Smith', team: 'Team Beta', requests: 987, tokens: 197400, cost: 9.87 },
            { email: 'bob.johnson@example.com', person: 'Bob Johnson', team: 'Team Alpha', requests: 756, tokens: 151200, cost: 7.56 },
            { email: 'alice.williams@example.com', person: 'Alice Williams', team: 'Team Gamma', requests: 654, tokens: 130800, cost: 6.54 },
            { email: 'charlie.brown@example.com', person: 'Charlie Brown', team: 'Team Delta', requests: 543, tokens: 108600, cost: 5.43 },
            { email: 'diana.prince@example.com', person: 'Diana Prince', team: 'Team Beta', requests: 432, tokens: 86400, cost: 4.32 },
            { email: 'edward.norton@example.com', person: 'Edward Norton', team: 'Team Alpha', requests: 321, tokens: 64200, cost: 3.21 },
            { email: 'fiona.apple@example.com', person: 'Fiona Apple', team: 'Team Gamma', requests: 298, tokens: 59600, cost: 2.98 },
            { email: 'george.martin@example.com', person: 'George Martin', team: 'Team Delta', requests: 234, tokens: 46800, cost: 2.34 },
            { email: 'helen.mirren@example.com', person: 'Helen Mirren', team: 'Team Beta', requests: 187, tokens: 37400, cost: 1.87 }
        ]
    };
}

/**
 * Generate date labels for charts
 */
function generateDateLabels() {
    const labels = [];
    const start = new Date(dateRange.start);
    const end = new Date(dateRange.end);
    
    while (start <= end) {
        labels.push(start.toISOString().split('T')[0]);
        start.setDate(start.getDate() + 1);
    }
    
    return labels.slice(0, 7); // Limit to 7 days for display
}

/**
 * Update KPI cards
 */
function updateKPIs(kpis) {
    // Try both with and without 'proxy-' prefix (for standalone page vs integrated tab)
    const elementIds = [
        ['total-requests', 'proxy-total-requests'],
        ['requests-change', 'proxy-requests-change'],
        ['total-tokens', 'proxy-total-tokens'],
        ['tokens-change', 'proxy-tokens-change'],
        ['total-cost', 'proxy-total-cost'],
        ['cost-change', 'proxy-cost-change'],
        ['avg-response-time', 'proxy-avg-response-time'],
        ['response-time-change', 'proxy-response-time-change']
    ];
    
    const values = {
        'total-requests': kpis.totalRequests.toLocaleString(),
        'requests-change': `↑ ${kpis.requestsChange} vs previous period`,
        'total-tokens': (kpis.totalTokens / 1000000).toFixed(1) + 'M',
        'tokens-change': `↑ ${kpis.tokensChange} vs previous period`,
        'total-cost': '$' + kpis.totalCost.toFixed(2),
        'cost-change': `↑ ${kpis.costChange} vs previous period`,
        'avg-response-time': kpis.avgResponseTime.toLocaleString() + 'ms',
        'response-time-change': `↓ ${kpis.responseTimeChange} vs previous period`
    };
    
    for (const [baseId, proxyId] of elementIds) {
        const value = values[baseId];
        // Try proxy- prefixed ID first (for index.html tab), then base ID (for standalone page)
        let element = document.getElementById(proxyId) || document.getElementById(baseId);
        
        if (element) {
            element.textContent = value;
        } else {
            console.warn(`Element with id '${baseId}' or '${proxyId}' not found in DOM`);
        }
    }
}

/**
 * Update all charts
 */
function updateCharts(chartsData) {
    // Destroy existing charts
    Object.values(charts).forEach(chart => chart && chart.destroy());
    charts = {};
    
    // Create charts
    charts.byHour = createBarChart('chart-by-hour', chartsData.byHour.labels, chartsData.byHour.data);
    charts.byTeam = createHorizontalBarChart('chart-by-team', chartsData.byTeam.labels, chartsData.byTeam.data);
    charts.byDay = createBarChart('chart-by-day', chartsData.byDay.labels, chartsData.byDay.data, true);
    charts.responseStatus = createPieChart('chart-response-status', chartsData.responseStatus.labels, chartsData.responseStatus.data);
    charts.trend = createLineChart('chart-trend', chartsData.trend.labels, chartsData.trend.datasets);
    
    // Update footers
    document.getElementById('peak-hour').textContent = chartsData.byHour.peakHour;
    document.getElementById('top-team').textContent = chartsData.byTeam.topTeam;
    document.getElementById('peak-day').textContent = chartsData.byDay.peakDay;
    document.getElementById('success-rate').textContent = chartsData.responseStatus.successRate;
}

/**
 * Create bar chart
 */
function createBarChart(canvasId, labels, data, rotateLabels = false) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Requests',
                data: data,
                backgroundColor: 'rgba(163, 211, 156, 0.7)',
                borderColor: 'rgba(163, 211, 156, 1)',
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(45, 55, 72, 0.95)',
                    padding: 12,
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: '#319795',
                    borderWidth: 1
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(0, 0, 0, 0.05)' },
                    ticks: {
                        callback: function(value) {
                            return value.toLocaleString();
                        }
                    }
                },
                x: {
                    grid: { display: false },
                    ticks: rotateLabels ? {
                        maxRotation: 45,
                        minRotation: 45
                    } : {}
                }
            }
        }
    });
}

/**
 * Create horizontal bar chart
 */
function createHorizontalBarChart(canvasId, labels, data) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Requests',
                data: data,
                backgroundColor: [
                    'rgba(120, 190, 130, 0.7)',
                    'rgba(140, 200, 145, 0.7)',
                    'rgba(163, 211, 156, 0.7)',
                    'rgba(185, 222, 175, 0.7)',
                    'rgba(205, 232, 195, 0.7)'
                ],
                borderColor: [
                    'rgba(120, 190, 130, 1)',
                    'rgba(140, 200, 145, 1)',
                    'rgba(163, 211, 156, 1)',
                    'rgba(185, 222, 175, 1)',
                    'rgba(205, 232, 195, 1)'
                ],
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(45, 55, 72, 0.95)',
                    padding: 12,
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: '#319795',
                    borderWidth: 1
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    grid: { color: 'rgba(0, 0, 0, 0.05)' },
                    ticks: {
                        callback: function(value) {
                            return value.toLocaleString();
                        }
                    }
                },
                y: {
                    grid: { display: false }
                }
            }
        }
    });
}

/**
 * Create pie chart
 */
function createPieChart(canvasId, labels, data) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    return new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: [
                    'rgba(56, 178, 172, 0.8)',
                    'rgba(237, 137, 54, 0.8)',
                    'rgba(229, 62, 62, 0.8)',
                    'rgba(197, 48, 48, 0.8)',
                    'rgba(160, 174, 192, 0.8)',
                    'rgba(113, 128, 150, 0.8)'
                ],
                borderColor: [
                    'rgba(56, 178, 172, 1)',
                    'rgba(237, 137, 54, 1)',
                    'rgba(229, 62, 62, 1)',
                    'rgba(197, 48, 48, 1)',
                    'rgba(160, 174, 192, 1)',
                    'rgba(113, 128, 150, 1)'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        padding: 15,
                        font: { size: 12 },
                        generateLabels: function(chart) {
                            const data = chart.data;
                            if (data.labels.length && data.datasets.length) {
                                return data.labels.map((label, i) => {
                                    const value = data.datasets[0].data[i];
                                    const total = data.datasets[0].data.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return {
                                        text: `${label}: ${value.toLocaleString()} (${percentage}%)`,
                                        fillStyle: data.datasets[0].backgroundColor[i],
                                        hidden: false,
                                        index: i
                                    };
                                });
                            }
                            return [];
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(45, 55, 72, 0.95)',
                    padding: 12,
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: '#319795',
                    borderWidth: 1
                }
            }
        }
    });
}

/**
 * Create line chart
 */
function createLineChart(canvasId, labels, datasets) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    const colors = [
        { border: 'rgba(80, 160, 110, 1)', bg: 'rgba(80, 160, 110, 0.15)' },
        { border: 'rgba(120, 190, 130, 1)', bg: 'rgba(120, 190, 130, 0.15)' },
        { border: 'rgba(163, 211, 156, 1)', bg: 'rgba(163, 211, 156, 0.15)' },
        { border: 'rgba(205, 232, 195, 1)', bg: 'rgba(205, 232, 195, 0.15)' },
        { border: 'rgba(100, 180, 120, 1)', bg: 'rgba(100, 180, 120, 0.15)' },
        { border: 'rgba(140, 200, 150, 1)', bg: 'rgba(140, 200, 150, 0.15)' },
        { border: 'rgba(180, 220, 180, 1)', bg: 'rgba(180, 220, 180, 0.15)' },
        { border: 'rgba(220, 240, 210, 1)', bg: 'rgba(220, 240, 210, 0.15)' }
    ];
    
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets.map((ds, i) => ({
                label: ds.label,
                data: ds.data,
                borderColor: colors[i % colors.length].border,
                backgroundColor: colors[i % colors.length].bg,
                tension: 0.4,
                fill: true,
                borderWidth: 2.5
            }))
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        font: { size: 12 }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(45, 55, 72, 0.95)',
                    padding: 12,
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: '#319795',
                    borderWidth: 1
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(0, 0, 0, 0.05)' },
                    ticks: {
                        callback: function(value) {
                            return value.toLocaleString();
                        }
                    }
                },
                x: {
                    grid: { display: false },
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
}

/**
 * Update usage table
 */
function updateTable() {
    const tbody = document.querySelector('#usage-table tbody');
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    const pageData = usageData.slice(start, end);
    
    if (pageData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6">No data available</td></tr>';
        return;
    }
    
    tbody.innerHTML = pageData.map(user => `
        <tr>
            <td>${user.email}</td>
            <td>${user.person}</td>
            <td>${user.team}</td>
            <td>${user.requests.toLocaleString()}</td>
            <td>${user.tokens.toLocaleString()}</td>
            <td>$${user.cost.toFixed(2)}</td>
        </tr>
    `).join('');
    
    // Update pagination
    updatePagination();
}

/**
 * Update pagination controls
 */
function updatePagination() {
    const start = (currentPage - 1) * pageSize + 1;
    const end = Math.min(currentPage * pageSize, totalUsers);
    
    document.getElementById('pagination-info').textContent = `Showing ${start}-${end} of ${totalUsers} users`;
    document.getElementById('prev-page').disabled = currentPage === 1;
    document.getElementById('next-page').disabled = end >= totalUsers;
}

/**
 * Navigate to previous page
 */
function previousPage() {
    if (currentPage > 1) {
        currentPage--;
        updateTable();
    }
}

/**
 * Navigate to next page
 */
function nextPage() {
    if (currentPage * pageSize < totalUsers) {
        currentPage++;
        updateTable();
    }
}

/**
 * Export data to CSV
 */
function exportToCSV() {
    const headers = ['Email', 'Person', 'Team', 'Requests', 'Tokens', 'Cost (USD)'];
    const rows = usageData.map(user => [
        user.email,
        user.person,
        user.team,
        user.requests,
        user.tokens,
        user.cost.toFixed(2)
    ]);
    
    const csv = [
        headers.join(','),
        ...rows.map(row => row.join(','))
    ].join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `proxy-usage-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
}

/**
 * Check API connection
 */
async function checkConnection() {
    try {
        // TODO: Replace with actual health check
        // await apiCall('/health', 'GET');
        updateConnectionStatus(true);
    } catch (error) {
        console.error('Connection check failed:', error);
        updateConnectionStatus(false);
    }
}

/**
 * Update connection status indicator
 */
function updateConnectionStatus(isConnected) {
    const statusEl = document.getElementById('connection-status');
    if (isConnected) {
        statusEl.className = 'connection-status connected';
        statusEl.textContent = '🟢 Connected to API';
    } else {
        statusEl.className = 'connection-status disconnected';
        statusEl.textContent = '🔴 Disconnected from API';
    }
}

/**
 * Show error message
 */
function showError(message) {
    alert(message); // TODO: Replace with better error UI
}

// ============================================================================
// USAGE TABLE FILTERING AND PAGINATION (NEW STYLE)
// ============================================================================

/**
 * Filter usage table based on search input
 */
function filterUsageTable() {
    const searchTerm = document.getElementById('usage-search').value.toLowerCase();
    
    if (!searchTerm) {
        usagePagination.filteredData = usagePagination.allData;
    } else {
        usagePagination.filteredData = usagePagination.allData.filter(user => {
            return (
                user.email?.toLowerCase().includes(searchTerm) ||
                user.person?.toLowerCase().includes(searchTerm) ||
                user.team?.toLowerCase().includes(searchTerm)
            );
        });
    }
    
    usagePagination.currentPage = 1;
    renderUsagePaginatedTable();
}

/**
 * Render usage table with pagination
 */
function renderUsagePaginatedTable() {
    const tbody = document.querySelector('#usage-table tbody');
    const start = (usagePagination.currentPage - 1) * usagePagination.pageSize;
    const end = start + usagePagination.pageSize;
    const pageData = usagePagination.filteredData.slice(start, end);
    
    if (pageData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No users found</td></tr>';
        updateUsagePaginationControls();
        return;
    }
    
    tbody.innerHTML = pageData.map(user => `
        <tr>
            <td>${user.email}</td>
            <td>${user.person}</td>
            <td>${user.team}</td>
            <td>${user.requests.toLocaleString()}</td>
            <td>${user.tokens.toLocaleString()}</td>
            <td>$${user.cost.toFixed(2)}</td>
        </tr>
    `).join('');
    
    updateUsagePaginationControls();
}

/**
 * Update usage pagination controls
 */
function updateUsagePaginationControls() {
    const total = usagePagination.filteredData.length;
    const totalPages = Math.ceil(total / usagePagination.pageSize);
    const start = total === 0 ? 0 : (usagePagination.currentPage - 1) * usagePagination.pageSize + 1;
    const end = Math.min(usagePagination.currentPage * usagePagination.pageSize, total);
    
    document.getElementById('usage-pagination-info').textContent = `Showing ${start}-${end} of ${total} users`;
    document.getElementById('usage-current-page').textContent = usagePagination.currentPage;
    document.getElementById('usage-total-pages').textContent = totalPages || 1;
    document.getElementById('usage-prev-page').disabled = usagePagination.currentPage === 1;
    document.getElementById('usage-next-page').disabled = usagePagination.currentPage >= totalPages;
}

/**
 * Navigate to previous usage page
 */
function previousUsagePage() {
    if (usagePagination.currentPage > 1) {
        usagePagination.currentPage--;
        renderUsagePaginatedTable();
    }
}

/**
 * Navigate to next usage page
 */
function nextUsagePage() {
    const totalPages = Math.ceil(usagePagination.filteredData.length / usagePagination.pageSize);
    if (usagePagination.currentPage < totalPages) {
        usagePagination.currentPage++;
        renderUsagePaginatedTable();
    }
}
