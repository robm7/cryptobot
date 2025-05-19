import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';

export default function QuickStartGuide({ onClose }) {
  const [currentStep, setCurrentStep] = useState(1);
  const [dismissed, setDismissed] = useState(false);
  const router = useRouter();
  
  const totalSteps = 5;
  
  useEffect(() => {
    // Check if the guide has been dismissed before
    const isDismissed = localStorage.getItem('cryptobot_quickstart_dismissed') === 'true';
    setDismissed(isDismissed);
  }, []);
  
  const nextStep = () => {
    if (currentStep < totalSteps) {
      setCurrentStep(currentStep + 1);
    } else {
      handleDismiss();
    }
  };
  
  const prevStep = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };
  
  const handleDismiss = () => {
    // Mark the guide as dismissed
    localStorage.setItem('cryptobot_quickstart_dismissed', 'true');
    setDismissed(true);
    
    // Call the onClose callback
    if (onClose) {
      onClose();
    }
  };
  
  const resetDismissed = () => {
    localStorage.removeItem('cryptobot_quickstart_dismissed');
    setDismissed(false);
  };
  
  if (dismissed) {
    return null;
  }
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold">Quick Start Guide</h2>
            <button 
              onClick={handleDismiss}
              className="text-gray-400 hover:text-gray-600"
              aria-label="Close"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          <div className="mb-4">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${(currentStep / totalSteps) * 100}%` }}
              ></div>
            </div>
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>Step {currentStep} of {totalSteps}</span>
              <button 
                onClick={handleDismiss}
                className="text-blue-600 hover:text-blue-800"
              >
                Skip Guide
              </button>
            </div>
          </div>
          
          {/* Step 1: Dashboard Overview */}
          {currentStep === 1 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Dashboard Overview</h3>
              <div className="p-4 bg-blue-50 rounded-lg">
                <p className="text-blue-800 mb-4">
                  The dashboard provides an overview of your trading activity and system status.
                </p>
                <div className="space-y-2">
                  <div className="flex items-start">
                    <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center mr-3">
                      <span className="text-blue-600 font-semibold">1</span>
                    </div>
                    <div>
                      <h4 className="font-medium">Navigation Menu</h4>
                      <p className="text-sm text-gray-600">Use the navigation menu on the left to access different sections of the application.</p>
                    </div>
                  </div>
                  <div className="flex items-start">
                    <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center mr-3">
                      <span className="text-blue-600 font-semibold">2</span>
                    </div>
                    <div>
                      <h4 className="font-medium">Performance Metrics</h4>
                      <p className="text-sm text-gray-600">View key performance metrics like profit/loss, win rate, and drawdown.</p>
                    </div>
                  </div>
                  <div className="flex items-start">
                    <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center mr-3">
                      <span className="text-blue-600 font-semibold">3</span>
                    </div>
                    <div>
                      <h4 className="font-medium">System Status</h4>
                      <p className="text-sm text-gray-600">Monitor the status of all services and connections.</p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="border rounded-lg overflow-hidden">
                <img 
                  src="/images/dashboard-overview.png" 
                  alt="Dashboard Overview" 
                  className="w-full"
                  onError={(e) => {
                    e.target.onerror = null;
                    e.target.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100%25' height='100%25' viewBox='0 0 800 400' preserveAspectRatio='none'%3E%3Crect fill='%23f3f4f6' width='800' height='400'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-family='system-ui, sans-serif' font-size='24' fill='%236b7280'%3EDashboard Preview%3C/text%3E%3C/svg%3E";
                  }}
                />
              </div>
            </div>
          )}
          
          {/* Step 2: Creating a Strategy */}
          {currentStep === 2 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Creating a Strategy</h3>
              <div className="p-4 bg-green-50 rounded-lg">
                <p className="text-green-800 mb-4">
                  Strategies define the rules for when to enter and exit trades.
                </p>
                <div className="space-y-2">
                  <div className="flex items-start">
                    <div className="flex-shrink-0 w-8 h-8 bg-green-100 rounded-full flex items-center justify-center mr-3">
                      <span className="text-green-600 font-semibold">1</span>
                    </div>
                    <div>
                      <h4 className="font-medium">Navigate to Strategies</h4>
                      <p className="text-sm text-gray-600">Click on "Strategies" in the navigation menu.</p>
                    </div>
                  </div>
                  <div className="flex items-start">
                    <div className="flex-shrink-0 w-8 h-8 bg-green-100 rounded-full flex items-center justify-center mr-3">
                      <span className="text-green-600 font-semibold">2</span>
                    </div>
                    <div>
                      <h4 className="font-medium">Create New Strategy</h4>
                      <p className="text-sm text-gray-600">Click the "New Strategy" button and select a template or start from scratch.</p>
                    </div>
                  </div>
                  <div className="flex items-start">
                    <div className="flex-shrink-0 w-8 h-8 bg-green-100 rounded-full flex items-center justify-center mr-3">
                      <span className="text-green-600 font-semibold">3</span>
                    </div>
                    <div>
                      <h4 className="font-medium">Configure Parameters</h4>
                      <p className="text-sm text-gray-600">Set the parameters for your strategy, such as indicators, timeframes, and risk settings.</p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="border rounded-lg overflow-hidden">
                <img 
                  src="/images/strategy-creation.png" 
                  alt="Strategy Creation" 
                  className="w-full"
                  onError={(e) => {
                    e.target.onerror = null;
                    e.target.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100%25' height='100%25' viewBox='0 0 800 400' preserveAspectRatio='none'%3E%3Crect fill='%23f3f4f6' width='800' height='400'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-family='system-ui, sans-serif' font-size='24' fill='%236b7280'%3EStrategy Creation Preview%3C/text%3E%3C/svg%3E";
                  }}
                />
              </div>
              <div className="bg-yellow-50 p-3 rounded-lg">
                <p className="text-sm text-yellow-800">
                  <strong>Tip:</strong> Start with a simple strategy and gradually add complexity as you gain experience.
                </p>
              </div>
            </div>
          )}
          
          {/* Step 3: Running a Backtest */}
          {currentStep === 3 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Running a Backtest</h3>
              <div className="p-4 bg-purple-50 rounded-lg">
                <p className="text-purple-800 mb-4">
                  Backtesting allows you to test your strategy against historical data.
                </p>
                <div className="space-y-2">
                  <div className="flex items-start">
                    <div className="flex-shrink-0 w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center mr-3">
                      <span className="text-purple-600 font-semibold">1</span>
                    </div>
                    <div>
                      <h4 className="font-medium">Navigate to Backtest</h4>
                      <p className="text-sm text-gray-600">Click on "Backtest" in the navigation menu.</p>
                    </div>
                  </div>
                  <div className="flex items-start">
                    <div className="flex-shrink-0 w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center mr-3">
                      <span className="text-purple-600 font-semibold">2</span>
                    </div>
                    <div>
                      <h4 className="font-medium">Select Strategy</h4>
                      <p className="text-sm text-gray-600">Choose the strategy you want to test from the dropdown menu.</p>
                    </div>
                  </div>
                  <div className="flex items-start">
                    <div className="flex-shrink-0 w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center mr-3">
                      <span className="text-purple-600 font-semibold">3</span>
                    </div>
                    <div>
                      <h4 className="font-medium">Configure Backtest</h4>
                      <p className="text-sm text-gray-600">Set the date range, initial capital, and other parameters for your backtest.</p>
                    </div>
                  </div>
                  <div className="flex items-start">
                    <div className="flex-shrink-0 w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center mr-3">
                      <span className="text-purple-600 font-semibold">4</span>
                    </div>
                    <div>
                      <h4 className="font-medium">Run and Analyze</h4>
                      <p className="text-sm text-gray-600">Click "Run Backtest" and analyze the results to evaluate your strategy's performance.</p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="border rounded-lg overflow-hidden">
                <img 
                  src="/images/backtest-screen.png" 
                  alt="Backtest Screen" 
                  className="w-full"
                  onError={(e) => {
                    e.target.onerror = null;
                    e.target.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100%25' height='100%25' viewBox='0 0 800 400' preserveAspectRatio='none'%3E%3Crect fill='%23f3f4f6' width='800' height='400'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-family='system-ui, sans-serif' font-size='24' fill='%236b7280'%3EBacktest Screen Preview%3C/text%3E%3C/svg%3E";
                  }}
                />
              </div>
            </div>
          )}
          
          {/* Step 4: Deploying a Strategy */}
          {currentStep === 4 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Deploying a Strategy</h3>
              <div className="p-4 bg-red-50 rounded-lg">
                <p className="text-red-800 mb-4">
                  Once you're satisfied with your strategy's backtest performance, you can deploy it for live trading.
                </p>
                <div className="space-y-2">
                  <div className="flex items-start">
                    <div className="flex-shrink-0 w-8 h-8 bg-red-100 rounded-full flex items-center justify-center mr-3">
                      <span className="text-red-600 font-semibold">1</span>
                    </div>
                    <div>
                      <h4 className="font-medium">Navigate to Trade</h4>
                      <p className="text-sm text-gray-600">Click on "Trade" in the navigation menu.</p>
                    </div>
                  </div>
                  <div className="flex items-start">
                    <div className="flex-shrink-0 w-8 h-8 bg-red-100 rounded-full flex items-center justify-center mr-3">
                      <span className="text-red-600 font-semibold">2</span>
                    </div>
                    <div>
                      <h4 className="font-medium">Deploy Strategy</h4>
                      <p className="text-sm text-gray-600">Select the strategy you want to deploy and click "Deploy".</p>
                    </div>
                  </div>
                  <div className="flex items-start">
                    <div className="flex-shrink-0 w-8 h-8 bg-red-100 rounded-full flex items-center justify-center mr-3">
                      <span className="text-red-600 font-semibold">3</span>
                    </div>
                    <div>
                      <h4 className="font-medium">Configure Risk</h4>
                      <p className="text-sm text-gray-600">Set risk parameters such as position size, stop loss, and take profit levels.</p>
                    </div>
                  </div>
                  <div className="flex items-start">
                    <div className="flex-shrink-0 w-8 h-8 bg-red-100 rounded-full flex items-center justify-center mr-3">
                      <span className="text-red-600 font-semibold">4</span>
                    </div>
                    <div>
                      <h4 className="font-medium">Start Trading</h4>
                      <p className="text-sm text-gray-600">Click "Start Trading" to begin executing trades based on your strategy.</p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="border rounded-lg overflow-hidden">
                <img 
                  src="/images/deploy-strategy.png" 
                  alt="Deploy Strategy" 
                  className="w-full"
                  onError={(e) => {
                    e.target.onerror = null;
                    e.target.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100%25' height='100%25' viewBox='0 0 800 400' preserveAspectRatio='none'%3E%3Crect fill='%23f3f4f6' width='800' height='400'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-family='system-ui, sans-serif' font-size='24' fill='%236b7280'%3EDeploy Strategy Preview%3C/text%3E%3C/svg%3E";
                  }}
                />
              </div>
              <div className="bg-yellow-50 p-3 rounded-lg">
                <p className="text-sm text-yellow-800">
                  <strong>Important:</strong> Always start with small position sizes when deploying a new strategy.
                </p>
              </div>
            </div>
          )}
          
          {/* Step 5: Monitoring Performance */}
          {currentStep === 5 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Monitoring Performance</h3>
              <div className="p-4 bg-indigo-50 rounded-lg">
                <p className="text-indigo-800 mb-4">
                  Monitor your strategy's performance and make adjustments as needed.
                </p>
                <div className="space-y-2">
                  <div className="flex items-start">
                    <div className="flex-shrink-0 w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center mr-3">
                      <span className="text-indigo-600 font-semibold">1</span>
                    </div>
                    <div>
                      <h4 className="font-medium">Dashboard</h4>
                      <p className="text-sm text-gray-600">Check the dashboard for an overview of your trading performance.</p>
                    </div>
                  </div>
                  <div className="flex items-start">
                    <div className="flex-shrink-0 w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center mr-3">
                      <span className="text-indigo-600 font-semibold">2</span>
                    </div>
                    <div>
                      <h4 className="font-medium">Trade History</h4>
                      <p className="text-sm text-gray-600">Review your trade history to identify patterns and areas for improvement.</p>
                    </div>
                  </div>
                  <div className="flex items-start">
                    <div className="flex-shrink-0 w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center mr-3">
                      <span className="text-indigo-600 font-semibold">3</span>
                    </div>
                    <div>
                      <h4 className="font-medium">Performance Metrics</h4>
                      <p className="text-sm text-gray-600">Analyze key metrics like profit factor, Sharpe ratio, and maximum drawdown.</p>
                    </div>
                  </div>
                  <div className="flex items-start">
                    <div className="flex-shrink-0 w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center mr-3">
                      <span className="text-indigo-600 font-semibold">4</span>
                    </div>
                    <div>
                      <h4 className="font-medium">Adjust Strategy</h4>
                      <p className="text-sm text-gray-600">Make adjustments to your strategy based on performance data.</p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="border rounded-lg overflow-hidden">
                <img 
                  src="/images/performance-monitoring.png" 
                  alt="Performance Monitoring" 
                  className="w-full"
                  onError={(e) => {
                    e.target.onerror = null;
                    e.target.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100%25' height='100%25' viewBox='0 0 800 400' preserveAspectRatio='none'%3E%3Crect fill='%23f3f4f6' width='800' height='400'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-family='system-ui, sans-serif' font-size='24' fill='%236b7280'%3EPerformance Monitoring Preview%3C/text%3E%3C/svg%3E";
                  }}
                />
              </div>
              <div className="bg-green-50 p-3 rounded-lg">
                <p className="text-sm text-green-800">
                  <strong>Congratulations!</strong> You've completed the quick start guide. You can access this guide again from the help menu if needed.
                </p>
              </div>
            </div>
          )}
          
          <div className="flex justify-between mt-6">
            <button
              onClick={prevStep}
              disabled={currentStep === 1}
              className={`px-4 py-2 rounded-md ${
                currentStep === 1
                  ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              Previous
            </button>
            
            <button
              onClick={nextStep}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              {currentStep < totalSteps ? 'Next' : 'Finish'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}