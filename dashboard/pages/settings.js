import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';
import Navigation from '../components/Navigation';
import FormField from '../components/FormField';
import ToggleSwitch from '../components/ToggleSwitch';
import HelpTooltip from '../components/HelpTooltip';
import { 
  resetFirstRunStatus, 
  getSetupPreferences, 
  saveSetupPreferences,
  resetDismissedTooltips
} from '../utils/firstRunUtils';
import { resetCompletedTours } from '../components/FeatureHighlight';

export default function Settings() {
  const [settings, setSettings] = useState({
    showTooltips: true,
    theme: 'light',
    notifications: {
      email: true,
      browser: true,
      tradeAlerts: true,
      systemAlerts: true
    },
    display: {
      compactView: false,
      darkMode: false,
      highContrastMode: false
    },
    dryRun: false // Initial default, will be fetched
  });
  const [dryRunLoading, setDryRunLoading] = useState(true);
  const [dryRunError, setDryRunError] = useState('');
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const router = useRouter();
  
  useEffect(() => {
    loadSettings();
    loadDryRunStatus();
  }, []);

  const loadDryRunStatus = async () => {
    setDryRunLoading(true);
    setDryRunError('');
    try {
      const token = localStorage.getItem('token');
      // Assuming API_BASE_URL is configured and available
      // If API_BASE_URL is like 'http://localhost:8000', then endpoint is '/api/v1/settings/dry_run'
      // If API_BASE_URL is like 'http://localhost:8000/api/v1', then endpoint is '/settings/dry_run'
      // Based on existing /settings call, it seems API_BASE_URL does not include /api/v1
      const response = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/v1/settings/dry_run`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSettings(prevSettings => ({
        ...prevSettings,
        dryRun: response.data.dry_run
      }));
    } catch (err) {
      console.error('Failed to load dry run status:', err);
      setDryRunError('Failed to load dry run status. Trading mode may not be accurate.');
      // Keep default dryRun state (false) or handle error appropriately
    } finally {
      setDryRunLoading(false);
    }
  };
  
  const loadSettings = async () => {
    setLoading(true);
    setError('');
    
    try {
      // Load user preferences from localStorage
      const preferences = getSetupPreferences();
      if (preferences) {
        setSettings(prevSettings => ({
          ...prevSettings,
          showTooltips: preferences.showTooltips !== false,
          ...(preferences.theme && { theme: preferences.theme }),
          ...(preferences.notifications && { notifications: {
            ...prevSettings.notifications,
            ...preferences.notifications
          }}),
          ...(preferences.display && { display: {
            ...prevSettings.display,
            ...preferences.display
          }})
        }));
      }
      
      // Load settings from API
      const token = localStorage.getItem('token');
      if (token) {
        try {
          const response = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/settings`, {
            headers: { Authorization: `Bearer ${token}` }
          });
          
          // Merge API settings with local settings, excluding dryRun as it's handled separately
          const { dryRun, ...apiSettings } = response.data;
          setSettings(prevSettings => ({
            ...prevSettings,
            ...apiSettings
          }));
        } catch (apiError) {
          console.warn('Could not load settings from API:', apiError);
          // Continue with local settings only
        }
      }
    } catch (err) {
      console.error('Failed to load settings:', err);
      setError('Failed to load settings');
    } finally {
      setLoading(false);
    }
  };
  
  const saveSettings = async () => {
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      // Save user preferences to localStorage
      saveSetupPreferences({
        showTooltips: settings.showTooltips,
        theme: settings.theme,
        notifications: settings.notifications,
        display: settings.display
      });
      
      // Save settings to API
      const token = localStorage.getItem('token');
      if (token) {
        try {
          // Exclude dryRun from general settings save, it's handled by its own endpoint
          const { dryRun, ...settingsToSave } = settings;
          await axios.post(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/settings`, settingsToSave, {
            headers: { Authorization: `Bearer ${token}` }
          });
        } catch (apiError) {
          console.warn('Could not save settings to API:', apiError);
          // Continue with local save only
        }
      }
      
      setSuccess('Settings saved successfully');
    } catch (err) {
      console.error('Failed to save settings:', err);
      setError('Failed to save settings');
    } finally {
      setLoading(false);
    }
  };
  
  const handleResetFirstRun = () => {
    resetFirstRunStatus();
    resetDismissedTooltips();
    resetCompletedTours();
    setShowResetConfirm(false);
    setSuccess('First-run experience has been reset. Reload the page to see the setup wizard.');
  };
  
  const handleToggleChange = (section, key) => (e) => {
    setSettings({
      ...settings,
      [section]: {
        ...settings[section],
        [key]: e.target.checked
      }
    });
  };
  
  const handleDirectToggle = (key) => (e) => {
    setSettings({
      ...settings,
      [key]: e.target.checked
    });
  };
  
  const handleSelectChange = (key) => (e) => {
    setSettings({
      ...settings,
      [key]: e.target.value
    });
  };

  const handleDryRunToggle = async (e) => {
    const newDryRunState = e.target.checked;
    setSettings(prev => ({ ...prev, dryRun: newDryRunState }));
    setDryRunError(''); // Clear previous errors

    try {
      const token = localStorage.getItem('token');
      await axios.put(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/v1/settings/dry_run`,
        { dry_run: newDryRunState },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setSuccess('Dry run mode updated successfully.');
      // Optionally re-fetch to confirm, or trust optimistic update
      // loadDryRunStatus();
    } catch (err) {
      console.error('Failed to update dry run status:', err);
      setDryRunError('Failed to update dry run status. Please try again.');
      // Revert optimistic update
      setSettings(prev => ({ ...prev, dryRun: !newDryRunState }));
      setSuccess('');
    }
  };
  
  if (loading && Object.keys(settings).length === 0) { // General settings loading
    return <div className="p-4">Loading settings...</div>;
  }
  
  return (
    <div className="container mx-auto px-4 py-8">
      <Navigation />
      <h1 className="text-2xl font-bold mb-6">Settings</h1>
      
      {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">{error}</div>}
      {success && <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">{success}</div>}
      
      {/* Reset First-Run Confirmation Modal */}
      {showResetConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-xl max-w-md w-full">
            <h3 className="text-lg font-semibold mb-4">Reset First-Run Experience?</h3>
            <p className="text-gray-600 mb-6">
              This will reset the first-run detection, tooltips, and feature tours. The setup wizard will be shown again the next time you reload the page.
            </p>
            <div className="flex justify-end space-x-4">
              <button
                onClick={() => setShowResetConfirm(false)}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
              >
                Cancel
              </button>
              <button
                onClick={handleResetFirstRun}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
              >
                Reset
              </button>
            </div>
          </div>
        </div>
      )}
      
      <div className="bg-white p-6 rounded-lg shadow-md mb-6">
        <h2 className="text-xl font-semibold mb-4">User Interface</h2>
        
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium">Show Help Tooltips</h3>
              <p className="text-sm text-gray-600">Display helpful tooltips throughout the application</p>
            </div>
            <ToggleSwitch
              id="toggle-tooltips"
              checked={settings.showTooltips}
              onChange={handleDirectToggle('showTooltips')}
            />
          </div>
          
          <div>
            <FormField
              label="Theme"
              tooltip="Choose the application theme"
            >
              <select
                value={settings.theme}
                onChange={handleSelectChange('theme')}
                className="focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md"
              >
                <option value="light">Light</option>
                <option value="dark">Dark</option>
                <option value="system">System Default</option>
              </select>
            </FormField>
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium">Compact View</h3>
              <p className="text-sm text-gray-600">Use a more compact layout with less whitespace</p>
            </div>
            <ToggleSwitch
              id="toggle-compact"
              checked={settings.display.compactView}
              onChange={handleToggleChange('display', 'compactView')}
            />
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium">Dark Mode</h3>
              <p className="text-sm text-gray-600">Use dark color scheme (overrides theme setting)</p>
            </div>
            <ToggleSwitch
              id="toggle-dark-mode"
              checked={settings.display.darkMode}
              onChange={handleToggleChange('display', 'darkMode')}
            />
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium">High Contrast Mode</h3>
              <p className="text-sm text-gray-600">Increase contrast for better accessibility</p>
            </div>
            <ToggleSwitch
              id="toggle-high-contrast"
              checked={settings.display.highContrastMode}
              onChange={handleToggleChange('display', 'highContrastMode')}
            />
          </div>
        </div>
      </div>

      {/* Trading Mode Section */}
      <div className="bg-white p-6 rounded-lg shadow-md mb-6">
        <h2 className="text-xl font-semibold mb-4">Trading Mode</h2>
        {dryRunError && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">{dryRunError}</div>}
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium">Dry Run Mode</h3>
              <p className="text-sm text-gray-600">
                {settings.dryRun
                  ? "Dry Run Mode Active – No live trades will be executed."
                  : "Live Mode Active – Trades will use real funds."}
              </p>
            </div>
            {dryRunLoading ? (
              <p className="text-sm text-gray-500">Loading status...</p>
            ) : (
              <ToggleSwitch
                id="toggle-dry-run"
                checked={settings.dryRun}
                onChange={handleDryRunToggle}
              />
            )}
          </div>
          {settings.dryRun && (
            <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md">
              <p className="text-sm text-yellow-700">
                <strong>Warning:</strong> While Dry Run Mode is active, the bot will simulate trades without using real funds.
                Ensure this is your intended setting before disabling it for live trading.
              </p>
            </div>
          )}
           {!settings.dryRun && !dryRunLoading && (
            <div className="p-3 bg-green-50 border border-green-200 rounded-md">
              <p className="text-sm text-green-700">
                <strong>Live Trading Active:</strong> The bot is configured to execute trades with real funds.
                Monitor your account and strategies closely.
              </p>
            </div>
          )}
        </div>
      </div>
      
      <div className="bg-white p-6 rounded-lg shadow-md mb-6">
        <h2 className="text-xl font-semibold mb-4">Notifications</h2>
        
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium">Email Notifications</h3>
              <p className="text-sm text-gray-600">Receive notifications via email</p>
            </div>
            <ToggleSwitch
              id="toggle-email"
              checked={settings.notifications.email}
              onChange={handleToggleChange('notifications', 'email')}
            />
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium">Browser Notifications</h3>
              <p className="text-sm text-gray-600">Receive notifications in your browser</p>
            </div>
            <ToggleSwitch
              id="toggle-browser"
              checked={settings.notifications.browser}
              onChange={handleToggleChange('notifications', 'browser')}
            />
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium">Trade Alerts</h3>
              <p className="text-sm text-gray-600">Receive alerts for trade executions</p>
            </div>
            <ToggleSwitch
              id="toggle-trade-alerts"
              checked={settings.notifications.tradeAlerts}
              onChange={handleToggleChange('notifications', 'tradeAlerts')}
            />
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium">System Alerts</h3>
              <p className="text-sm text-gray-600">Receive alerts for system events</p>
            </div>
            <ToggleSwitch
              id="toggle-system-alerts"
              checked={settings.notifications.systemAlerts}
              onChange={handleToggleChange('notifications', 'systemAlerts')}
            />
          </div>
        </div>
      </div>
      
      <div className="bg-white p-6 rounded-lg shadow-md mb-6">
        <h2 className="text-xl font-semibold mb-4">Reset Options</h2>
        
        <div className="space-y-6">
          <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-100">
            <h3 className="font-medium text-yellow-800 mb-2">Reset First-Run Experience</h3>
            <p className="text-sm text-yellow-700 mb-4">
              This will reset the first-run detection, tooltips, and feature tours. The setup wizard will be shown again the next time you reload the page.
            </p>
            <button
              onClick={() => setShowResetConfirm(true)}
              className="px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700"
            >
              Reset First-Run Experience
            </button>
          </div>
        </div>
      </div>
      
      <div className="flex justify-end">
        <button
          onClick={saveSettings}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </div>
  );
}