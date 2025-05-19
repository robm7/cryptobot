import { useState, useEffect } from 'react';
import axios from 'axios';

export default function AlertThresholdConfig({ onUpdate }) {
  const [thresholds, setThresholds] = useState({
    mismatch_percentage: 0.01, // Default to 1%
    missing_orders: 5,
    extra_orders: 5
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    fetchThresholds();
  }, []);

  const fetchThresholds = async () => {
    setLoading(true);
    setError('');
    try {
      const token = localStorage.getItem('token');
      if (!token) return;

      const response = await axios.get(`${process.env.API_BASE_URL}/reconciliation/config/thresholds`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.data && response.data.thresholds) {
        setThresholds(response.data.thresholds);
      }
    } catch (err) {
      console.error('Failed to fetch thresholds:', err);
      setError('Failed to load alert thresholds');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    let parsedValue = parseFloat(value);
    
    // Validate input
    if (isNaN(parsedValue) || parsedValue < 0) {
      parsedValue = 0;
    }
    
    // For percentage, convert from display percentage to decimal
    if (name === 'mismatch_percentage') {
      parsedValue = parsedValue / 100;
    }
    
    setThresholds(prev => ({
      ...prev,
      [name]: parsedValue
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      const token = localStorage.getItem('token');
      if (!token) return;

      await axios.post(`${process.env.API_BASE_URL}/reconciliation/config/thresholds`, {
        thresholds
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      setSuccess('Alert thresholds updated successfully');
      setIsEditing(false);
      
      // Notify parent component if provided
      if (onUpdate) {
        onUpdate(thresholds);
      }
    } catch (err) {
      console.error('Failed to update thresholds:', err);
      setError(err.response?.data?.message || 'Failed to update alert thresholds');
    } finally {
      setLoading(false);
    }
  };

  const formatPercentage = (value) => {
    return (value * 100).toFixed(2);
  };

  if (loading && !isEditing) {
    return (
      <div className="bg-white p-4 rounded-lg shadow">
        <h2 className="text-lg font-semibold mb-4">Alert Thresholds</h2>
        <p className="text-gray-500">Loading thresholds...</p>
      </div>
    );
  }

  return (
    <div className="bg-white p-4 rounded-lg shadow">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">Alert Thresholds</h2>
        {!isEditing && (
          <button
            onClick={() => setIsEditing(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white py-1 px-3 rounded-md text-sm"
          >
            Edit Thresholds
          </button>
        )}
      </div>
      
      {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">{error}</div>}
      {success && <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">{success}</div>}
      
      {isEditing ? (
        <form onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Mismatch Percentage
              </label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <input
                  type="number"
                  name="mismatch_percentage"
                  value={formatPercentage(thresholds.mismatch_percentage)}
                  onChange={handleChange}
                  step="0.01"
                  min="0"
                  className="focus:ring-blue-500 focus:border-blue-500 block w-full pl-3 pr-12 sm:text-sm border-gray-300 rounded-md"
                  placeholder="1.00"
                />
                <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                  <span className="text-gray-500 sm:text-sm">%</span>
                </div>
              </div>
              <p className="mt-1 text-xs text-gray-500">
                Alerts triggered when mismatch rate exceeds this percentage
              </p>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Missing Orders
              </label>
              <input
                type="number"
                name="missing_orders"
                value={thresholds.missing_orders}
                onChange={handleChange}
                min="0"
                step="1"
                className="focus:ring-blue-500 focus:border-blue-500 block w-full pl-3 pr-3 sm:text-sm border-gray-300 rounded-md"
                placeholder="5"
              />
              <p className="mt-1 text-xs text-gray-500">
                Alerts triggered when missing orders exceed this number
              </p>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Extra Orders
              </label>
              <input
                type="number"
                name="extra_orders"
                value={thresholds.extra_orders}
                onChange={handleChange}
                min="0"
                step="1"
                className="focus:ring-blue-500 focus:border-blue-500 block w-full pl-3 pr-3 sm:text-sm border-gray-300 rounded-md"
                placeholder="5"
              />
              <p className="mt-1 text-xs text-gray-500">
                Alerts triggered when extra orders exceed this number
              </p>
            </div>
          </div>
          
          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={() => {
                setIsEditing(false);
                fetchThresholds(); // Reset to original values
                setError('');
                setSuccess('');
              }}
              className="bg-gray-200 hover:bg-gray-300 text-gray-800 py-2 px-4 rounded-md"
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-md disabled:opacity-50"
              disabled={loading}
            >
              {loading ? 'Saving...' : 'Save Thresholds'}
            </button>
          </div>
        </form>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-50 p-3 rounded">
            <h3 className="text-sm font-medium text-gray-700">Mismatch Percentage</h3>
            <p className="text-xl font-semibold mt-1">{formatPercentage(thresholds.mismatch_percentage)}%</p>
          </div>
          
          <div className="bg-gray-50 p-3 rounded">
            <h3 className="text-sm font-medium text-gray-700">Missing Orders</h3>
            <p className="text-xl font-semibold mt-1">{thresholds.missing_orders}</p>
          </div>
          
          <div className="bg-gray-50 p-3 rounded">
            <h3 className="text-sm font-medium text-gray-700">Extra Orders</h3>
            <p className="text-xl font-semibold mt-1">{thresholds.extra_orders}</p>
          </div>
        </div>
      )}
      
      <div className="mt-4 text-xs text-gray-500">
        <p>Severity levels are determined based on these thresholds:</p>
        <ul className="list-disc pl-5 mt-1">
          <li><span className="font-medium text-yellow-600">Warning</span>: Equal to or greater than the threshold</li>
          <li><span className="font-medium text-orange-600">Error</span>: Equal to or greater than 2x the threshold</li>
          <li><span className="font-medium text-red-600">Critical</span>: Equal to or greater than 3x the threshold</li>
        </ul>
      </div>
    </div>
  );
}