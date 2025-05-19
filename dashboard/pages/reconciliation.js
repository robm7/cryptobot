import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';
import dynamic from 'next/dynamic';
import { downloadCSV, formatDate } from '../utils/exportUtils';

// Dynamically import Chart components to avoid SSR issues
const ReconciliationChart = dynamic(() => import('../components/ReconciliationChart'), { ssr: false });
const MismatchChart = dynamic(() => import('../components/MismatchChart'), { ssr: false });
const ReconciliationAlerts = dynamic(() => import('../components/ReconciliationAlerts'), { ssr: false });
const AlertThresholdConfig = dynamic(() => import('../components/AlertThresholdConfig'), { ssr: false });

export default function ReconciliationDashboard() {
  const [summary, setSummary] = useState(null);
  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [dateRange, setDateRange] = useState('7'); // Default to 7 days
  const [isRunning, setIsRunning] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      return;
    }

    fetchData(token);
  }, [dateRange]);

  const fetchData = async (token) => {
    setLoading(true);
    setError('');
    try {
      // Fetch summary data
      const summaryRes = await axios.get(`${process.env.API_BASE_URL}/reconciliation/summary?days=${dateRange}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSummary(summaryRes.data.summary);

      // Fetch reports
      const reportsRes = await axios.get(`${process.env.API_BASE_URL}/reconciliation/reports`, {
        headers: { Authorization: `Bearer ${token}` },
        params: {
          start_date: new Date(Date.now() - (parseInt(dateRange) * 24 * 60 * 60 * 1000)).toISOString()
        }
      });
      setReports(reportsRes.data.reports || []);
      
      // Set selected report to the most recent one if available
      if (reportsRes.data.reports && reportsRes.data.reports.length > 0) {
        setSelectedReport(reportsRes.data.reports[0]);
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to fetch reconciliation data');
    } finally {
      setLoading(false);
    }
  };

  const runReconciliation = async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      return;
    }

    setIsRunning(true);
    setError('');
    try {
      const res = await axios.post(`${process.env.API_BASE_URL}/reconciliation/run`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // Refresh data after successful run
      await fetchData(token);
      
      // Set the new report as selected
      if (res.data.result) {
        setSelectedReport(res.data.result);
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to run reconciliation');
    } finally {
      setIsRunning(false);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const formatPercentage = (value) => {
    return (value * 100).toFixed(2) + '%';
  };
  
  const exportReportsToCSV = () => {
    if (!reports || reports.length === 0) return;
    
    // Define headers for CSV
    const headers = [
      { key: 'timestamp', label: 'Timestamp' },
      { key: 'totalOrders', label: 'Total Orders' },
      { key: 'matchedOrders', label: 'Matched Orders' },
      { key: 'mismatchedOrders', label: 'Mismatched Orders' },
      { key: 'missingOrders', label: 'Missing Orders' },
      { key: 'extraOrders', label: 'Extra Orders' },
      { key: 'mismatchRate', label: 'Mismatch Rate' },
      { key: 'alertTriggered', label: 'Alert Triggered' },
      { key: 'severity', label: 'Severity' }
    ];
    
    // Transform data for CSV
    const csvData = reports.map(report => {
      // Determine severity based on mismatch percentage
      let severity = 'info';
      const mismatchPercentage = report.result.mismatch_percentage || 0;
      const missingOrders = report.result.missing_orders?.length || 0;
      const extraOrders = report.result.extra_orders?.length || 0;
      
      if (mismatchPercentage >= 0.03 || missingOrders >= 15 || extraOrders >= 15) {
        severity = 'critical';
      } else if (mismatchPercentage >= 0.02 || missingOrders >= 10 || extraOrders >= 10) {
        severity = 'error';
      } else if (mismatchPercentage >= 0.01 || missingOrders >= 5 || extraOrders >= 5) {
        severity = 'warning';
      }
      
      return {
        timestamp: formatDate(new Date(report.timestamp)),
        totalOrders: report.result.total_orders,
        matchedOrders: report.result.matched_orders,
        mismatchedOrders: report.result.mismatched_orders,
        missingOrders: report.result.missing_orders?.length || 0,
        extraOrders: report.result.extra_orders?.length || 0,
        mismatchRate: formatPercentage(report.result.mismatch_percentage),
        alertTriggered: report.result.alert_triggered ? 'Yes' : 'No',
        severity: report.result.alert_triggered ? severity.toUpperCase() : 'N/A'
      };
    });
    
    // Generate filename with current date
    const now = new Date();
    const filename = `reconciliation_reports_${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}.csv`;
    
    // Download CSV
    downloadCSV(csvData, headers, filename);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Reconciliation Dashboard</h1>
      
      <div className="mb-6 flex justify-between items-center">
        <div>
          <label htmlFor="dateRange" className="mr-2 font-medium">Time Period:</label>
          <select
            id="dateRange"
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2"
          >
            <option value="1">Last 24 Hours</option>
            <option value="7">Last 7 Days</option>
            <option value="30">Last 30 Days</option>
            <option value="90">Last 90 Days</option>
          </select>
        </div>
        
        <button
          onClick={runReconciliation}
          disabled={isRunning}
          className="bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-md disabled:opacity-50"
        >
          {isRunning ? 'Running...' : 'Run Reconciliation Now'}
        </button>
      </div>
      
      {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">{error}</div>}
      
      {loading ? (
        <div className="text-center py-8">Loading...</div>
      ) : (
        <>
          {/* Alert Threshold Configuration */}
          <div className="mb-8">
            <AlertThresholdConfig />
          </div>
          
          {/* Summary Cards */}
          {summary && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
              <div className="bg-white p-4 rounded-lg shadow">
                <h3 className="text-gray-500 text-sm font-medium">Total Orders</h3>
                <p className="text-2xl font-bold">{summary.total_orders}</p>
              </div>
              
              <div className="bg-white p-4 rounded-lg shadow">
                <h3 className="text-gray-500 text-sm font-medium">Mismatched Orders</h3>
                <p className="text-2xl font-bold">{summary.total_mismatches}</p>
              </div>
              
              <div className="bg-white p-4 rounded-lg shadow">
                <h3 className="text-gray-500 text-sm font-medium">Average Mismatch Rate</h3>
                <p className={`text-2xl font-bold ${summary.avg_mismatch_percentage > 0.01 ? 'text-red-600' : 'text-green-600'}`}>
                  {formatPercentage(summary.avg_mismatch_percentage)}
                </p>
              </div>
              
              <div className="bg-white p-4 rounded-lg shadow">
                <h3 className="text-gray-500 text-sm font-medium">Alerts Triggered</h3>
                <p className={`text-2xl font-bold ${summary.alerts_triggered > 0 ? 'text-red-600' : 'text-green-600'}`}>
                  {summary.alerts_triggered}
                </p>
              </div>
            </div>
          )}
          
          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <div className="bg-white p-4 rounded-lg shadow">
              <h2 className="text-lg font-semibold mb-4">Reconciliation History</h2>
              <div className="h-80">
                <ReconciliationChart data={reports} />
              </div>
            </div>
            
            <div className="bg-white p-4 rounded-lg shadow">
              <h2 className="text-lg font-semibold mb-4">Mismatch Distribution</h2>
              <div className="h-80">
                <MismatchChart data={reports} />
              </div>
            </div>
          </div>
          
          {/* Alerts Section */}
          <div className="mb-8">
            <ReconciliationAlerts reports={reports} />
          </div>
          
          {/* Reports Table */}
          <div className="bg-white p-4 rounded-lg shadow mb-8">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold">Reconciliation Reports</h2>
              
              <button
                onClick={exportReportsToCSV}
                disabled={reports.length === 0}
                className="bg-green-600 hover:bg-green-700 text-white py-2 px-4 rounded-md disabled:opacity-50 flex items-center"
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Export to CSV
              </button>
            </div>
            
            {reports.length === 0 ? (
              <p className="text-gray-500">No reports available for the selected time period.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Timestamp</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Total Orders</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Matched</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Mismatched</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Mismatch Rate</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Alert</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {reports.map((report, index) => (
                      <tr 
                        key={index} 
                        className={`${selectedReport === report ? 'bg-blue-50' : ''} hover:bg-gray-50 cursor-pointer`}
                        onClick={() => setSelectedReport(report)}
                      >
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{formatDate(report.timestamp)}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{report.result.total_orders}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{report.result.matched_orders}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{report.result.mismatched_orders}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          <span className={report.result.mismatch_percentage > 0.01 ? 'text-red-600' : 'text-green-600'}>
                            {formatPercentage(report.result.mismatch_percentage)}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {report.result.alert_triggered ? (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                              Yes
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                              No
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
          
          {/* Selected Report Details */}
          {selectedReport && (
            <div className="bg-white p-4 rounded-lg shadow">
              <h2 className="text-lg font-semibold mb-4">Report Details</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <h3 className="text-md font-medium mb-2">General Information</h3>
                  <div className="bg-gray-50 p-3 rounded">
                    <p><span className="font-medium">Timestamp:</span> {formatDate(selectedReport.timestamp)}</p>
                    <p><span className="font-medium">Time Period:</span> {selectedReport.result.time_period}</p>
                    <p><span className="font-medium">Total Orders:</span> {selectedReport.result.total_orders}</p>
                    <p><span className="font-medium">Mismatch Rate:</span> {formatPercentage(selectedReport.result.mismatch_percentage)}</p>
                  </div>
                </div>
                
                <div>
                  <h3 className="text-md font-medium mb-2">Mismatch Breakdown</h3>
                  <div className="bg-gray-50 p-3 rounded">
                    <p><span className="font-medium">Matched Orders:</span> {selectedReport.result.matched_orders}</p>
                    <p><span className="font-medium">Mismatched Orders:</span> {selectedReport.result.mismatched_orders}</p>
                    <p><span className="font-medium">Missing Orders:</span> {selectedReport.result.missing_orders}</p>
                    <p><span className="font-medium">Extra Orders:</span> {selectedReport.result.extra_orders}</p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}