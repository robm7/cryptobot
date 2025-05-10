/**
 * Performance Dashboard JavaScript
 * 
 * This file handles the functionality of the performance dashboard, including:
 * - Fetching performance data
 * - Updating the UI
 * - Handling configuration changes
 */

// Charts
let cpuChart;
let memoryChart;
let diskChart;
let networkChart;
let cacheChart;
let queryStatsChart;

// Refresh interval
let refreshInterval = 30000; // 30 seconds
let refreshTimer;

// Last updated timestamp
let lastUpdated = new Date();

// Initialize the dashboard
document.addEventListener('DOMContentLoaded', function() {
    // Initialize charts
    initializeCharts();
    
    // Load initial data
    loadDashboardData();
    
    // Set up refresh timer
    startRefreshTimer();
    
    // Set up event listeners
    setupEventListeners();
});

/**
 * Initialize all charts
 */
function initializeCharts() {
    // CPU Chart
    const cpuCtx = document.getElementById('cpu-chart').getContext('2d');
    cpuChart = new Chart(cpuCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'CPU Usage (%)',
                data: [],
                borderColor: '#28a745',
                backgroundColor: 'rgba(40, 167, 69, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'CPU Usage (%)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Time'
                    }
                }
            }
        }
    });
    
    // Memory Chart
    const memoryCtx = document.getElementById('memory-chart').getContext('2d');
    memoryChart = new Chart(memoryCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Memory Usage (MB)',
                data: [],
                borderColor: '#17a2b8',
                backgroundColor: 'rgba(23, 162, 184, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Memory Usage (MB)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Time'
                    }
                }
            }
        }
    });
    
    // Disk Chart
    const diskCtx = document.getElementById('disk-chart').getContext('2d');
    diskChart = new Chart(diskCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Read (MB/s)',
                    data: [],
                    borderColor: '#fd7e14',
                    backgroundColor: 'rgba(253, 126, 20, 0.1)',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.4
                },
                {
                    label: 'Write (MB/s)',
                    data: [],
                    borderColor: '#6f42c1',
                    backgroundColor: 'rgba(111, 66, 193, 0.1)',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Disk I/O (MB/s)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Time'
                    }
                }
            }
        }
    });
    
    // Network Chart
    const networkCtx = document.getElementById('network-chart').getContext('2d');
    networkChart = new Chart(networkCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Received (MB/s)',
                    data: [],
                    borderColor: '#20c997',
                    backgroundColor: 'rgba(32, 201, 151, 0.1)',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.4
                },
                {
                    label: 'Sent (MB/s)',
                    data: [],
                    borderColor: '#e83e8c',
                    backgroundColor: 'rgba(232, 62, 140, 0.1)',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Network I/O (MB/s)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Time'
                    }
                }
            }
        }
    });
    
    // Cache Chart
    const cacheCtx = document.getElementById('cache-chart').getContext('2d');
    cacheChart = new Chart(cacheCtx, {
        type: 'pie',
        data: {
            labels: ['Hits', 'Misses'],
            datasets: [{
                data: [0, 0],
                backgroundColor: ['#28a745', '#dc3545'],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
    
    // Query Stats Chart
    const queryStatsCtx = document.getElementById('query-stats-chart').getContext('2d');
    queryStatsChart = new Chart(queryStatsCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Average Query Time (ms)',
                data: [],
                backgroundColor: 'rgba(23, 162, 184, 0.7)',
                borderColor: '#17a2b8',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Average Time (ms)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Query'
                    }
                }
            }
        }
    });
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    // Navigation
    document.getElementById('dashboard-link').addEventListener('click', function(e) {
        e.preventDefault();
        showDashboardView();
    });
    
    document.getElementById('config-link').addEventListener('click', function(e) {
        e.preventDefault();
        showConfigView();
    });
    
    document.getElementById('reports-link').addEventListener('click', function(e) {
        e.preventDefault();
        // TODO: Implement reports view
    });
    
    // Refresh button
    document.getElementById('refresh-btn').addEventListener('click', function(e) {
        e.preventDefault();
        loadDashboardData();
    });
    
    // Apply profile button
    document.getElementById('apply-profile-btn').addEventListener('click', function() {
        const profile = document.getElementById('profile-select').value;
        applyProfile(profile);
    });
    
    // Save config button
    document.getElementById('save-config-btn').addEventListener('click', function() {
        saveConfiguration();
    });
    
    // Reset config button
    document.getElementById('reset-config-btn').addEventListener('click', function() {
        loadConfiguration();
    });
}

/**
 * Show dashboard view
 */
function showDashboardView() {
    document.getElementById('dashboard-view').style.display = 'block';
    document.getElementById('config-view').style.display = 'none';
    
    document.getElementById('dashboard-link').classList.add('active');
    document.getElementById('config-link').classList.remove('active');
    document.getElementById('reports-link').classList.remove('active');
    
    // Refresh data
    loadDashboardData();
}

/**
 * Show configuration view
 */
function showConfigView() {
    document.getElementById('dashboard-view').style.display = 'none';
    document.getElementById('config-view').style.display = 'block';
    
    document.getElementById('dashboard-link').classList.remove('active');
    document.getElementById('config-link').classList.add('active');
    document.getElementById('reports-link').classList.remove('active');
    
    // Load configuration
    loadConfiguration();
}

/**
 * Start refresh timer
 */
function startRefreshTimer() {
    // Clear existing timer
    if (refreshTimer) {
        clearInterval(refreshTimer);
    }
    
    // Start new timer
    refreshTimer = setInterval(function() {
        loadDashboardData();
    }, refreshInterval);
}

/**
 * Load dashboard data
 */
function loadDashboardData() {
    // Show loading indicator
    // TODO: Implement loading indicator
    
    // Fetch data from API
    fetch('/api/v1/performance/stats')
        .then(response => response.json())
        .then(data => {
            updateDashboard(data);
        })
        .catch(error => {
            console.error('Error fetching performance data:', error);
            // TODO: Show error message
        });
}

/**
 * Update dashboard with new data
 */
function updateDashboard(data) {
    // Update last updated timestamp
    lastUpdated = new Date();
    document.getElementById('last-updated').textContent = `Last updated: ${lastUpdated.toLocaleTimeString()}`;
    
    // Update overview metrics
    updateOverviewMetrics(data);
    
    // Update bottlenecks table
    updateBottlenecksTable(data.bottlenecks);
    
    // Update slow queries table
    updateSlowQueriesTable(data.slow_queries);
    
    // Update charts
    updateCharts(data);
}

/**
 * Update overview metrics
 */
function updateOverviewMetrics(data) {
    // Average response time
    const avgResponseTime = data.function_stats && Object.keys(data.function_stats).length > 0
        ? Object.values(data.function_stats).reduce((sum, stat) => sum + (stat.avg_time || 0), 0) / Object.keys(data.function_stats).length * 1000
        : 0;
    
    document.getElementById('avg-response-time').textContent = `${avgResponseTime.toFixed(2)} ms`;
    
    const avgResponseTimeBar = document.getElementById('avg-response-time-bar');
    avgResponseTimeBar.style.width = `${Math.min(avgResponseTime / 10, 100)}%`;
    
    if (avgResponseTime > 500) {
        avgResponseTimeBar.className = 'progress-bar bg-danger';
    } else if (avgResponseTime > 200) {
        avgResponseTimeBar.className = 'progress-bar bg-warning';
    } else {
        avgResponseTimeBar.className = 'progress-bar bg-success';
    }
    
    // Cache hit rate
    const cacheHitRate = data.cache_stats && data.cache_stats.hits + data.cache_stats.misses > 0
        ? (data.cache_stats.hits / (data.cache_stats.hits + data.cache_stats.misses) * 100)
        : 0;
    
    document.getElementById('cache-hit-rate').textContent = `${cacheHitRate.toFixed(2)}%`;
    document.getElementById('cache-hit-rate-bar').style.width = `${cacheHitRate}%`;
    
    // Memory usage
    const memoryUsage = data.memory_stats && data.memory_stats.current_memory_usage
        ? data.memory_stats.current_memory_usage / (1024 * 1024) // Convert to MB
        : 0;
    
    document.getElementById('memory-usage').textContent = `${memoryUsage.toFixed(2)} MB`;
    
    const memoryUsageBar = document.getElementById('memory-usage-bar');
    const memoryPercent = data.memory_stats && data.memory_stats.memory_usage && data.memory_stats.memory_usage.system_percent
        ? data.memory_stats.memory_usage.system_percent
        : 0;
    
    memoryUsageBar.style.width = `${memoryPercent}%`;
    
    if (memoryPercent > 80) {
        memoryUsageBar.className = 'progress-bar bg-danger';
    } else if (memoryPercent > 60) {
        memoryUsageBar.className = 'progress-bar bg-warning';
    } else {
        memoryUsageBar.className = 'progress-bar bg-info';
    }
    
    // CPU usage
    const cpuUsage = data.system_stats && data.system_stats.cpu_usage && data.system_stats.cpu_usage.length > 0
        ? data.system_stats.cpu_usage[data.system_stats.cpu_usage.length - 1].value
        : 0;
    
    document.getElementById('cpu-usage').textContent = `${cpuUsage.toFixed(2)}%`;
    
    const cpuUsageBar = document.getElementById('cpu-usage-bar');
    cpuUsageBar.style.width = `${cpuUsage}%`;
    
    if (cpuUsage > 80) {
        cpuUsageBar.className = 'progress-bar bg-danger';
    } else if (cpuUsage > 60) {
        cpuUsageBar.className = 'progress-bar bg-warning';
    } else {
        cpuUsageBar.className = 'progress-bar bg-success';
    }
    
    // Cache hits and misses
    document.getElementById('cache-hits').textContent = data.cache_stats ? data.cache_stats.hits : 0;
    document.getElementById('cache-misses').textContent = data.cache_stats ? data.cache_stats.misses : 0;
}

/**
 * Update bottlenecks table
 */
function updateBottlenecksTable(bottlenecks) {
    const table = document.getElementById('bottlenecks-table').getElementsByTagName('tbody')[0];
    table.innerHTML = '';
    
    if (!bottlenecks || bottlenecks.length === 0) {
        const row = table.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 5;
        cell.textContent = 'No bottlenecks detected';
        cell.className = 'text-center';
        return;
    }
    
    bottlenecks.forEach(bottleneck => {
        const row = table.insertRow();
        
        const typeCell = row.insertCell();
        typeCell.textContent = bottleneck.type;
        
        const nameCell = row.insertCell();
        nameCell.textContent = bottleneck.name;
        
        const avgTimeCell = row.insertCell();
        avgTimeCell.textContent = `${(bottleneck.avg_time * 1000).toFixed(2)} ms`;
        
        const countCell = row.insertCell();
        countCell.textContent = bottleneck.count;
        
        const severityCell = row.insertCell();
        if (bottleneck.severity === 'critical') {
            severityCell.innerHTML = '<span class="badge bg-danger">Critical</span>';
        } else {
            severityCell.innerHTML = '<span class="badge bg-warning">Warning</span>';
        }
    });
}

/**
 * Update slow queries table
 */
function updateSlowQueriesTable(slowQueries) {
    const table = document.getElementById('slow-queries-table').getElementsByTagName('tbody')[0];
    table.innerHTML = '';
    
    if (!slowQueries || slowQueries.length === 0) {
        const row = table.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 4;
        cell.textContent = 'No slow queries detected';
        cell.className = 'text-center';
        return;
    }
    
    slowQueries.forEach(query => {
        const row = table.insertRow();
        
        const queryCell = row.insertCell();
        queryCell.textContent = query.query;
        
        const avgTimeCell = row.insertCell();
        avgTimeCell.textContent = `${(query.avg_time * 1000).toFixed(2)} ms`;
        
        const countCell = row.insertCell();
        countCell.textContent = query.count;
        
        const maxTimeCell = row.insertCell();
        maxTimeCell.textContent = `${(query.max_time * 1000).toFixed(2)} ms`;
    });
}

/**
 * Update charts with new data
 */
function updateCharts(data) {
    // CPU Chart
    if (data.system_stats && data.system_stats.cpu_usage) {
        const cpuData = data.system_stats.cpu_usage;
        cpuChart.data.labels = cpuData.map(point => {
            const date = new Date(point.timestamp);
            return date.toLocaleTimeString();
        });
        cpuChart.data.datasets[0].data = cpuData.map(point => point.value);
        cpuChart.update();
    }
    
    // Memory Chart
    if (data.system_stats && data.system_stats.memory_usage) {
        const memoryData = data.system_stats.memory_usage;
        memoryChart.data.labels = memoryData.map(point => {
            const date = new Date(point.timestamp);
            return date.toLocaleTimeString();
        });
        memoryChart.data.datasets[0].data = memoryData.map(point => point.value / (1024 * 1024)); // Convert to MB
        memoryChart.update();
    }
    
    // Disk Chart
    if (data.system_stats && data.system_stats.disk_usage) {
        const diskData = data.system_stats.disk_usage;
        diskChart.data.labels = diskData.map(point => {
            const date = new Date(point.timestamp);
            return date.toLocaleTimeString();
        });
        
        // Calculate read/write rates
        const readData = [];
        const writeData = [];
        
        for (let i = 1; i < diskData.length; i++) {
            const prevPoint = diskData[i - 1];
            const currPoint = diskData[i];
            
            const prevTime = new Date(prevPoint.timestamp).getTime();
            const currTime = new Date(currPoint.timestamp).getTime();
            const timeDiff = (currTime - prevTime) / 1000; // in seconds
            
            const readDiff = (currPoint.read_bytes - prevPoint.read_bytes) / (1024 * 1024); // in MB
            const writeDiff = (currPoint.write_bytes - prevPoint.write_bytes) / (1024 * 1024); // in MB
            
            const readRate = readDiff / timeDiff; // MB/s
            const writeRate = writeDiff / timeDiff; // MB/s
            
            readData.push(readRate);
            writeData.push(writeRate);
        }
        
        // Add a placeholder for the first point
        readData.unshift(0);
        writeData.unshift(0);
        
        diskChart.data.datasets[0].data = readData;
        diskChart.data.datasets[1].data = writeData;
        diskChart.update();
    }
    
    // Network Chart
    if (data.system_stats && data.system_stats.network_usage) {
        const networkData = data.system_stats.network_usage;
        networkChart.data.labels = networkData.map(point => {
            const date = new Date(point.timestamp);
            return date.toLocaleTimeString();
        });
        
        // Calculate received/sent rates
        const recvData = [];
        const sentData = [];
        
        for (let i = 1; i < networkData.length; i++) {
            const prevPoint = networkData[i - 1];
            const currPoint = networkData[i];
            
            const prevTime = new Date(prevPoint.timestamp).getTime();
            const currTime = new Date(currPoint.timestamp).getTime();
            const timeDiff = (currTime - prevTime) / 1000; // in seconds
            
            const recvDiff = (currPoint.bytes_recv - prevPoint.bytes_recv) / (1024 * 1024); // in MB
            const sentDiff = (currPoint.bytes_sent - prevPoint.bytes_sent) / (1024 * 1024); // in MB
            
            const recvRate = recvDiff / timeDiff; // MB/s
            const sentRate = sentDiff / timeDiff; // MB/s
            
            recvData.push(recvRate);
            sentData.push(sentRate);
        }
        
        // Add a placeholder for the first point
        recvData.unshift(0);
        sentData.unshift(0);
        
        networkChart.data.datasets[0].data = recvData;
        networkChart.data.datasets[1].data = sentData;
        networkChart.update();
    }
    
    // Cache Chart
    if (data.cache_stats) {
        cacheChart.data.datasets[0].data = [
            data.cache_stats.hits || 0,
            data.cache_stats.misses || 0
        ];
        cacheChart.update();
    }
    
    // Query Stats Chart
    if (data.database_stats) {
        const queryStats = Object.entries(data.database_stats)
            .map(([query, stats]) => ({
                query: query.substring(0, 30) + (query.length > 30 ? '...' : ''),
                avgTime: stats.avg_time * 1000 // Convert to ms
            }))
            .sort((a, b) => b.avgTime - a.avgTime)
            .slice(0, 10); // Top 10 queries
        
        queryStatsChart.data.labels = queryStats.map(stat => stat.query);
        queryStatsChart.data.datasets[0].data = queryStats.map(stat => stat.avgTime);
        queryStatsChart.update();
    }
}

/**
 * Load configuration
 */
function loadConfiguration() {
    fetch('/api/v1/performance/config')
        .then(response => response.json())
        .then(config => {
            updateConfigForm(config);
        })
        .catch(error => {
            console.error('Error fetching configuration:', error);
            // TODO: Show error message
        });
}

/**
 * Update configuration form
 */
function updateConfigForm(config) {
    // Query Optimizer
    if (config.query_optimizer) {
        document.getElementById('query-optimizer-enabled').checked = config.query_optimizer.enabled;
        document.getElementById('auto-optimize').checked = config.query_optimizer.auto_optimize;
        document.getElementById('auto-index').checked = config.query_optimizer.auto_index;
        document.getElementById('slow-query-threshold').value = config.query_optimizer.slow_query_threshold;
        document.getElementById('index-creation-threshold').value = config.query_optimizer.index_creation_threshold;
    }
    
    // Cache Manager
    if (config.cache_manager) {
        document.getElementById('cache-manager-enabled').checked = config.cache_manager.enabled;
        document.getElementById('memory-cache-fallback').checked = config.cache_manager.memory_cache_fallback;
        document.getElementById('default-ttl').value = config.cache_manager.default_ttl;
        document.getElementById('cache-prefix').value = config.cache_manager.cache_prefix;
        document.getElementById('memory-cache-max-size').value = config.cache_manager.memory_cache_max_size;
        
        if (config.cache_manager.redis) {
            document.getElementById('redis-host').value = config.cache_manager.redis.host;
            document.getElementById('redis-port').value = config.cache_manager.redis.port;
            document.getElementById('redis-db').value = config.cache_manager.redis.db;
            document.getElementById('redis-ssl').checked = config.cache_manager.redis.ssl;
        }
    }
    
    // Rate Limiter
    if (config.rate_limiter) {
        document.getElementById('rate-limiter-enabled').checked = config.rate_limiter.enabled;
        document.getElementById('wait-on-limit').checked = config.rate_limiter.wait_on_limit;
    }
    
    // Memory Optimizer
    if (config.memory_optimizer) {
        document.getElementById('memory-optimizer-enabled').checked = config.memory_optimizer.enabled;
        
        if (config.memory_optimizer.monitoring) {
            document.getElementById('monitoring-enabled').checked = config.memory_optimizer.monitoring.enabled;
            document.getElementById('monitoring-interval').value = config.memory_optimizer.monitoring.interval;
            document.getElementById('warning-threshold').value = config.memory_optimizer.monitoring.warning_threshold;
            document.getElementById('critical-threshold').value = config.memory_optimizer.monitoring.critical_threshold;
        }
        
        if (config.memory_optimizer.tracemalloc) {
            document.getElementById('tracemalloc-enabled').checked = config.memory_optimizer.tracemalloc.enabled;
        }
    }
    
    // Performance Monitor
    if (config.performance_monitor) {
        document.getElementById('performance-monitor-enabled').checked = config.performance_monitor.enabled;
        
        if (config.performance_monitor.monitoring) {
            document.getElementById('perf-monitoring-enabled').checked = config.performance_monitor.monitoring.enabled;
            document.getElementById('perf-monitoring-interval').value = config.performance_monitor.monitoring.interval;
        }
        
        if (config.performance_monitor.thresholds) {
            document.getElementById('perf-warning-threshold').value = config.performance_monitor.thresholds.warning;
            document.getElementById('perf-critical-threshold').value = config.performance_monitor.thresholds.critical;
        }
    }
}

/**
 * Save configuration
 */
function saveConfiguration() {
    // Build configuration object
    const config = {
        query_optimizer: {
            enabled: document.getElementById('query-optimizer-enabled').checked,
            auto_optimize: document.getElementById('auto-optimize').checked,
            auto_index: document.getElementById('auto-index').checked,
            slow_query_threshold: parseFloat(document.getElementById('slow-query-threshold').value),
            index_creation_threshold: parseInt(document.getElementById('index-creation-threshold').value)
        },
        cache_manager: {
            enabled: document.getElementById('cache-manager-enabled').checked,
            memory_cache_fallback: document.getElementById('memory-cache-fallback').checked,
            default_ttl: parseInt(document.getElementById('default-ttl').value),
            cache_prefix: document.getElementById('cache-prefix').value,
            memory_cache_max_size: parseInt(document.getElementById('memory-cache-max-size').value),
            redis: {
                host: document.getElementById('redis-host').value,
                port: parseInt(document.getElementById('redis-port').value),
                db: parseInt(document.getElementById('redis-db').value),
                ssl: document.getElementById('redis-ssl').checked
            }
        },
        rate_limiter: {
            enabled: document.getElementById('rate-limiter-enabled').checked,
            wait_on_limit: document.getElementById('wait-on-limit').checked
        },
        memory_optimizer: {
            enabled: document.getElementById('memory-optimizer-enabled').checked,
            monitoring: {
                enabled: document.getElementById('monitoring-enabled').checked,
                interval: parseInt(document.getElementById('monitoring-interval').value),
                warning_threshold: parseFloat(document.getElementById('warning-threshold').value),
                critical_threshold: parseFloat(document.getElementById('critical-threshold').value)
            },
            tracemalloc: {
                enabled: document.getElementById('tracemalloc-enabled').checked
            }
        },
        performance_monitor: {
            enabled: document.getElementById('performance-monitor-enabled').checked,
            monitoring: {
                enabled: document.getElementById('perf-monitoring-enabled').checked,
                interval: parseInt(document.getElementById('perf-monitoring-interval').value)
            },
            thresholds: {
                warning: parseFloat(document.getElementById('perf-warning-threshold').value),
                critical: parseFloat(document.getElementById('perf-critical-threshold').value)
            }
        }
    };
    
    // Send configuration to API
    fetch('/api/v1/performance/config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(config)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Configuration saved successfully');
        } else {
            alert('Error saving configuration: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error saving configuration:', error);
        alert('Error saving configuration');
    });
}

/**
 * Apply profile
 */
function applyProfile(profile) {
    fetch(`/api/v1/performance/profile/${profile}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(`Profile "${profile}" applied successfully`);
            loadConfiguration();
        } else {
            alert('Error applying profile: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error applying profile:', error);
        alert('Error applying profile');
    });
}