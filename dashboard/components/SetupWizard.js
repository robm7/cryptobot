import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import StepProgressBar from './StepProgressBar';
import ConfigWizardStep from './ConfigWizardStep';
import FormField from './FormField';
import ToggleSwitch from './ToggleSwitch';
import { 
  markFirstRunComplete, 
  saveSetupPreferences, 
  getSampleConfig 
} from '../utils/firstRunUtils';

export default function SetupWizard({ onComplete }) {
  const [currentStep, setCurrentStep] = useState(1);
  const [config, setConfig] = useState(null);
  const [selectedPreset, setSelectedPreset] = useState('basic');
  const [apiKeys, setApiKeys] = useState({
    binance: '',
    coinbase: '',
    kraken: ''
  });
  const [showTooltips, setShowTooltips] = useState(true);
  const router = useRouter();
  
  const steps = [
    { label: 'Welcome' },
    { label: 'Configuration' },
    { label: 'API Keys' },
    { label: 'Preferences' },
    { label: 'Complete' }
  ];
  
  const totalSteps = steps.length;
  
  useEffect(() => {
    // Initialize with basic configuration
    setConfig(getSampleConfig('basic'));
  }, []);
  
  const handlePresetChange = (preset) => {
    setSelectedPreset(preset);
    setConfig(getSampleConfig(preset));
  };
  
  const handleApiKeyChange = (exchange, value) => {
    setApiKeys({
      ...apiKeys,
      [exchange]: value
    });
  };
  
  const handleComplete = () => {
    // Save preferences
    saveSetupPreferences({
      config,
      apiKeys,
      showTooltips
    });
    
    // Mark first run as complete
    markFirstRunComplete(true);
    
    // Call the onComplete callback
    if (onComplete) {
      onComplete();
    }
  };
  
  const nextStep = () => {
    if (currentStep < totalSteps) {
      setCurrentStep(currentStep + 1);
    }
  };
  
  const prevStep = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };
  
  const skipSetup = () => {
    // Mark first run as complete but with default settings
    markFirstRunComplete(true);
    
    // Save basic preferences
    saveSetupPreferences({
      config: getSampleConfig('basic'),
      apiKeys: {},
      showTooltips: true
    });
    
    // Call the onComplete callback
    if (onComplete) {
      onComplete();
    }
  };
  
  if (!config) {
    return <div className="p-4">Loading setup wizard...</div>;
  }
  
  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold mb-2">Welcome to CryptoBot</h1>
        <p className="text-gray-600">Let's get you set up and ready to trade</p>
      </div>
      
      {/* Progress Indicator */}
      <StepProgressBar
        steps={steps}
        currentStep={currentStep}
        goToStep={(step) => setCurrentStep(step)}
      />
      
      {/* Step Content */}
      <div className="bg-white p-6 rounded-lg shadow-md">
        <ConfigWizardStep
          title="Welcome to CryptoBot"
          description="Your automated cryptocurrency trading platform"
          isActive={currentStep === 1}
        >
          <div className="space-y-6">
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-100">
              <h3 className="text-lg font-medium text-blue-800 mb-2">What is CryptoBot?</h3>
              <p className="text-blue-700 mb-4">
                CryptoBot is a powerful platform for automated cryptocurrency trading. It allows you to:
              </p>
              <ul className="list-disc pl-5 text-blue-700 space-y-2">
                <li>Connect to multiple cryptocurrency exchanges</li>
                <li>Create and deploy trading strategies</li>
                <li>Backtest strategies against historical data</li>
                <li>Monitor performance in real-time</li>
                <li>Manage risk with advanced controls</li>
              </ul>
            </div>
            
            <div className="p-4 bg-green-50 rounded-lg border border-green-100">
              <h3 className="text-lg font-medium text-green-800 mb-2">Getting Started</h3>
              <p className="text-green-700 mb-2">
                This setup wizard will guide you through the initial configuration of CryptoBot:
              </p>
              <ol className="list-decimal pl-5 text-green-700 space-y-2">
                <li>Choose a configuration preset</li>
                <li>Set up API keys for exchanges</li>
                <li>Configure your preferences</li>
                <li>Start trading or backtesting</li>
              </ol>
            </div>
          </div>
        </ConfigWizardStep>
        
        <ConfigWizardStep
          title="Configuration Preset"
          description="Choose a configuration preset that matches your needs"
          isActive={currentStep === 2}
        >
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div 
                className={`p-4 rounded-lg border cursor-pointer transition-all ${
                  selectedPreset === 'basic' 
                    ? 'border-blue-500 bg-blue-50 shadow-md' 
                    : 'border-gray-200 hover:border-blue-300 hover:bg-blue-50'
                }`}
                onClick={() => handlePresetChange('basic')}
              >
                <h3 className="text-lg font-medium mb-2">Basic Trading</h3>
                <p className="text-sm text-gray-600 mb-4">
                  Optimized for simple trading strategies with minimal configuration.
                </p>
                <ul className="text-xs text-gray-500 space-y-1">
                  <li>• Trade execution enabled</li>
                  <li>• Market data service enabled</li>
                  <li>• Strategy service enabled</li>
                  <li>• SQLite database</li>
                  <li>• Standard logging</li>
                </ul>
              </div>
              
              <div 
                className={`p-4 rounded-lg border cursor-pointer transition-all ${
                  selectedPreset === 'backtesting' 
                    ? 'border-blue-500 bg-blue-50 shadow-md' 
                    : 'border-gray-200 hover:border-blue-300 hover:bg-blue-50'
                }`}
                onClick={() => handlePresetChange('backtesting')}
              >
                <h3 className="text-lg font-medium mb-2">Backtesting</h3>
                <p className="text-sm text-gray-600 mb-4">
                  Optimized for strategy development and historical testing.
                </p>
                <ul className="text-xs text-gray-500 space-y-1">
                  <li>• Trade execution disabled</li>
                  <li>• Market data service enabled</li>
                  <li>• Strategy service enabled</li>
                  <li>• Backtesting service enabled</li>
                  <li>• Debug logging</li>
                </ul>
              </div>
              
              <div 
                className={`p-4 rounded-lg border cursor-pointer transition-all ${
                  selectedPreset === 'advanced' 
                    ? 'border-blue-500 bg-blue-50 shadow-md' 
                    : 'border-gray-200 hover:border-blue-300 hover:bg-blue-50'
                }`}
                onClick={() => handlePresetChange('advanced')}
              >
                <h3 className="text-lg font-medium mb-2">Advanced</h3>
                <p className="text-sm text-gray-600 mb-4">
                  Full-featured configuration for experienced users.
                </p>
                <ul className="text-xs text-gray-500 space-y-1">
                  <li>• All services enabled</li>
                  <li>• PostgreSQL database</li>
                  <li>• Higher worker counts</li>
                  <li>• Enhanced security</li>
                  <li>• Comprehensive logging</li>
                </ul>
              </div>
            </div>
            
            <div className="mt-6 p-4 bg-gray-50 rounded-lg">
              <h3 className="text-lg font-medium mb-2">Selected Configuration</h3>
              <p className="text-sm text-gray-600 mb-2">
                You can customize this configuration later in the Configuration Wizard.
              </p>
              <div className="bg-white p-2 rounded border">
                <pre className="text-xs overflow-auto max-h-40">{JSON.stringify(config, null, 2)}</pre>
              </div>
            </div>
          </div>
        </ConfigWizardStep>
        
        <ConfigWizardStep
          title="API Keys"
          description="Set up your exchange API keys"
          isActive={currentStep === 3}
        >
          <div className="space-y-6">
            <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-100 mb-4">
              <h3 className="text-lg font-medium text-yellow-800 mb-2">Important Security Notice</h3>
              <p className="text-yellow-700">
                API keys provide access to your exchange accounts. Always:
              </p>
              <ul className="list-disc pl-5 text-yellow-700 mt-2 space-y-1">
                <li>Use read-only API keys when possible</li>
                <li>Enable IP restrictions on your API keys</li>
                <li>Never share your API keys with anyone</li>
                <li>Regularly rotate your API keys</li>
              </ul>
            </div>
            
            <div className="space-y-4">
              <FormField
                label="Binance API Key"
                tooltip="Your Binance API key for trading and data access"
                helpText="Create API keys in your Binance account settings"
              >
                <input
                  type="password"
                  value={apiKeys.binance}
                  onChange={(e) => handleApiKeyChange('binance', e.target.value)}
                  className="focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md"
                  placeholder="Enter your Binance API key"
                />
              </FormField>
              
              <FormField
                label="Coinbase API Key"
                tooltip="Your Coinbase API key for trading and data access"
                helpText="Create API keys in your Coinbase account settings"
              >
                <input
                  type="password"
                  value={apiKeys.coinbase}
                  onChange={(e) => handleApiKeyChange('coinbase', e.target.value)}
                  className="focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md"
                  placeholder="Enter your Coinbase API key"
                />
              </FormField>
              
              <FormField
                label="Kraken API Key"
                tooltip="Your Kraken API key for trading and data access"
                helpText="Create API keys in your Kraken account settings"
              >
                <input
                  type="password"
                  value={apiKeys.kraken}
                  onChange={(e) => handleApiKeyChange('kraken', e.target.value)}
                  className="focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md"
                  placeholder="Enter your Kraken API key"
                />
              </FormField>
            </div>
            
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-600">
                You can skip this step and add API keys later in the settings.
              </p>
            </div>
          </div>
        </ConfigWizardStep>
        
        <ConfigWizardStep
          title="Preferences"
          description="Set your user preferences"
          isActive={currentStep === 4}
        >
          <div className="space-y-6">
            <div className="p-4 border rounded-lg">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-medium">Show Help Tooltips</h3>
                  <p className="text-sm text-gray-600">
                    Display helpful tooltips throughout the application
                  </p>
                </div>
                <ToggleSwitch
                  id="toggle-tooltips"
                  checked={showTooltips}
                  onChange={(e) => setShowTooltips(e.target.checked)}
                />
              </div>
            </div>
            
            <div className="p-4 bg-gray-50 rounded-lg">
              <h3 className="text-lg font-medium mb-2">Quick Start Guide</h3>
              <p className="text-sm text-gray-600 mb-4">
                After setup, you'll see a quick start guide that will help you:
              </p>
              <ul className="list-disc pl-5 text-gray-600 space-y-2">
                <li>Navigate the dashboard</li>
                <li>Create your first strategy</li>
                <li>Run a backtest</li>
                <li>Deploy a trading strategy</li>
                <li>Monitor performance</li>
              </ul>
            </div>
          </div>
        </ConfigWizardStep>
        
        <ConfigWizardStep
          title="Setup Complete"
          description="You're ready to start using CryptoBot"
          isActive={currentStep === 5}
        >
          <div className="space-y-6 text-center">
            <div className="p-8 bg-green-50 rounded-lg border border-green-100">
              <svg className="w-16 h-16 mx-auto text-green-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <h3 className="text-xl font-medium text-green-800 mb-2">Setup Complete!</h3>
              <p className="text-green-700">
                Your CryptoBot is now configured and ready to use.
              </p>
            </div>
            
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-100">
              <h3 className="text-lg font-medium text-blue-800 mb-2">What's Next?</h3>
              <p className="text-blue-700 mb-4">
                Here are some things you can do next:
              </p>
              <ul className="list-disc pl-5 text-blue-700 space-y-2 text-left">
                <li>Explore the dashboard to get familiar with the interface</li>
                <li>Create your first trading strategy</li>
                <li>Run a backtest to evaluate your strategy</li>
                <li>Configure additional settings in the Configuration Wizard</li>
                <li>Check out the documentation for more advanced features</li>
              </ul>
            </div>
          </div>
        </ConfigWizardStep>
        
        <div className="flex justify-between mt-8">
          {currentStep === 1 ? (
            <button
              onClick={skipSetup}
              className="px-4 py-2 text-gray-600 hover:text-gray-800"
            >
              Skip Setup
            </button>
          ) : (
            <button
              onClick={prevStep}
              disabled={currentStep === 1}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
            >
              Previous
            </button>
          )}
          
          {currentStep < totalSteps ? (
            <button
              onClick={nextStep}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Next
            </button>
          ) : (
            <button
              onClick={handleComplete}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
            >
              Get Started
            </button>
          )}
        </div>
      </div>
    </div>
  );
}