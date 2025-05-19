import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';
import Navigation from '../components/Navigation';
import ConfigWizardStep from '../components/ConfigWizardStep';
import StepProgressBar from '../components/StepProgressBar';
import FormField from '../components/FormField';
import ToggleSwitch from '../components/ToggleSwitch';
// HelpTooltip might be used per-field if needed, but removed generic one for now
// import HelpTooltip from '../components/HelpTooltip';
import { resetFirstRunStatus, markFirstRunComplete } from '../utils/firstRunUtils';
import '../styles/config-wizard.css';

export default function ConfigWizard() {
  const [currentStep, setCurrentStep] = useState(1);
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [formErrors, setFormErrors] = useState({}); // Added for field validation errors
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const router = useRouter();
  
  const steps = [
    { label: 'Services' },
    { label: 'Database' },
    { label: 'Security' },
    { label: 'Logging' },
    { label: 'Review' }
  ];
  
  const totalSteps = steps.length;
  
  useEffect(() => {
    fetchConfig();
  }, []);
  
  const fetchConfig = async () => {
    setLoading(true);
    setError('');
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        router.push('/login');
        return;
      }
      
      const response = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/v1/config`, { // Ensure API_BASE_URL is correctly accessed
        headers: { Authorization: `Bearer ${token}` }
      });
      
      setConfig(response.data);
    } catch (err) {
      console.error('Failed to fetch configuration:', err);
      setError(err.response?.data?.message || err.response?.data?.detail || 'Failed to load configuration. Please ensure the API is running and accessible.');
      if (err.response?.status === 401) {
        router.push('/login');
      }
    } finally {
      setLoading(false);
    }
  };
  
  const handleSaveConfig = async () => {
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        router.push('/login');
        return;
      }
      
      await axios.post(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/v1/config`, config, { // Ensure API_BASE_URL is correctly accessed
        headers: { Authorization: `Bearer ${token}` }
      });
      
      markFirstRunComplete(true); // Mark setup as complete
      setSuccess('Configuration saved successfully! The application is now configured.');
      // Optionally, redirect or inform the user
      // router.push('/'); // Redirect to dashboard or home
    } catch (err) {
      console.error('Failed to save configuration:', err);
      setError(err.response?.data?.message || err.response?.data?.detail || 'Failed to save configuration. Please check your inputs and try again.');
    } finally {
      setLoading(false);
    }
  };
  
  const nextStep = () => {
    if (currentStep < totalSteps) {
      // Basic validation before proceeding (example for database URL on step 2)
      if (currentStep === 2 && (!config?.database?.url || config.database.url.trim() === '')) {
        setFormErrors(prev => ({ ...prev, database: { ...prev.database, url: 'Database URL is required.' } }));
        return; // Prevent moving to next step
      }
      setCurrentStep(currentStep + 1);
      setError(''); // Clear general error when moving step
      setSuccess(''); // Clear success message
    }
  };
  
  const prevStep = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
      setError(''); // Clear error
      setSuccess(''); // Clear success
    }
  };
  
  const goToStep = (step) => {
    if (step >= 1 && step <= totalSteps) {
      // Allow navigation to completed, current, or the immediate next step if current is not the last
      const canNavigate = (step < currentStep) || (step === currentStep) || (step === currentStep + 1 && currentStep < totalSteps);
      if(canNavigate) {
        setCurrentStep(step);
        setError('');
        setSuccess('');
      }
    }
  };
  
  const handleResetFirstRun = () => {
    resetFirstRunStatus();
    setShowResetConfirm(false);
    setSuccess('First-run experience has been reset. Reload the page to see the setup wizard again.');
    // Optionally, force a reload or redirect to re-trigger first-run logic
    // router.reload(); 
  };

  const handleInputChange = (section, field, value, serviceName = null) => {
    // Clear specific field error on change
    setFormErrors(prevErrors => {
      const newSectionErrors = { ...(prevErrors[section] || {}) };
      delete newSectionErrors[field];
      if (serviceName && prevErrors.services && prevErrors.services[serviceName]) {
        const newServiceErrors = { ...(prevErrors.services[serviceName] || {}) };
        delete newServiceErrors[field];
        return { ...prevErrors, services: { ...prevErrors.services, [serviceName]: newServiceErrors }, [section]: newSectionErrors };
      }
      return { ...prevErrors, [section]: newSectionErrors };
    });

    setConfig(prevConfig => {
      if (serviceName) {
        return {
          ...prevConfig,
          services: {
            ...prevConfig.services,
            [serviceName]: {
              ...prevConfig.services[serviceName],
              [field]: value
            }
          }
        };
      }
      return {
        ...prevConfig,
        [section]: {
          ...prevConfig[section],
          [field]: value
        }
      };
    });
  };

  if (loading && !config) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="p-6 bg-white rounded-lg shadow-xl text-center">
          <svg className="animate-spin h-8 w-8 text-indigo-600 mx-auto mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p className="text-lg font-medium text-gray-700">Loading configuration...</p>
        </div>
      </div>
    );
  }
  
  if (error && !config && currentStep === 1) { // Only show full page error if config fails to load initially
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
        <div className="p-6 bg-white rounded-lg shadow-xl text-center max-w-md">
          <svg className="h-12 w-12 text-red-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <h3 className="text-xl font-semibold text-red-700 mb-2">Configuration Error</h3>
          <p className="text-sm text-gray-600 mb-4">{error}</p>
          <button
            onClick={fetchConfig}
            className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            Retry Loading
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <Navigation />
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
        <div className="bg-white shadow-2xl rounded-xl overflow-hidden">
          <div className="px-6 py-5 sm:px-8 lg:px-10 border-b border-gray-200 bg-gray-50">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center">
              <h1 className="text-2xl sm:text-3xl font-bold text-gray-800">Configuration Wizard</h1>
              <button
                onClick={() => setShowResetConfirm(true)}
                className="mt-3 sm:mt-0 text-sm text-indigo-600 hover:text-indigo-700 flex items-center font-medium py-1 px-2 rounded-md hover:bg-indigo-50 transition-colors"
              >
                <svg className="w-4 h-4 mr-1.5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                  <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
                </svg>
                Reset First-Run
              </button>
            </div>
          </div>

          <div className="px-6 py-6 sm:p-8 lg:p-10">
            {error && (
              <div className="bg-red-50 border-l-4 border-red-500 text-red-800 p-4 mb-6 rounded-md shadow-md" role="alert">
                <div className="flex">
                  <div className="py-1"><svg className="fill-current h-6 w-6 text-red-600 mr-3" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><path d="M2.93 17.07A10 10 0 1 1 17.07 2.93 10 10 0 0 1 2.93 17.07zM11.414 10l2.829-2.828-1.415-1.415L10 8.586 7.172 5.757 5.757 7.172 8.586 10l-2.829 2.828 1.415 1.415L10 11.414l2.828 2.829 1.415-1.415L11.414 10z"/></svg></div>
                  <div>
                    <p className="font-bold text-red-700">Error</p>
                    <p className="text-sm">{error}</p>
                  </div>
                </div>
              </div>
            )}
            {success && (
              <div className="bg-green-50 border-l-4 border-green-500 text-green-800 p-4 mb-6 rounded-md shadow-md" role="alert">
                 <div className="flex">
                  <div className="py-1"><svg className="fill-current h-6 w-6 text-green-600 mr-3" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><path d="M2.93 17.07A10 10 0 1 1 17.07 2.93 10 10 0 0 1 2.93 17.07zm12.73-1.41A8 8 0 1 0 4.34 4.34a8 8 0 0 0 11.32 11.32zM6.7 9.29L9 11.6l4.3-4.3 1.4 1.42L9 14.4l-3.7-3.7 1.4-1.42z"/></svg></div>
                  <div>
                    <p className="font-bold text-green-700">Success</p>
                    <p className="text-sm">{success}</p>
                  </div>
                </div>
              </div>
            )}

            {showResetConfirm && (
              <div className="fixed inset-0 bg-gray-700 bg-opacity-60 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
                <div className="bg-white p-6 sm:p-8 rounded-lg shadow-xl max-w-md w-full">
                  <h3 className="text-xl font-semibold mb-4 text-gray-800">Reset First-Run Experience?</h3>
                  <p className="text-gray-600 mb-6 text-sm">
                    This action will reset the first-run detection. The setup wizard will be shown again the next time you load the application. This is useful for testing or re-configuring from scratch.
                  </p>
                  <div className="flex justify-end space-x-3">
                    <button
                      onClick={() => setShowResetConfirm(false)}
                      className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-opacity-50 text-sm font-medium"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleResetFirstRun}
                      className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 text-sm font-medium"
                    >
                      Confirm Reset
                    </button>
                  </div>
                </div>
              </div>
            )}

            <div className="mb-8 sm:mb-12">
              <StepProgressBar
                steps={steps}
                currentStep={currentStep}
                goToStep={goToStep}
              />
            </div>
            
            <div className="bg-white rounded-lg relative">
              <ConfigWizardStep
                title="Services Configuration"
                description="Enable and configure the microservices that power your CryptoBot."
                isActive={currentStep === 1}
              >
                <div className="space-y-8">
                  {config && config.services && Object.keys(config.services).map((serviceName) => (
                    <div 
                      key={serviceName} 
                      className={`p-5 sm:p-6 border rounded-xl shadow-lg transition-all duration-300 ease-in-out ${config.services[serviceName].enabled ? 'border-indigo-300 bg-indigo-50/70' : 'border-gray-200 bg-gray-50 hover:shadow-xl'}`}
                    >
                      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-5">
                        <h3 className={`text-xl font-semibold ${config.services[serviceName].enabled ? 'text-indigo-700' : 'text-gray-700'}`}>
                          {serviceName.charAt(0).toUpperCase() + serviceName.slice(1)} Service
                        </h3>
                        <div className="mt-3 sm:mt-0">
                          <ToggleSwitch
                            id={`toggle-${serviceName}`}
                            checked={config.services[serviceName].enabled}
                            onChange={(e) => handleInputChange('services', 'enabled', e.target.checked, serviceName)}
                            label={config.services[serviceName].enabled ? "Enabled" : "Disabled"}
                          />
                        </div>
                      </div>
                      
                      {config.services[serviceName].enabled && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-5 pt-5 border-t border-indigo-200 border-dashed mt-5">
                          <FormField
                            label="Host Address"
                            tooltip="The network hostname or IP address for this service (e.g., localhost, 0.0.0.0)."
                          >
                            <input
                              type="text"
                              value={config.services[serviceName].host || ''}
                              onChange={(e) => handleInputChange('services', 'host', e.target.value, serviceName)}
                              className="mt-1 block w-full px-3.5 py-2.5 bg-white border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm transition-shadow"
                              placeholder="e.g., localhost"
                            />
                          </FormField>
                          
                          <FormField
                            label="Port Number"
                            tooltip="The network port this service will listen on (1-65535)."
                          >
                            <input
                              type="number"
                              min="1"
                              max="65535"
                              value={config.services[serviceName].port || ''}
                              onChange={(e) => {
                                const portVal = e.target.value === '' ? '' : parseInt(e.target.value);
                                handleInputChange('services', 'port', portVal, serviceName);
                              }}
                              onBlur={(e) => {
                                const portVal = parseInt(e.target.value);
                                if (e.target.value !== '' && (isNaN(portVal) || portVal < 1 || portVal > 65535)) {
                                  handleInputChange('services', 'port', config.services[serviceName].port || 80, serviceName); // Revert or set default
                                }
                              }}
                              className="mt-1 block w-full px-3.5 py-2.5 bg-white border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm transition-shadow"
                              placeholder="e.g., 8080"
                            />
                          </FormField>
                          
                          <FormField
                            label="Worker Processes"
                            tooltip="Number of worker processes to run for this service. More workers can handle more concurrent requests."
                          >
                            <input
                              type="number"
                              min="1"
                              max="16"
                              value={config.services[serviceName].workers || 1}
                              onChange={(e) => {
                                const workersVal = e.target.value === '' ? '' : parseInt(e.target.value);
                                if (workersVal === '' || (workersVal >=1 && workersVal <=16) ) {
                                   handleInputChange('services', 'workers', workersVal === '' ? '' : Math.max(1, workersVal), serviceName);
                                }
                              }}
                               className="mt-1 block w-full px-3.5 py-2.5 bg-white border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm transition-shadow"
                              placeholder="e.g., 4"
                            />
                          </FormField>
                          
                          <FormField
                            label="Service Description"
                            tooltip="A brief description of what this service does."
                          >
                            <input
                              type="text"
                              value={config.services[serviceName].description || ''}
                              onChange={(e) => handleInputChange('services', 'description', e.target.value, serviceName)}
                              className="mt-1 block w-full px-3.5 py-2.5 bg-white border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm transition-shadow"
                              placeholder="e.g., Handles authentication"
                            />
                          </FormField>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </ConfigWizardStep>
        
              <ConfigWizardStep
                title="Database Configuration"
                description="Set up the connection to your primary database."
                isActive={currentStep === 2}
              >
                <div className="p-5 sm:p-6 border rounded-xl shadow-lg bg-white">
                  <div className="space-y-6">
                    <FormField
                      label="Database URL"
                      tooltip="Full connection string for your database (e.g., postgresql://user:pass@host:port/dbname)."
                      helpText="Example for PostgreSQL: postgresql://user:secret@localhost:5432/cryptobot_db. For SQLite: sqlite:///./cryptobot.db"
                    >
                      <input
                        type="text"
                        id="db-url"
                        value={config?.database?.url || ''}
                        onChange={(e) => handleInputChange('database', 'url', e.target.value)}
                        onBlur={(e) => { // Add onBlur validation
                          if (!e.target.value.trim()) {
                            setFormErrors(prev => ({ ...prev, database: { ...prev.database, url: 'Database URL is required.' } }));
                          } else {
                            setFormErrors(prev => ({ ...prev, database: { ...prev.database, url: null } }));
                          }
                        }}
                        className={`mt-1 block w-full px-3.5 py-2.5 bg-white border rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm transition-shadow ${formErrors.database?.url ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : 'border-gray-300'}`}
                        placeholder="e.g., postgresql://user:pass@localhost/dbname"
                        aria-describedby="db-url-error"
                      />
                      {formErrors.database?.url && (
                        <p className="mt-1.5 text-xs text-red-600" id="db-url-error">
                          {formErrors.database.url}
                        </p>
                      )}
                    </FormField>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-5">
                      <FormField
                        label="Connection Pool Size"
                        tooltip="Number of connections to keep open in the pool."
                      >
                        <input
                          type="number"
                          min="1"
                          max="100"
                          value={config?.database?.pool_size || ''}
                          onChange={(e) => {
                            const val = e.target.value === '' ? '' : parseInt(e.target.value);
                            if (val === '' || (val >=1 && val <=100)) {
                               handleInputChange('database', 'pool_size', val);
                            }
                          }}
                          className="mt-1 block w-full px-3.5 py-2.5 bg-white border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm transition-shadow"
                          placeholder="e.g., 10"
                        />
                      </FormField>
                      
                      <FormField
                        label="Max Overflow Connections"
                        tooltip="Maximum number of connections that can be opened beyond the pool size."
                      >
                        <input
                          type="number"
                          min="0"
                          max="50"
                          value={config?.database?.max_overflow || ''}
                           onChange={(e) => {
                            const val = e.target.value === '' ? '' : parseInt(e.target.value);
                            if (val === '' || (val >=0 && val <=50)) {
                               handleInputChange('database', 'max_overflow', val);
                            }
                          }}
                          className="mt-1 block w-full px-3.5 py-2.5 bg-white border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm transition-shadow"
                          placeholder="e.g., 5"
                        />
                      </FormField>
                    </div>
                    
                    <div className="pt-4">
                       <ToggleSwitch
                        id="echo-sql"
                        checked={config?.database?.echo || false}
                        onChange={(e) => handleInputChange('database', 'echo', e.target.checked)}
                        label="Echo SQL Statements"
                        tooltip="Log all SQL statements executed by the ORM. Useful for debugging but can be verbose in production."
                      />
                    </div>
                  </div>
                </div>
              </ConfigWizardStep>
        
              <ConfigWizardStep
                title="Security Configuration"
                description="Strengthen your application's security posture with these settings."
                isActive={currentStep === 3}
              >
                <div className="p-5 sm:p-6 border rounded-xl shadow-lg bg-white">
                  <div className="space-y-6">
                    <FormField
                      label="JWT Secret Key"
                      tooltip="A strong, unique secret key for signing JWT tokens. Keep this highly confidential."
                      helpText="Use a long, random string. You can use the 'Generate' button for a new one. Store this securely."
                    >
                      <div className="relative mt-1">
                        <input
                          type="password"
                          autoComplete="new-password"
                          value={config?.security?.secret_key || ''}
                          onChange={(e) => handleInputChange('security', 'secret_key', e.target.value)}
                          className="block w-full px-3.5 py-2.5 bg-white border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm pr-28 transition-shadow"
                          placeholder="Enter or generate a strong secret key"
                        />
                        <button
                          type="button"
                          onClick={() => {
                            const randomKey = Array.from(window.crypto.getRandomValues(new Uint8Array(32)))
                              .map(b => b.toString(16).padStart(2, '0'))
                              .join('');
                            handleInputChange('security', 'secret_key', randomKey);
                          }}
                          className="absolute inset-y-0 right-0 flex items-center px-4 text-sm font-medium text-indigo-700 bg-indigo-100 rounded-r-lg hover:bg-indigo-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors"
                        >
                          Generate
                        </button>
                      </div>
                    </FormField>
                    
                    <FormField
                      label="Token Expiration (seconds)"
                      tooltip="Duration for which JWT tokens remain valid after issuance."
                      helpText="Common values: 3600 (1 hour), 86400 (1 day), 604800 (1 week)."
                    >
                      <input
                        type="number"
                        min="60"
                        value={config?.security?.token_expiration || ''}
                        onChange={(e) => {
                            const val = e.target.value === '' ? '' : parseInt(e.target.value);
                            if (val === '' || val >=60) {
                               handleInputChange('security', 'token_expiration', val);
                            }
                        }}
                        className="mt-1 block w-full px-3.5 py-2.5 bg-white border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm transition-shadow"
                        placeholder="e.g., 3600"
                      />
                    </FormField>
                    
                    <div className="pt-4">
                       <ToggleSwitch
                        id="enable-rate-limiting"
                        checked={config?.security?.enable_rate_limiting || false}
                        onChange={(e) => handleInputChange('security', 'enable_rate_limiting', e.target.checked)}
                        label="Enable API Rate Limiting"
                        tooltip="Protect your API endpoints from abuse by limiting request rates."
                      />
                    </div>
                    
                    {config?.security?.enable_rate_limiting && (
                      <div className="pl-0 sm:pl-6 mt-4 space-y-5 border-l-0 sm:border-l-4 border-indigo-200/70">
                        <FormField
                          label="Default Rate Limit"
                          tooltip="Default rate limit string (e.g., '100/minute', '20/second', '1000/hour')."
                        >
                          <input
                            type="text"
                            value={config?.security?.rate_limit_default || '100/minute'}
                            onChange={(e) => handleInputChange('security', 'rate_limit_default', e.target.value)}
                            className="mt-1 block w-full px-3.5 py-2.5 bg-white border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm transition-shadow"
                            placeholder="e.g., 100/minute"
                          />
                        </FormField>
                      </div>
                    )}
                  </div>
                </div>
              </ConfigWizardStep>
        
              <ConfigWizardStep
                title="Logging Configuration"
                description="Define how application logs are generated, stored, and their verbosity."
                isActive={currentStep === 4}
              >
                <div className="p-5 sm:p-6 border rounded-xl shadow-lg bg-white">
                  <div className="space-y-6">
                    <FormField
                      label="Log Level"
                      tooltip="Minimum severity level for messages to be logged."
                      helpText="DEBUG is verbose, CRITICAL is for severe errors only. INFO is a good default for production."
                    >
                      <select
                        value={config?.logging?.level || 'INFO'}
                        onChange={(e) => handleInputChange('logging', 'level', e.target.value)}
                        className="mt-1 block w-full pl-3.5 pr-10 py-2.5 bg-white border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm transition-shadow appearance-none"
                      >
                        <option value="DEBUG">DEBUG</option>
                        <option value="INFO">INFO</option>
                        <option value="WARNING">WARNING</option>
                        <option value="ERROR">ERROR</option>
                        <option value="CRITICAL">CRITICAL</option>
                      </select>
                    </FormField>
                    
                    <FormField
                      label="Log File Path"
                      tooltip="Absolute or relative path to the log file. Leave empty to disable file logging."
                      helpText="Example: logs/cryptobot.log. Ensure the directory is writable by the application."
                    >
                      <input
                        type="text"
                        value={config?.logging?.file_path || ''}
                        onChange={(e) => handleInputChange('logging', 'file_path', e.target.value)}
                        className="mt-1 block w-full px-3.5 py-2.5 bg-white border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm transition-shadow"
                        placeholder="e.g., logs/app.log or /var/log/app.log"
                      />
                    </FormField>
                    
                    <div className="pt-4">
                      <ToggleSwitch
                        id="log-to-console"
                        checked={config?.logging?.log_to_console !== undefined ? config.logging.log_to_console : true}
                        onChange={(e) => handleInputChange('logging', 'log_to_console', e.target.checked)}
                        label="Log to Console"
                        tooltip="Output logs to the standard console (stdout/stderr) in addition to (or instead of) file logging."
                      />
                    </div>
                  </div>
                </div>
              </ConfigWizardStep>
        
              <ConfigWizardStep
                title="Review Configuration"
                description="Carefully review all your settings below before saving. This configuration will be applied to your CryptoBot."
                isActive={currentStep === 5}
              >
                <div className="bg-gray-50 p-5 sm:p-6 rounded-xl border border-gray-200 shadow-inner">
                  <h4 className="text-lg font-semibold text-gray-800 mb-4">Current Configuration Summary:</h4>
                  {config ? (
                    <pre className="text-xs sm:text-sm whitespace-pre-wrap break-all bg-white p-4 sm:p-5 rounded-lg border border-gray-300 overflow-auto max-h-[30rem] shadow-sm">
                      {JSON.stringify(config, null, 2)}
                    </pre>
                  ) : (
                    <p className="text-gray-500">Configuration data is not available for review.</p>
                  )}
                </div>
              </ConfigWizardStep>
        
              <div className="mt-10 pt-8 border-t border-gray-300">
                <div className="flex flex-col sm:flex-row justify-between items-center gap-3">
                  <button
                    onClick={prevStep}
                    disabled={currentStep === 1 || loading}
                    className="w-full sm:w-auto px-6 py-2.5 text-sm font-medium text-gray-700 bg-gray-200 rounded-lg hover:bg-gray-300 disabled:opacity-60 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-1 transition-colors"
                  >
                    Previous
                  </button>
                  
                  {currentStep === totalSteps ? (
                    <button
                      onClick={() => {
                        let canSave = true;
                        const newErrors = { services: {}, database: {}, security: {}, logging: {} }; // Initialize all sections
                        
                        // Validate Services
                        if (config && config.services) {
                          Object.keys(config.services).forEach(serviceName => {
                            if (config.services[serviceName].enabled) {
                              if (!config.services[serviceName].host?.trim()) {
                                newErrors.services[serviceName] = { ...newErrors.services[serviceName], host: 'Host is required.' }; canSave = false;
                              }
                              if (!config.services[serviceName].port) {
                                newErrors.services[serviceName] = { ...newErrors.services[serviceName], port: 'Port is required.' }; canSave = false;
                              } else if (config.services[serviceName].port < 1 || config.services[serviceName].port > 65535) {
                                newErrors.services[serviceName] = { ...newErrors.services[serviceName], port: 'Port must be 1-65535.' }; canSave = false;
                              }
                            }
                          });
                        }

                        // Validate Database
                        if (!config?.database?.url || config.database.url.trim() === '') {
                          newErrors.database = { ...newErrors.database, url: 'Database URL is required.' }; canSave = false;
                        } else {
                          try { new URL(config.database.url); } catch (_) {
                            newErrors.database = { ...newErrors.database, url: 'Invalid URL format.' }; canSave = false;
                          }
                        }
                        if (config?.database?.pool_size && (config.database.pool_size < 1 || config.database.pool_size > 100)) {
                          newErrors.database = { ...newErrors.database, pool_size: 'Pool size must be 1-100.' }; canSave = false;
                        }

                        // Validate Security
                        if (!config?.security?.secret_key || config.security.secret_key.trim() === '') {
                          newErrors.security = { ...newErrors.security, secret_key: 'JWT Secret Key is required.' }; canSave = false;
                        }
                        if (config?.security?.token_expiration && config.security.token_expiration < 60) {
                          newErrors.security = { ...newErrors.security, token_expiration: 'Token expiration must be at least 60s.' }; canSave = false;
                        }
                        
                        // Validate Logging
                        if (config?.logging?.level && !['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'].includes(config.logging.level.toUpperCase())) {
                          newErrors.logging = { ...newErrors.logging, level: 'Invalid log level.'}; canSave = false;
                        }
                        if (config?.logging?.retention_days && config.logging.retention_days < 1) {
                            newErrors.logging = { ...newErrors.logging, retention_days: 'Retention must be at least 1 day.'}; canSave = false;
                        }

                        setFormErrors(newErrors);
                        if (canSave) {
                          handleSaveConfig();
                        } else {
                          setError("Please correct all errors before saving. Check all steps for highlighted fields.");
                        }
                      }}
                      disabled={loading || !config }
                      className="w-full sm:w-auto px-6 py-2.5 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-60 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 transition-colors"
                    >
                      {loading ? (
                        <span className="flex items-center justify-center">
                          <svg className="animate-spin -ml-1 mr-2.5 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          Saving...
                        </span>
                      ) : 'Save Configuration'}
                    </button>
                  ) : (
                    <button
                      onClick={() => {
                        let canProceed = true;
                        const newErrors = { ...formErrors };
                        setError(''); // Clear general error first

                        if (currentStep === 1) { // Services step validation
                          newErrors.services = {}; // Reset service errors for current validation
                          if (config && config.services) {
                            Object.keys(config.services).forEach(serviceName => {
                              if (config.services[serviceName].enabled) {
                                if (!config.services[serviceName].host?.trim()) {
                                  newErrors.services[serviceName] = { ...newErrors.services[serviceName], host: 'Host is required.' }; canProceed = false;
                                }
                                if (!config.services[serviceName].port) {
                                  newErrors.services[serviceName] = { ...newErrors.services[serviceName], port: 'Port is required.' }; canProceed = false;
                                } else if (config.services[serviceName].port < 1 || config.services[serviceName].port > 65535) {
                                  newErrors.services[serviceName] = { ...newErrors.services[serviceName], port: 'Port must be 1-65535.' }; canProceed = false;
                                }
                              }
                            });
                          }
                        } else if (currentStep === 2) { // Database step validation
                          newErrors.database = {}; // Reset database errors
                          if (!config?.database?.url || config.database.url.trim() === '') {
                            newErrors.database = { ...newErrors.database, url: 'Database URL is required.' }; canProceed = false;
                          } else {
                             try { new URL(config.database.url); } catch (_) {
                               newErrors.database = { ...newErrors.database, url: 'Invalid URL format.' }; canProceed = false;
                             }
                          }
                          if (config?.database?.pool_size && (config.database.pool_size < 1 || config.database.pool_size > 100)) {
                              newErrors.database = { ...newErrors.database, pool_size: 'Pool size must be 1-100.' }; canProceed = false;
                          }
                        } else if (currentStep === 3) { // Security step
                          newErrors.security = {}; // Reset security errors
                          if (!config?.security?.secret_key || config.security.secret_key.trim() === '') {
                              newErrors.security = { ...newErrors.security, secret_key: 'JWT Secret Key is required.' }; canProceed = false;
                          }
                          if (config?.security?.token_expiration && config.security.token_expiration < 60) {
                              newErrors.security = { ...newErrors.security, token_expiration: 'Token expiration must be at least 60s.' }; canProceed = false;
                          }
                        } else if (currentStep === 4) { // Logging step
                            newErrors.logging = {}; // Reset logging errors
                            if (config?.logging?.level && !['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'].includes(config.logging.level.toUpperCase())) {
                                newErrors.logging = { ...newErrors.logging, level: 'Invalid log level.'}; canProceed = false;
                            }
                            if (config?.logging?.retention_days && config.logging.retention_days < 1) {
                                newErrors.logging = { ...newErrors.logging, retention_days: 'Retention must be at least 1 day.'}; canProceed = false;
                            }
                        }
                        setFormErrors(prev => ({...prev, ...newErrors})); // Merge new errors for the current step
                        if (canProceed) {
                          nextStep(); // Call original nextStep
                        } else {
                          setError("Please correct the highlighted errors before proceeding.");
                        }
                      }}
                      disabled={loading || !config}
                      className="w-full sm:w-auto px-6 py-2.5 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 transition-colors"
                    >
                      Next
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}