import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';
import dynamic from 'next/dynamic';

// Dynamically import Chart component to avoid SSR issues
const Chart = dynamic(() => import('../components/Chart'), { ssr: false });

export default function Backtest() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const router = useRouter();
  const { strategy } = router.query;

  useEffect(() => {
    const fetchBacktestReport = async () => {
      if (!strategy) return;

      try {
        const token = localStorage.getItem('token');
        const res = await axios.get(`${process.env.API_BASE_URL}/backtest/${strategy}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setReport(res.data);
      } catch (err) {
        setError(err.response?.data?.message || 'Failed to fetch backtest report');
        if (err.response?.status === 401) {
          router.push('/login');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchBacktestReport();
  }, [strategy]);

  if (loading) return <div className="p-4">Loading backtest report...</div>;
  if (error) return <div className="p-4 text-red-500">{error}</div>;
  if (!report) return <div className="p-4">No report data available</div>;

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Backtest Report: {report.strategy_name}</h1>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="font-semibold mb-2">Performance Metrics</h3>
          <div className="space-y-2">
            <p>Total Return: <span className="font-medium">{report.total_return}%</span></p>
            <p>Sharpe Ratio: <span className="font-medium">{report.sharpe_ratio}</span></p>
            <p>Max Drawdown: <span className="font-medium">{report.max_drawdown}%</span></p>
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="font-semibold mb-2">Trade Statistics</h3>
          <div className="space-y-2">
            <p>Total Trades: <span className="font-medium">{report.total_trades}</span></p>
            <p>Win Rate: <span className="font-medium">{report.win_rate}%</span></p>
            <p>Avg Win/Loss: <span className="font-medium">{report.avg_win_loss_ratio}</span></p>
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="font-semibold mb-2">Time Period</h3>
          <div className="space-y-2">
            <p>Start: <span className="font-medium">{report.start_date}</span></p>
            <p>End: <span className="font-medium">{report.end_date}</span></p>
            <p>Duration: <span className="font-medium">{report.duration_days} days</span></p>
          </div>
        </div>
      </div>

      <div className="bg-white p-4 rounded-lg shadow mb-8">
        <h2 className="text-xl font-semibold mb-4">Equity Curve</h2>
        <div className="h-96">
          <Chart data={report.equity_curve} />
        </div>
      </div>

      <div className="bg-white p-4 rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-4">Trade History</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Price</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Size</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">PnL</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {report.trades.map((trade, index) => (
                <tr key={index}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{trade.date}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span className={`px-2 py-1 rounded-full text-xs ${
                      trade.type === 'buy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {trade.type}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{trade.price}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{trade.size}</td>
                  <td className={`px-6 py-4 whitespace-nowrap text-sm ${
                    trade.pnl >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {trade.pnl}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}