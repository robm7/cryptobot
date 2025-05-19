import { useState, useEffect } from 'react';
import { format } from 'date-fns';

export default function ReconciliationAlerts({ reports }) {
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    if (!reports || reports.length === 0) return;

    // Extract alerts from reports
    const extractedAlerts = reports
      .filter(report => report.result.alert_triggered)
      .map(report => {
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
          id: report.timestamp,
          timestamp: new Date(report.timestamp),
          severity,
          title: 'Order Reconciliation Alert',
          message: `${missingOrders} missing orders, ${extraOrders} extra orders (${(mismatchPercentage * 100).toFixed(2)}% mismatch rate out of ${report.result.total_orders} total orders)`,
          details: report.result
        };
      })
      .sort((a, b) => b.timestamp - a.timestamp); // Sort by timestamp descending

    setAlerts(extractedAlerts);
  }, [reports]);

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 border-red-500 text-red-900';
      case 'error':
        return 'bg-orange-100 border-orange-500 text-orange-900';
      case 'warning':
        return 'bg-yellow-100 border-yellow-500 text-yellow-900';
      default:
        return 'bg-blue-100 border-blue-500 text-blue-900';
    }
  };

  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'critical':
        return (
          <svg className="h-5 w-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        );
      case 'error':
        return (
          <svg className="h-5 w-5 text-orange-500" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        );
      case 'warning':
        return (
          <svg className="h-5 w-5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        );
      default:
        return (
          <svg className="h-5 w-5 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zm-1 4a1 1 0 00-1 1v2a1 1 0 102 0v-2a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        );
    }
  };

  const formatDateTime = (date) => {
    return format(date, 'MMM d, yyyy HH:mm:ss');
  };

  if (alerts.length === 0) {
    return (
      <div className="bg-white p-4 rounded-lg shadow">
        <h2 className="text-lg font-semibold mb-4">Recent Alerts</h2>
        <p className="text-gray-500">No alerts in the selected time period.</p>
      </div>
    );
  }

  return (
    <div className="bg-white p-4 rounded-lg shadow">
      <h2 className="text-lg font-semibold mb-4">Recent Alerts</h2>
      <div className="space-y-4">
        {alerts.map((alert) => (
          <div 
            key={alert.id} 
            className={`border-l-4 p-4 rounded-r-md ${getSeverityColor(alert.severity)}`}
          >
            <div className="flex items-start">
              <div className="flex-shrink-0 mt-0.5">
                {getSeverityIcon(alert.severity)}
              </div>
              <div className="ml-3 w-full">
                <div className="flex justify-between">
                  <h3 className="text-sm font-medium">{alert.title}</h3>
                  <span className="text-xs text-gray-500">{formatDateTime(alert.timestamp)}</span>
                </div>
                <div className="mt-2 text-sm">
                  <p>{alert.message}</p>
                </div>
                <div className="mt-2">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                    {alert.severity.toUpperCase()}
                  </span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}