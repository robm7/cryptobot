import { useState, useEffect } from 'react';
import axios from 'axios';

export default function NotificationPreferences() {
  const [preferences, setPreferences] = useState(null);
  const [channels, setChannels] = useState([]);
  const [severities, setSeverities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      const token = localStorage.getItem('token');
      if (!token) return;

      // Fetch user preferences
      const prefsRes = await axios.get(`${process.env.API_BASE_URL}/notification-preferences/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setPreferences(prefsRes.data);

      // Fetch available channels
      const channelsRes = await axios.get(`${process.env.API_BASE_URL}/notification-preferences/channels`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setChannels(channelsRes.data);

      // Fetch severity levels
      const severitiesRes = await axios.get(`${process.env.API_BASE_URL}/notification-preferences/severities`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSeverities(severitiesRes.data);
    } catch (err) {
      console.error('Failed to fetch notification preferences:', err);
      setError(err.response?.data?.message || 'Failed to load notification preferences');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      const token = localStorage.getItem('token');
      if (!token) return;

      await axios.put(
        `${process.env.API_BASE_URL}/notification-preferences/me`,
        preferences,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setSuccess('Notification preferences saved successfully');
      setIsEditing(false);
    } catch (err) {
      console.error('Failed to save notification preferences:', err);
      setError(err.response?.data?.message || 'Failed to save notification preferences');
    } finally {
      setSaving(false);
    }
  };

  const handleToggleChannel = (channelId) => {
    setPreferences(prev => {
      const updatedChannels = { ...prev.channels };
      
      // If channel doesn't exist in preferences, add it with default values
      if (!updatedChannels[channelId]) {
        updatedChannels[channelId] = {
          enabled: true,
          min_severity: 'warning'
        };
      } else {
        // Toggle enabled state
        updatedChannels[channelId] = {
          ...updatedChannels[channelId],
          enabled: !updatedChannels[channelId].enabled
        };
      }
      
      return {
        ...prev,
        channels: updatedChannels
      };
    });
  };

  const handleChangeSeverity = (channelId, severity) => {
    setPreferences(prev => {
      const updatedChannels = { ...prev.channels };
      
      if (updatedChannels[channelId]) {
        updatedChannels[channelId] = {
          ...updatedChannels[channelId],
          min_severity: severity
        };
      }
      
      return {
        ...prev,
        channels: updatedChannels
      };
    });
  };

  const handleChangeAddress = (channelId, address) => {
    setPreferences(prev => {
      const updatedChannels = { ...prev.channels };
      
      if (updatedChannels[channelId]) {
        updatedChannels[channelId] = {
          ...updatedChannels[channelId],
          address: address
        };
      }
      
      return {
        ...prev,
        channels: updatedChannels
      };
    });
  };

  const handleToggleAlertType = (alertType) => {
    setPreferences(prev => ({
      ...prev,
      [alertType]: !prev[alertType]
    }));
  };

  const handleChangeQuietHours = (field, value) => {
    // Convert to number or null
    let numValue = value === '' ? null : parseInt(value);
    
    // Validate hour range (0-23)
    if (numValue !== null && (numValue < 0 || numValue > 23)) {
      return;
    }
    
    setPreferences(prev => ({
      ...prev,
      [field]: numValue
    }));
  };

  const handleToggleQuietHoursOverride = () => {
    setPreferences(prev => ({
      ...prev,
      quiet_hours_override_critical: !prev.quiet_hours_override_critical
    }));
  };

  if (loading) {
    return (
      <div className="bg-white p-4 rounded-lg shadow">
        <h2 className="text-lg font-semibold mb-4">Notification Preferences</h2>
        <p className="text-gray-500">Loading preferences...</p>
      </div>
    );
  }

  if (!preferences) {
    return (
      <div className="bg-white p-4 rounded-lg shadow">
        <h2 className="text-lg font-semibold mb-4">Notification Preferences</h2>
        <p className="text-red-500">Failed to load notification preferences</p>
      </div>
    );
  }

  return (
    <div className="bg-white p-4 rounded-lg shadow">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">Notification Preferences</h2>
        {!isEditing ? (
          <button
            onClick={() => setIsEditing(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white py-1 px-3 rounded-md text-sm"
          >
            Edit Preferences
          </button>
        ) : (
          <div className="flex space-x-2">
            <button
              onClick={() => {
                setIsEditing(false);
                fetchData(); // Reset to original values
                setError('');
                setSuccess('');
              }}
              className="bg-gray-200 hover:bg-gray-300 text-gray-800 py-1 px-3 rounded-md text-sm"
              disabled={saving}
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="bg-blue-600 hover:bg-blue-700 text-white py-1 px-3 rounded-md text-sm disabled:opacity-50"
              disabled={saving}
            >
              {saving ? 'Saving...' : 'Save Preferences'}
            </button>
          </div>
        )}
      </div>
      
      {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">{error}</div>}
      {success && <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">{success}</div>}
      
      <div className={isEditing ? '' : 'opacity-75 pointer-events-none'}>
        {/* Notification Channels */}
        <div className="mb-6">
          <h3 className="text-md font-medium mb-3">Notification Channels</h3>
          <div className="space-y-4">
            {channels.map(channel => {
              const channelConfig = preferences.channels[channel.id] || { enabled: false, min_severity: 'warning' };
              return (
                <div key={channel.id} className="border rounded-md p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center">
                      <input
                        type="checkbox"
                        id={`channel-${channel.id}`}
                        checked={channelConfig.enabled || false}
                        onChange={() => handleToggleChannel(channel.id)}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <label htmlFor={`channel-${channel.id}`} className="ml-2 block text-sm font-medium text-gray-700">
                        {channel.name}
                      </label>
                    </div>
                    <span className="text-xs text-gray-500">{channel.description}</span>
                  </div>
                  
                  {channelConfig.enabled && (
                    <div className="pl-6 space-y-3">
                      {/* Channel Address */}
                      {channel.requires_address && (
                        <div>
                          <label htmlFor={`address-${channel.id}`} className="block text-xs font-medium text-gray-700 mb-1">
                            {channel.address_type === 'email' ? 'Email Address' : 
                             channel.address_type === 'phone' ? 'Phone Number' : 
                             channel.address_type === 'slack_id' ? 'Slack User ID' : 
                             channel.address_type === 'url' ? 'Webhook URL' : 'Address'}
                          </label>
                          <input
                            type="text"
                            id={`address-${channel.id}`}
                            value={channelConfig.address || ''}
                            onChange={(e) => handleChangeAddress(channel.id, e.target.value)}
                            className="focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md"
                            placeholder={
                              channel.address_type === 'email' ? 'user@example.com' : 
                              channel.address_type === 'phone' ? '+15551234567' : 
                              channel.address_type === 'slack_id' ? 'U12345678' : 
                              channel.address_type === 'url' ? 'https://example.com/webhook' : ''
                            }
                          />
                        </div>
                      )}
                      
                      {/* Minimum Severity */}
                      <div>
                        <label htmlFor={`severity-${channel.id}`} className="block text-xs font-medium text-gray-700 mb-1">
                          Minimum Alert Severity
                        </label>
                        <select
                          id={`severity-${channel.id}`}
                          value={channelConfig.min_severity || 'warning'}
                          onChange={(e) => handleChangeSeverity(channel.id, e.target.value)}
                          className="focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md"
                        >
                          {severities.map(severity => (
                            <option key={severity.id} value={severity.id}>
                              {severity.name} - {severity.description}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
        
        {/* Alert Types */}
        <div className="mb-6">
          <h3 className="text-md font-medium mb-3">Alert Types</h3>
          <div className="space-y-2">
            <div className="flex items-center">
              <input
                type="checkbox"
                id="reconciliation-alerts"
                checked={preferences.reconciliation_alerts}
                onChange={() => handleToggleAlertType('reconciliation_alerts')}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label htmlFor="reconciliation-alerts" className="ml-2 block text-sm font-medium text-gray-700">
                Reconciliation Alerts
              </label>
            </div>
            
            <div className="flex items-center">
              <input
                type="checkbox"
                id="system-alerts"
                checked={preferences.system_alerts}
                onChange={() => handleToggleAlertType('system_alerts')}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label htmlFor="system-alerts" className="ml-2 block text-sm font-medium text-gray-700">
                System Alerts
              </label>
            </div>
            
            <div className="flex items-center">
              <input
                type="checkbox"
                id="performance-alerts"
                checked={preferences.performance_alerts}
                onChange={() => handleToggleAlertType('performance_alerts')}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label htmlFor="performance-alerts" className="ml-2 block text-sm font-medium text-gray-700">
                Performance Alerts
              </label>
            </div>
          </div>
        </div>
        
        {/* Quiet Hours */}
        <div className="mb-6">
          <h3 className="text-md font-medium mb-3">Quiet Hours</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="quiet-hours-start" className="block text-sm font-medium text-gray-700 mb-1">
                Start Time (24-hour format)
              </label>
              <input
                type="number"
                id="quiet-hours-start"
                min="0"
                max="23"
                value={preferences.quiet_hours_start === null ? '' : preferences.quiet_hours_start}
                onChange={(e) => handleChangeQuietHours('quiet_hours_start', e.target.value)}
                className="focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md"
                placeholder="22"
              />
              <p className="mt-1 text-xs text-gray-500">
                Hour of day (0-23) when quiet hours begin
              </p>
            </div>
            
            <div>
              <label htmlFor="quiet-hours-end" className="block text-sm font-medium text-gray-700 mb-1">
                End Time (24-hour format)
              </label>
              <input
                type="number"
                id="quiet-hours-end"
                min="0"
                max="23"
                value={preferences.quiet_hours_end === null ? '' : preferences.quiet_hours_end}
                onChange={(e) => handleChangeQuietHours('quiet_hours_end', e.target.value)}
                className="focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md"
                placeholder="7"
              />
              <p className="mt-1 text-xs text-gray-500">
                Hour of day (0-23) when quiet hours end
              </p>
            </div>
          </div>
          
          <div className="mt-3">
            <div className="flex items-center">
              <input
                type="checkbox"
                id="override-critical"
                checked={preferences.quiet_hours_override_critical}
                onChange={handleToggleQuietHoursOverride}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label htmlFor="override-critical" className="ml-2 block text-sm font-medium text-gray-700">
                Allow critical alerts during quiet hours
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}