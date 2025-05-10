class APIKeyManager {
    constructor() {
        this.baseUrl = '/api/keys';
        this.initEventListeners();
        this.loadKeyData();
    }

    async loadKeyData() {
        try {
            // Load current key
            const currentKey = await this.fetchCurrentKey();
            this.displayCurrentKey(currentKey);

            // Load key history
            const keyHistory = await this.fetchKeyHistory();
            this.displayKeyHistory(keyHistory);

            // Load upcoming expirations
            const expirations = await this.fetchUpcomingExpirations();
            this.displayExpirations(expirations);

            // Load permissions
            const permissions = await this.fetchPermissions();
            this.displayPermissions(permissions);

        } catch (error) {
            console.error('Failed to load key data:', error);
            this.showError('Failed to load key data. Please try again.');
        }
    }

    initEventListeners() {
        document.getElementById('rotate-key-btn').addEventListener('click', () => this.rotateKey());
        document.getElementById('revoke-key-btn').addEventListener('click', () => this.revokeKey());
        document.getElementById('update-permissions-btn').addEventListener('click', () => this.updatePermissions());
    }

    async fetchCurrentKey() {
        const response = await fetch(`${this.baseUrl}/current`);
        return await response.json();
    }

    async fetchKeyHistory() {
        const response = await fetch(`${this.baseUrl}/history`);
        return await response.json();
    }

    async fetchUpcomingExpirations() {
        const response = await fetch(`${this.baseUrl}/expirations`);
        return await response.json();
    }

    async fetchPermissions() {
        const response = await fetch(`${this.baseUrl}/permissions`);
        return await response.json();
    }

    displayCurrentKey(key) {
        const container = document.getElementById('current-key-container');
        if (!key) {
            container.innerHTML = '<p class="text-danger">No active API key</p>';
            return;
        }

        container.innerHTML = `
            <div class="key-info">
                <p><strong>Key ID:</strong> ${key.id}</p>
                <p><strong>Created:</strong> ${new Date(key.created_at).toLocaleString()}</p>
                <p><strong>Expires:</strong> ${new Date(key.expires_at).toLocaleString()}</p>
                <p><strong>Status:</strong> ${this.getStatusBadge(key)}</p>
                <p><strong>Version:</strong> ${key.version}</p>
            </div>
        `;
    }

    displayKeyHistory(keys) {
        const tbody = document.querySelector('#key-history-table tbody');
        tbody.innerHTML = keys.map(key => `
            <tr>
                <td>${key.id}</td>
                <td>${new Date(key.created_at).toLocaleString()}</td>
                <td>${new Date(key.expires_at).toLocaleString()}</td>
                <td>${this.getStatusBadge(key)}</td>
                <td>${key.version}</td>
            </tr>
        `).join('');
    }

    displayExpirations(expirations) {
        const container = document.getElementById('expiration-alerts');
        if (expirations.length === 0) {
            container.innerHTML = '<div class="alert alert-success">No keys expiring soon</div>';
            return;
        }

        container.innerHTML = expirations.map(key => `
            <div class="alert alert-warning">
                <strong>${key.id}</strong> expires in 
                ${this.getDaysUntilExpiration(key)} days (${new Date(key.expires_at).toLocaleDateString()})
            </div>
        `).join('');
    }

    displayPermissions(permissions) {
        const container = document.getElementById('permissions-container');
        container.innerHTML = `
            <div class="permissions-list">
                ${permissions.map(perm => `
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" 
                               id="perm-${perm}" value="${perm}" 
                               ${perm === '*' ? 'checked disabled' : ''}>
                        <label class="form-check-label" for="perm-${perm}">
                            ${perm}
                        </label>
                    </div>
                `).join('')}
            </div>
        `;
    }

    getStatusBadge(key) {
        if (key.is_revoked) return '<span class="badge bg-danger">Revoked</span>';
        if (!key.is_active) return '<span class="badge bg-warning">Deprecated</span>';
        return '<span class="badge bg-success">Active</span>';
    }

    getDaysUntilExpiration(key) {
        const expires = new Date(key.expires_at);
        const now = new Date();
        return Math.ceil((expires - now) / (1000 * 60 * 60 * 24));
    }

    async rotateKey() {
        try {
            const response = await fetch(`${this.baseUrl}/rotate`, {
                method: 'POST'
            });
            
            if (response.ok) {
                this.showSuccess('Key rotated successfully');
                this.loadKeyData();
            } else {
                throw new Error('Failed to rotate key');
            }
        } catch (error) {
            console.error('Key rotation failed:', error);
            this.showError('Failed to rotate key. Please try again.');
        }
    }

    async revokeKey() {
        if (!confirm('Are you sure you want to revoke this key? This cannot be undone.')) {
            return;
        }

        try {
            const response = await fetch(`${this.baseUrl}/revoke`, {
                method: 'POST'
            });
            
            if (response.ok) {
                this.showSuccess('Key revoked successfully');
                this.loadKeyData();
            } else {
                throw new Error('Failed to revoke key');
            }
        } catch (error) {
            console.error('Key revocation failed:', error);
            this.showError('Failed to revoke key. Please try again.');
        }
    }

    async updatePermissions() {
        const checkboxes = document.querySelectorAll('.permissions-list input[type="checkbox"]:not(:disabled)');
        const selectedPermissions = Array.from(checkboxes)
            .filter(checkbox => checkbox.checked)
            .map(checkbox => checkbox.value);

        try {
            const response = await fetch(`${this.baseUrl}/permissions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ permissions: selectedPermissions })
            });
            
            if (response.ok) {
                this.showSuccess('Permissions updated successfully');
            } else {
                throw new Error('Failed to update permissions');
            }
        } catch (error) {
            console.error('Permission update failed:', error);
            this.showError('Failed to update permissions. Please try again.');
        }
    }

    showSuccess(message) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-success';
        alert.textContent = message;
        document.querySelector('.container').prepend(alert);
        setTimeout(() => alert.remove(), 5000);
    }

    showError(message) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger';
        alert.textContent = message;
        document.querySelector('.container').prepend(alert);
        setTimeout(() => alert.remove(), 5000);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new APIKeyManager();
});