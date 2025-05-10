// API Key Management Frontend Logic
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const currentKeyInfo = document.getElementById('current-key-info');
    const rotateBtn = document.getElementById('rotate-key-btn');
    const revokeAllBtn = document.getElementById('revoke-all-btn');
    const revokeCurrentBtn = document.getElementById('revoke-current-btn');
    const rotationDaysInput = document.getElementById('rotation-days');
    const saveSettingsBtn = document.getElementById('save-settings-btn');
    const notifyExpiry = document.getElementById('notify-expiry');
    const notifyRotation = document.getElementById('notify-rotation');
    const notifyEmergency = document.getElementById('notify-emergency');

    // Load current key info
    function loadKeyInfo() {
        fetch('/api-keys')
            .then(response => response.json())
            .then(data => {
                // Find the active key
                const activeKey = data.keys.find(key => key.status === 'active');
                
                if (activeKey) {
                    currentKeyInfo.innerHTML = `
                        <p><strong>Key ID:</strong> ${activeKey.id}</p>
                        <p><strong>Exchange:</strong> ${activeKey.exchange}</p>
                        <p><strong>Description:</strong> ${activeKey.description}</p>
                        <p><strong>Created:</strong> ${new Date(activeKey.created_at).toLocaleString()}</p>
                        <p><strong>Expires:</strong> ${new Date(activeKey.expires_at).toLocaleString()}</p>
                        <p><strong>Status:</strong> <span class="status-active">Active</span></p>
                        <p><strong>Version:</strong> ${activeKey.version}</p>
                        ${activeKey.last_used ? `<p><strong>Last Used:</strong> ${new Date(activeKey.last_used).toLocaleString()}</p>` : ''}
                    `;
                    
                    // Update key history table
                    updateKeyHistoryTable(data.keys);
                    
                    // Show expiration warning if key expires within 7 days
                    const expiresIn = Math.floor((new Date(activeKey.expires_at) - new Date()) / (1000 * 60 * 60 * 24));
                    if (expiresIn <= 7) {
                        currentKeyInfo.innerHTML += `
                            <div class="expiration-warning">
                                <i class="icon-warning"></i>
                                <span>This key expires in ${expiresIn} days. Consider rotating it soon.</span>
                            </div>
                        `;
                    }
                } else {
                    currentKeyInfo.innerHTML = `
                        <p>No active API key found. Create a new one.</p>
                        <button id="create-key-btn" class="btn btn-primary">Create New Key</button>
                    `;
                    
                    // Add event listener for create button
                    document.getElementById('create-key-btn').addEventListener('click', createNewKey);
                }
            })
            .catch(error => console.error('Error loading key info:', error));
    }
    
    // Update key history table
    function updateKeyHistoryTable(keys) {
        const tableBody = document.querySelector('#key-history-table tbody');
        tableBody.innerHTML = '';
        
        keys.forEach(key => {
            const row = document.createElement('tr');
            
            // Add status class
            row.classList.add(`status-${key.status}`);
            
            row.innerHTML = `
                <td>${key.id.substring(0, 8)}...</td>
                <td>${new Date(key.created_at).toLocaleDateString()}</td>
                <td>${new Date(key.expires_at).toLocaleDateString()}</td>
                <td><span class="status-badge ${key.status}">${key.status}</span></td>
                <td>
                    ${key.status === 'active' ? `<button class="btn btn-sm btn-primary rotate-btn" data-id="${key.id}">Rotate</button>` : ''}
                    ${key.status === 'active' || key.status === 'rotating' ? `<button class="btn btn-sm btn-danger revoke-btn" data-id="${key.id}">Revoke</button>` : ''}
                    <button class="btn btn-sm btn-secondary details-btn" data-id="${key.id}">Details</button>
                </td>
            `;
            
            tableBody.appendChild(row);
        });
        
        // Add event listeners for buttons
        document.querySelectorAll('.rotate-btn').forEach(btn => {
            btn.addEventListener('click', () => rotateKey(btn.dataset.id));
        });
        
        document.querySelectorAll('.revoke-btn').forEach(btn => {
            btn.addEventListener('click', () => revokeKey(btn.dataset.id));
        });
        
        document.querySelectorAll('.details-btn').forEach(btn => {
            btn.addEventListener('click', () => showKeyDetails(btn.dataset.id));
        });
    }

    // Create new API key
    function createNewKey() {
        // Show modal for key creation
        const exchange = prompt('Enter exchange name:');
        const description = prompt('Enter key description:');
        
        if (!exchange || !description) {
            alert('Exchange and description are required');
            return;
        }
        
        const keyData = {
            exchange,
            description,
            is_test: false,
            expiry_days: parseInt(rotationDaysInput.value) || 90
        };
        
        fetch('/api-keys', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(keyData)
        })
        .then(response => {
            if (!response.ok) throw new Error('Failed to create key');
            return response.json();
        })
        .then(data => {
            // Show the new key to the user
            alert(`Your new API key has been created. Please save it now as it won't be shown again:\n\n${data.key}`);
            loadKeyInfo();
        })
        .catch(error => {
            console.error('Error creating key:', error);
            alert('Failed to create API key');
        });
    }
    
    // Rotate specific key
    function rotateKey(keyId) {
        if (!confirm('Are you sure you want to rotate this API key? A new key will be generated and the old one will enter a grace period.')) {
            return;
        }
        
        const rotationData = {
            key_id: keyId,
            grace_period_hours: 24 // Default grace period
        };
        
        fetch('/api-keys/rotate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(rotationData)
        })
        .then(response => {
            if (!response.ok) throw new Error('Failed to rotate key');
            return response.json();
        })
        .then(data => {
            alert(`Your new API key has been created. Please save it now as it won't be shown again:\n\n${data.key}`);
            loadKeyInfo();
        })
        .catch(error => {
            console.error('Error rotating key:', error);
            alert('Failed to rotate API key');
        });
    }
    
    // Rotate button event listener
    rotateBtn.addEventListener('click', () => {
        // Find the active key ID
        fetch('/api-keys')
            .then(response => response.json())
            .then(data => {
                const activeKey = data.keys.find(key => key.status === 'active');
                if (activeKey) {
                    rotateKey(activeKey.id);
                } else {
                    alert('No active key found to rotate');
                }
            })
            .catch(error => {
                console.error('Error finding active key:', error);
                alert('Failed to find active key');
            });
    });

    // Revoke specific key
    function revokeKey(keyId) {
        if (!confirm('Are you sure you want to revoke this API key? This action cannot be undone.')) {
            return;
        }
        
        const reason = prompt('Please provide a reason for revocation:') || 'Manual revocation';
        
        const revocationData = {
            key_id: keyId,
            reason: reason
        };
        
        fetch('/api-keys/revoke', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(revocationData)
        })
        .then(response => {
            if (!response.ok) throw new Error('Failed to revoke key');
            return response.json();
        })
        .then(data => {
            alert('API key revoked successfully');
            loadKeyInfo();
        })
        .catch(error => {
            console.error('Error revoking key:', error);
            alert('Failed to revoke API key');
        });
    }
    
    // Show key details
    function showKeyDetails(keyId) {
        fetch(`/api-keys/${keyId}`)
            .then(response => {
                if (!response.ok) throw new Error('Failed to get key details');
                return response.json();
            })
            .then(key => {
                // Create modal with key details
                const modal = document.createElement('div');
                modal.className = 'modal';
                modal.innerHTML = `
                    <div class="modal-content">
                        <span class="close">&times;</span>
                        <h2>API Key Details</h2>
                        <div class="key-details">
                            <p><strong>ID:</strong> ${key.id}</p>
                            <p><strong>Exchange:</strong> ${key.exchange}</p>
                            <p><strong>Description:</strong> ${key.description}</p>
                            <p><strong>Status:</strong> <span class="status-badge ${key.status}">${key.status}</span></p>
                            <p><strong>Version:</strong> ${key.version}</p>
                            <p><strong>Created:</strong> ${new Date(key.created_at).toLocaleString()}</p>
                            <p><strong>Expires:</strong> ${new Date(key.expires_at).toLocaleString()}</p>
                            ${key.last_used ? `<p><strong>Last Used:</strong> ${new Date(key.last_used).toLocaleString()}</p>` : ''}
                            ${key.rotated_at ? `<p><strong>Rotated At:</strong> ${new Date(key.rotated_at).toLocaleString()}</p>` : ''}
                            ${key.grace_period_ends ? `<p><strong>Grace Period Ends:</strong> ${new Date(key.grace_period_ends).toLocaleString()}</p>` : ''}
                            ${key.revoked_at ? `<p><strong>Revoked At:</strong> ${new Date(key.revoked_at).toLocaleString()}</p>` : ''}
                            ${key.revocation_reason ? `<p><strong>Revocation Reason:</strong> ${key.revocation_reason}</p>` : ''}
                            ${key.compromised_at ? `<p><strong>Compromised At:</strong> ${new Date(key.compromised_at).toLocaleString()}</p>` : ''}
                            ${key.compromise_details ? `<p><strong>Compromise Details:</strong> ${key.compromise_details}</p>` : ''}
                        </div>
                    </div>
                `;
                
                document.body.appendChild(modal);
                
                // Close button functionality
                const closeBtn = modal.querySelector('.close');
                closeBtn.addEventListener('click', () => {
                    document.body.removeChild(modal);
                });
                
                // Close when clicking outside the modal
                window.addEventListener('click', (event) => {
                    if (event.target === modal) {
                        document.body.removeChild(modal);
                    }
                });
            })
            .catch(error => {
                console.error('Error getting key details:', error);
                alert('Failed to get key details');
            });
    }
    
    // Revoke all keys
    revokeAllBtn.addEventListener('click', () => {
        if (confirm('EMERGENCY ACTION: Are you sure you want to revoke ALL API keys? This action cannot be undone.')) {
            // Get all keys
            fetch('/api-keys')
                .then(response => response.json())
                .then(data => {
                    const activeKeys = data.keys.filter(key =>
                        key.status === 'active' || key.status === 'rotating'
                    );
                    
                    if (activeKeys.length === 0) {
                        alert('No active keys to revoke');
                        return;
                    }
                    
                    const reason = prompt('Please provide a reason for emergency revocation:') || 'Emergency revocation';
                    
                    // Revoke each key
                    const revokePromises = activeKeys.map(key => {
                        const revocationData = {
                            key_id: key.id,
                            reason: reason
                        };
                        
                        return fetch('/api-keys/revoke', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(revocationData)
                        });
                    });
                    
                    Promise.all(revokePromises)
                        .then(() => {
                            alert(`Successfully revoked ${activeKeys.length} API keys`);
                            loadKeyInfo();
                        })
                        .catch(error => {
                            console.error('Error revoking all keys:', error);
                            alert('Failed to revoke all keys');
                        });
                })
                .catch(error => {
                    console.error('Error getting keys:', error);
                    alert('Failed to get keys');
                });
        }
    });

    // Revoke current key (emergency)
    revokeCurrentBtn.addEventListener('click', () => {
        if (confirm('EMERGENCY ACTION: Are you sure you want to mark your current API key as COMPROMISED? This will immediately revoke it and trigger security alerts.')) {
            // Find the active key
            fetch('/api-keys')
                .then(response => response.json())
                .then(data => {
                    const activeKey = data.keys.find(key => key.status === 'active');
                    
                    if (!activeKey) {
                        alert('No active key found');
                        return;
                    }
                    
                    const details = prompt('Please provide details about the compromise:');
                    
                    if (!details) {
                        alert('Compromise details are required for security purposes');
                        return;
                    }
                    
                    const compromiseData = {
                        key_id: activeKey.id,
                        details: details
                    };
                    
                    fetch('/api-keys/emergency-revoke', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(compromiseData)
                    })
                    .then(response => {
                        if (!response.ok) throw new Error('Failed to mark key as compromised');
                        return response.json();
                    })
                    .then(data => {
                        alert('API key marked as compromised and revoked. Security team has been notified.');
                        loadKeyInfo();
                    })
                    .catch(error => {
                        console.error('Error marking key as compromised:', error);
                        alert('Failed to mark key as compromised');
                    });
                })
                .catch(error => {
                    console.error('Error finding active key:', error);
                    alert('Failed to find active key');
                });
        }
    });

    // Save settings (just store in localStorage for now)
    saveSettingsBtn.addEventListener('click', () => {
        const settings = {
            rotation_days: parseInt(rotationDaysInput.value) || 90
        };

        // In a real implementation, this would be sent to the server
        localStorage.setItem('api_key_settings', JSON.stringify(settings));
        alert('Settings saved');
    });
    
    // Check for expiring keys
    function checkExpiringKeys() {
        fetch('/api-keys/expiring')
            .then(response => response.json())
            .then(data => {
                if (data.keys.length > 0) {
                    const expiringKeysDiv = document.createElement('div');
                    expiringKeysDiv.className = 'expiring-keys-alert';
                    
                    expiringKeysDiv.innerHTML = `
                        <h3>Expiring API Keys</h3>
                        <p>You have ${data.keys.length} API key(s) expiring within ${data.days_threshold} days:</p>
                        <ul>
                            ${data.keys.map(key => `
                                <li>
                                    ${key.exchange} (${key.description}): Expires on
                                    ${new Date(key.expires_at).toLocaleDateString()}
                                    <button class="btn btn-sm btn-primary rotate-expiring-btn" data-id="${key.id}">Rotate Now</button>
                                </li>
                            `).join('')}
                        </ul>
                    `;
                    
                    document.querySelector('.container').prepend(expiringKeysDiv);
                    
                    // Add event listeners for rotate buttons
                    document.querySelectorAll('.rotate-expiring-btn').forEach(btn => {
                        btn.addEventListener('click', () => rotateKey(btn.dataset.id));
                    });
                }
            })
            .catch(error => console.error('Error checking expiring keys:', error));
    }

    // Initialize
    loadKeyInfo();
    checkExpiringKeys();
    
    // Load settings from localStorage
    try {
        const savedSettings = JSON.parse(localStorage.getItem('api_key_settings'));
        if (savedSettings) {
            rotationDaysInput.value = savedSettings.rotation_days || 90;
        }
    } catch (e) {
        console.error('Error loading settings:', e);
    }
});