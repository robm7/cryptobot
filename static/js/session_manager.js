/**
 * Session Manager - Handles session management UI and WebSocket communication
 */

class SessionManager {
    constructor() {
        this.socket = null;
        this.sessionsChart = null;
        this.activityChart = null;
        this.initWebSocket();
        this.initCharts();
        this.setupEventListeners();
    }

    initWebSocket() {
        this.socket = new WebSocket(`wss://${window.location.host}/ws/sessions`);
        
        this.socket.onopen = () => {
            console.log('WebSocket connected for session management');
        };

        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            switch(data.type) {
                case 'sessions_update':
                    this.updateSessionsList(data.sessions);
                    this.updateCharts(data.stats);
                    break;
                case 'activity_alert':
                    this.addActivityAlert(data.alert);
                    break;
                case 'session_terminated':
                    this.showNotification('Session terminated successfully');
                    this.loadSessions();
                    break;
            }
        };

        this.socket.onclose = () => {
            console.log('WebSocket disconnected, attempting to reconnect...');
            setTimeout(() => this.initWebSocket(), 5000);
        };
    }

    initCharts() {
        const sessionsCtx = document.getElementById('sessions-chart');
        const activityCtx = document.getElementById('activity-chart');

        this.sessionsChart = new Chart(sessionsCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Active Sessions',
                    data: [],
                    borderColor: 'rgb(59, 130, 246)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: 'Session Activity Over Time'
                    }
                }
            }
        });

        this.activityChart = new Chart(activityCtx, {
            type: 'doughnut',
            data: {
                labels: ['High', 'Medium', 'Low'],
                datasets: [{
                    data: [0, 0, 0],
                    backgroundColor: [
                        'rgb(220, 38, 38)',
                        'rgb(234, 179, 8)',
                        'rgb(37, 99, 235)'
                    ],
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: 'Security Alert Severity'
                    }
                }
            }
        });
    }

    setupEventListeners() {
        document.getElementById('refresh-sessions').addEventListener('click', () => this.loadSessions());
        document.getElementById('terminate-all').addEventListener('click', () => this.terminateAllSessions());
    }

    async loadSessions() {
        try {
            const response = await fetch('/api/auth/sessions', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                }
            });
            const data = await response.json();
            this.updateSessionsList(data.sessions);
            this.updateCharts(data.stats);
        } catch (error) {
            console.error('Failed to load sessions:', error);
            this.showNotification('Failed to load sessions', 'error');
        }
    }

    async loadActivityAlerts() {
        try {
            const response = await fetch('/api/auth/suspicious-activity', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                }
            });
            const data = await response.json();
            this.updateActivityAlerts(data.alerts);
        } catch (error) {
            console.error('Failed to load activity alerts:', error);
        }
    }

    updateSessionsList(sessions) {
        const container = document.getElementById('sessions-list');
        container.innerHTML = sessions.map(session => this.createSessionRow(session)).join('');
    }

    createSessionRow(session) {
        return `
            <tr class="border-b border-gray-700 ${session.is_current ? 'bg-gray-700' : ''} ${session.is_suspicious ? 'bg-red-900 bg-opacity-30' : ''}">
                <td class="px-6 py-4">
                    <div class="flex items-center">
                        <i class="fas ${this.getDeviceIcon(session.device_info)} mr-2"></i>
                        <div>
                            <div class="font-medium">${session.device_info.device || 'Unknown'}</div>
                            <div class="text-xs text-gray-400">${session.device_info.browser || 'Unknown browser'}</div>
                        </div>
                    </div>
                </td>
                <td class="px-6 py-4">
                    ${session.location ? `
                        <div>
                            <div>${session.location.city || 'Unknown'}, ${session.location.country_code || ''}</div>
                            <div class="text-xs text-gray-400">IP: ${session.ip_address}</div>
                        </div>
                    ` : 'Unknown location'}
                </td>
                <td class="px-6 py-4">
                    ${new Date(session.last_activity).toLocaleString()}
                    ${session.is_current ? '<span class="ml-2 text-xs bg-blue-600 px-2 py-1 rounded-full">Current</span>' : ''}
                </td>
                <td class="px-6 py-4">
                    ${this.getStatusBadge(session)}
                </td>
                <td class="px-6 py-4">
                    ${!session.is_current ? `
                        <button onclick="sessionManager.terminateSession('${session.id}')" 
                                class="px-3 py-1 bg-red-600 rounded hover:bg-red-700 transition-colors">
                            Terminate
                        </button>
                    ` : ''}
                </td>
            </tr>
        `;
    }

    updateActivityAlerts(alerts) {
        const container = document.getElementById('alerts-list');
        container.innerHTML = alerts.map(alert => this.createAlertRow(alert)).join('');
    }

    createAlertRow(alert) {
        return `
            <tr class="border-b border-gray-700">
                <td class="px-6 py-4">
                    <span class="font-medium">${alert.activity_type.replace(/_/g, ' ')}</span>
                </td>
                <td class="px-6 py-4">
                    <div class="max-w-xs truncate">${JSON.stringify(alert.details)}</div>
                </td>
                <td class="px-6 py-4">
                    ${new Date(alert.created_at).toLocaleString()}
                </td>
                <td class="px-6 py-4">
                    <span class="px-2 py-1 rounded-full text-xs ${this.getSeverityClass(alert.severity)}">
                        ${alert.severity}
                    </span>
                </td>
                <td class="px-6 py-4">
                    <button onclick="sessionManager.dismissAlert('${alert.id}')" 
                            class="px-3 py-1 bg-gray-600 rounded hover:bg-gray-700 transition-colors">
                        Dismiss
                    </button>
                </td>
            </tr>
        `;
    }

    updateCharts(stats) {
        // Update sessions chart
        this.sessionsChart.data.labels = stats.timestamps.map(ts => new Date(ts).toLocaleTimeString());
        this.sessionsChart.data.datasets[0].data = stats.session_counts;
        this.sessionsChart.update();

        // Update activity chart
        this.activityChart.data.datasets[0].data = [
            stats.high_severity,
            stats.medium_severity,
            stats.low_severity
        ];
        this.activityChart.update();
    }

    async terminateSession(sessionId) {
        if (!confirm('Are you sure you want to terminate this session?')) return;
        
        try {
            await fetch(`/api/auth/sessions/${sessionId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                }
            });
            this.showNotification('Session terminated successfully');
            this.loadSessions();
        } catch (error) {
            console.error('Failed to terminate session:', error);
            this.showNotification('Failed to terminate session', 'error');
        }
    }

    async terminateAllSessions() {
        if (!confirm('This will log you out of all other devices. Continue?')) return;
        
        try {
            await fetch('/api/auth/sessions', {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                }
            });
            this.showNotification('All other sessions terminated');
            this.loadSessions();
        } catch (error) {
            console.error('Failed to terminate sessions:', error);
            this.showNotification('Failed to terminate sessions', 'error');
        }
    }

    async dismissAlert(alertId) {
        try {
            await fetch(`/api/auth/suspicious-activity/${alertId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                }
            });
            this.loadActivityAlerts();
        } catch (error) {
            console.error('Failed to dismiss alert:', error);
        }
    }

    getDeviceIcon(deviceInfo) {
        if (deviceInfo.is_mobile) return 'fa-mobile-alt';
        if (deviceInfo.is_tablet) return 'fa-tablet-alt';
        if (deviceInfo.is_pc) return 'fa-desktop';
        return 'fa-question-circle';
    }

    getStatusBadge(session) {
        if (session.is_suspicious) return '<span class="px-2 py-1 rounded-full text-xs bg-red-600">Suspicious</span>';
        if (!session.is_active) return '<span class="px-2 py-1 rounded-full text-xs bg-gray-600">Inactive</span>';
        return '<span class="px-2 py-1 rounded-full text-xs bg-green-600">Active</span>';
    }

    getSeverityClass(severity) {
        switch(severity.toLowerCase()) {
            case 'high': return 'bg-red-600';
            case 'medium': return 'bg-yellow-600';
            case 'low': return 'bg-blue-600';
            default: return 'bg-gray-600';
        }
    }

    showNotification(message, type = 'success') {
        // Implement notification system or use existing one
        console.log(`${type.toUpperCase()}: ${message}`);
    }
}

// Initialize SessionManager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.sessionManager = new SessionManager();
});