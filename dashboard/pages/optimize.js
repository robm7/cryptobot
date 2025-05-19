import React, { useState, useEffect } from 'react';
import axios from 'axios'; // Import axios
import { useRouter } from 'next/router'; // Import useRouter

const OptimizePage = () => {
  // --- State Variables ---
  const [availableStrategies, setAvailableStrategies] = useState([]); // For strategies fetched from API
  const [selectedStrategy, setSelectedStrategy] = useState('');
  const [strategyParams, setStrategyParams] = useState([]); // Changed to array to match fetched strategy param structure
  const [optimizationParams, setOptimizationParams] = useState({}); // To store start, end, step for each param
  const [backtestSettings, setBacktestSettings] = useState({
    symbol: 'BTC/USDT',
    timeframe: '1h',
    start_date: '2023-01-01',
    end_date: '2023-12-31',
  });
  const [loading, setLoading] = useState(false); // General loading state
  const [loadingStrategies, setLoadingStrategies] = useState(true); // Specific for loading strategies
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const router = useRouter(); // Initialize router

  // Fetch strategies from API on component mount
  useEffect(() => {
    const fetchStrategies = async () => {
      setLoadingStrategies(true);
      try {
        const token = localStorage.getItem('token');
        if (!token) {
          router.push('/login'); // Redirect if no token
          return;
        }
        // Adjust API_BASE_URL to your actual environment variable for the strategy service
        const apiUrl = process.env.NEXT_PUBLIC_STRATEGY_API_URL || 'http://localhost:8004/api';
        const response = await axios.get(`${apiUrl}/strategies`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        // Assuming the API returns an array of strategy objects
        // Each strategy object should have an 'id', 'name', and 'parameters' (which is a dict)
        // We need to transform 'parameters' (dict) into an array of param objects if needed by UI
        const formattedStrategies = response.data.map(strat => ({
            id: strat.id.toString(), // Ensure ID is a string if used as select value directly
            name: strat.name,
            // The 'params' for UI was an array of objects like {id, name, type}
            // The API returns 'parameters' as a dictionary e.g., {"sma_window": "20", "threshold": "1.5"}
            // We need to decide how to represent this. For now, let's assume the API provides enough detail
            // or we adapt the UI to handle the dictionary format.
            // For this example, let's assume strategy.parameters is a dictionary and we'll iterate over its keys.
            // The original UI expected strategyParams to be an array of {id, name, type}.
            // Let's try to create that structure if possible, or simplify.
            // For now, let's assume the API response for strategy details will give parameter definitions.
            // The list endpoint might only give names. We might need another fetch or richer list response.
            // For simplicity now, we'll use the keys of the parameters dict as param.id and param.name.
            params: strat.parameters ? Object.keys(strat.parameters).map(key => ({
                id: key, // e.g., "sma_window"
                name: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()), // "Sma Window"
                type: 'number' // Assuming all are numbers for now, this needs to be richer from API
            })) : []
        }));
        setAvailableStrategies(formattedStrategies);
      } catch (err) {
        console.error("Failed to fetch strategies:", err);
        setError("Failed to load strategies. " + (err.response?.data?.detail || err.message));
        if (err.response?.status === 401) {
          router.push('/login');
        }
      } finally {
        setLoadingStrategies(false);
      }
    };
    fetchStrategies();
  }, [router]);


  // --- Event Handlers ---
  const handleStrategyChange = (e) => {
    const strategyId = e.target.value;
    setSelectedStrategy(strategyId);
    const selected = availableStrategies.find(s => s.id === strategyId); // Use availableStrategies
    if (selected) {
      const initialOptParams = {};
      (selected.params || []).forEach(param => { // Ensure selected.params exists
        initialOptParams[param.id] = { start: '', end: '', step: '' };
      });
      setOptimizationParams(initialOptParams);
      setStrategyParams(selected.params || []); // Ensure selected.params exists
    } else {
      setOptimizationParams({});
      setStrategyParams([]);
    }
    setResults(null);
    setError(null);
  };

  const handleBacktestSettingChange = (e) => {
    const { name, value } = e.target;
    setBacktestSettings(prev => ({ ...prev, [name]: value }));
  };

  const handleOptimizationParamChange = (paramId, field, value) => {
    setOptimizationParams(prev => ({
      ...prev,
      [paramId]: {
        ...prev[paramId],
        [field]: value,
      },
    }));
  };

  const handleRunOptimization = async () => {
    if (!selectedStrategy) {
      setError('Please select a strategy.');
      return;
    }
    setLoading(true);
    setError(null);
    setResults(null);

    const payload = {
      strategy_id: selectedStrategy,
      symbol: backtestSettings.symbol,
      timeframe: backtestSettings.timeframe,
      start_date: backtestSettings.start_date,
      end_date: backtestSettings.end_date,
      parameters_to_optimize: {},
    };

    for (const paramId in optimizationParams) {
      const { start, end, step } = optimizationParams[paramId];
      if (start && end && step) { // Only include if all fields are filled
        payload.parameters_to_optimize[paramId] = {
          start: parseFloat(start),
          end: parseFloat(end),
          step: parseFloat(step),
        };
      }
    }

    if (Object.keys(payload.parameters_to_optimize).length === 0) {
        setError('Please define at least one parameter range to optimize.');
        setLoading(false);
        return;
    }

    try {
      const response = await fetch('/api/backtest/optimize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: 'Optimization failed with status: ' + response.status }));
        throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setResults(data);
    } catch (err) {
      console.error('Optimization error:', err);
      setError(err.message || 'Failed to run optimization.');
    } finally {
      setLoading(false);
    }
  };

  // --- Render ---
  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">Strategy Parameter Optimization</h1>

      {/* Strategy Selection */}
      <div className="mb-6 p-4 border rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-3">1. Select Strategy</h2>
        <label htmlFor="strategy" className="block text-sm font-medium text-gray-700 mb-1">
          Strategy:
        </label>
        <select
          id="strategy"
          name="strategy"
          value={selectedStrategy}
          onChange={handleStrategyChange}
          className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
          disabled={loadingStrategies}
        >
          <option value="">{loadingStrategies ? "Loading strategies..." : "-- Select a Strategy --"}</option>
          {availableStrategies.map(strategy => ( // Use availableStrategies
            <option key={strategy.id} value={strategy.id}>
              {strategy.name}
            </option>
          ))}
        </select>
      </div>

      {/* Parameter Ranges */}
      {selectedStrategy && strategyParams.length > 0 && (
        <div className="mb-6 p-4 border rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-3">2. Define Parameter Ranges</h2>
          {strategyParams.map(param => (
            <div key={param.id} className="mb-4 p-3 border rounded">
              <h3 className="text-md font-medium text-gray-800 mb-2">{param.name}</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label htmlFor={`${param.id}-start`} className="block text-sm font-medium text-gray-700">Start:</label>
                  <input
                    type="number"
                    id={`${param.id}-start`}
                    value={optimizationParams[param.id]?.start || ''}
                    onChange={(e) => handleOptimizationParamChange(param.id, 'start', e.target.value)}
                    className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label htmlFor={`${param.id}-end`} className="block text-sm font-medium text-gray-700">End:</label>
                  <input
                    type="number"
                    id={`${param.id}-end`}
                    value={optimizationParams[param.id]?.end || ''}
                    onChange={(e) => handleOptimizationParamChange(param.id, 'end', e.target.value)}
                    className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label htmlFor={`${param.id}-step`} className="block text-sm font-medium text-gray-700">Step:</label>
                  <input
                    type="number"
                    id={`${param.id}-step`}
                    value={optimizationParams[param.id]?.step || ''}
                    onChange={(e) => handleOptimizationParamChange(param.id, 'step', e.target.value)}
                    className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Backtest Settings */}
      {selectedStrategy && (
        <div className="mb-6 p-4 border rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-3">3. Backtest Settings</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="symbol" className="block text-sm font-medium text-gray-700">Symbol:</label>
              <input
                type="text"
                id="symbol"
                name="symbol"
                value={backtestSettings.symbol}
                onChange={handleBacktestSettingChange}
                className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>
            <div>
              <label htmlFor="timeframe" className="block text-sm font-medium text-gray-700">Timeframe:</label>
              <input
                type="text"
                id="timeframe"
                name="timeframe"
                value={backtestSettings.timeframe}
                onChange={handleBacktestSettingChange}
                className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>
            <div>
              <label htmlFor="start_date" className="block text-sm font-medium text-gray-700">Start Date:</label>
              <input
                type="date"
                id="start_date"
                name="start_date"
                value={backtestSettings.start_date}
                onChange={handleBacktestSettingChange}
                className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>
            <div>
              <label htmlFor="end_date" className="block text-sm font-medium text-gray-700">End Date:</label>
              <input
                type="date"
                id="end_date"
                name="end_date"
                value={backtestSettings.end_date}
                onChange={handleBacktestSettingChange}
                className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>
          </div>
        </div>
      )}

      {/* Run Optimization Button */}
      {selectedStrategy && (
        <div className="mt-8 mb-6">
          <button
            onClick={handleRunOptimization}
            disabled={loading}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 px-4 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
          >
            {loading ? 'Optimizing...' : 'Run Optimization'}
          </button>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="my-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-md">
          <p><strong>Error:</strong> {error}</p>
        </div>
      )}

      {/* Results Display */}
      {results && !error && (
        <div className="mt-8 p-4 border rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Optimization Results</h2>
          {results.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Parameters</th>
                    {/* Dynamically generate metric headers if possible, or list common ones */}
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Total P&L</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sharpe Ratio</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Max Drawdown</th>
                    {/* Add other relevant metric headers */}
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {results.map((result, index) => (
                    <tr key={index}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {result.parameters && typeof result.parameters === 'object' ?
                          Object.entries(result.parameters)
                            .map(([key, value]) => {
                                const paramDef = Array.isArray(strategyParams) ? strategyParams.find(p => p.id === key) : null;
                                return `${paramDef?.name || key}: ${value}`;
                            })
                            .join(', ')
                          : 'N/A'
                        }
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{result.metrics?.total_pnl?.toFixed(2) || 'N/A'}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{result.metrics?.sharpe_ratio?.toFixed(3) || 'N/A'}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{result.metrics?.max_drawdown?.toFixed(2) || 'N/A'}%</td>
                      {/* Render other metrics */}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p>No optimization results found, or the optimization did not yield any valid combinations.</p>
          )}
        </div>
      )}
    </div>
  );
};

export default OptimizePage;