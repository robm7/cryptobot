import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';
import dynamic from 'next/dynamic';
import { getCachedData, setCachedData } from '../utils/cache';

// Dynamically import Chart component to avoid SSR issues
const Chart = dynamic(() => import('../components/Chart'), { ssr: false });

export default function Backtest() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const router = useRouter();
  const { strategy } = router.query;
  const BACKTEST_REPORT_CACHE_KEY = strategy ? `backtest_report_${strategy}` : null;


  useEffect(() => {
    const fetchBacktestReport = async () => {
      if (!strategy) {
        setLoading(false);
        setError("Strategy ID is missing.");
        return;
      }
      setLoading(true);

      const cachedReport = getCachedData(BACKTEST_REPORT_CACHE_KEY);
      if (cachedReport) {
        setReport(cachedReport);
        setLoading(false);
        return;
      }

      try {
        const token = localStorage.getItem('token');
        const res = await axios.get(`${process.env.API_BASE_URL}/backtest/${strategy}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setReport(res.data);
        setCachedData(BACKTEST_REPORT_CACHE_KEY, res.data);
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
  }, [strategy, BACKTEST_REPORT_CACHE_KEY]);

  if (loading) return <div className="p-4">Loading backtest report...</div>;
  if (error) return <div className="p-4 text-red-500">{error}</div>;
  if (!report) return <div className="p-4">No report data available</div>;

  return (
    <div className="container mx-auto px-2 sm:px-4 py-4 sm:py-8"> {/* Adjusted padding */}
      <h1 className="text-xl sm:text-2xl font-bold mb-4 sm:mb-6">Backtest Report: {report.strategy_name}</h1> {/* Adjusted font size & margin */}
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6 mb-6 sm:mb-8"> {/* Adjusted gap & margin */}
        {/* Performance Metrics Card */}
        <div className="bg-white p-3 sm:p-4 rounded-lg shadow"> {/* Adjusted padding */}
          <h3 className="text-md sm:text-lg font-semibold mb-2">Performance Metrics</h3> {/* Adjusted font size */}
          <div className="space-y-1 sm:space-y-2 text-sm sm:text-base"> {/* Adjusted spacing & font size */}
            <p>Total Return: <span className="font-medium">{report.total_return}%</span></p>
            <p>Sharpe Ratio: <span className="font-medium">{report.sharpe_ratio}</span></p>
            <p>Max Drawdown: <span className="font-medium">{report.max_drawdown}%</span></p>
          </div>
        </div>

        {/* Trade Statistics Card */}
        <div className="bg-white p-3 sm:p-4 rounded-lg shadow"> {/* Adjusted padding */}
          <h3 className="text-md sm:text-lg font-semibold mb-2">Trade Statistics</h3> {/* Adjusted font size */}
          <div className="space-y-1 sm:space-y-2 text-sm sm:text-base"> {/* Adjusted spacing & font size */}
            <p>Total Trades: <span className="font-medium">{report.total_trades}</span></p>
            <p>Win Rate: <span className="font-medium">{report.win_rate}%</span></p>
            <p>Avg Win/Loss: <span className="font-medium">{report.avg_win_loss_ratio}</span></p>
          </div>
        </div>

        {/* Time Period Card */}
        <div className="bg-white p-3 sm:p-4 rounded-lg shadow"> {/* Adjusted padding */}
          <h3 className="text-md sm:text-lg font-semibold mb-2">Time Period</h3> {/* Adjusted font size */}
          <div className="space-y-1 sm:space-y-2 text-sm sm:text-base"> {/* Adjusted spacing & font size */}
            <p>Start: <span className="font-medium">{report.start_date}</span></p>
            <p>End: <span className="font-medium">{report.end_date}</span></p>
            <p>Duration: <span className="font-medium">{report.duration_days} days</span></p>
          </div>
        </div>
      </div>

      {/* Equity Curve Card */}
      <div className="bg-white p-3 sm:p-4 rounded-lg shadow mb-6 sm:mb-8"> {/* Adjusted padding & margin */}
        <h2 className="text-lg sm:text-xl font-semibold mb-3 sm:mb-4">Equity Curve</h2> {/* Adjusted font size & margin */}
        <div className="h-64 sm:h-80 lg:h-96"> {/* Responsive chart height */}
          <Chart data={report.equity_curve} />
        </div>
      </div>

      {/* Trade History Card */}
      <div className="bg-white p-3 sm:p-4 rounded-lg shadow"> {/* Adjusted padding */}
        <h2 className="text-lg sm:text-xl font-semibold mb-3 sm:mb-4">Trade History</h2> {/* Adjusted font size & margin */}
        {/* Desktop Table View */}
        <div className="hidden md:block overflow-x-auto">
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

        {/* Mobile Card View */}
        <div className="md:hidden space-y-3 sm:space-y-4"> {/* Adjusted spacing */}
          {report.trades.map((trade, index) => (
            <div key={index} className="bg-gray-50 p-3 sm:p-4 rounded-lg shadow"> {/* Adjusted padding */}
              <div className="flex justify-between items-center mb-1 sm:mb-2"> {/* Adjusted margin */}
                <span className="text-xs sm:text-sm text-gray-600">{trade.date}</span> {/* Adjusted font size */}
                <span className={`px-2 py-1 rounded-full text-xs ${
                  trade.type === 'buy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }`}>
                  {trade.type}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs sm:text-sm"> {/* Adjusted font size */}
                <div>
                  <p className="text-gray-500">Price</p>
                  <p className="font-medium">{trade.price}</p>
                </div>
                <div>
                  <p className="text-gray-500">Size</p>
                  <p className="font-medium">{trade.size}</p>
                </div>
                <div className="col-span-2 mt-1 sm:mt-0"> {/* Adjusted margin for PnL on small screens */}
                  <p className="text-gray-500">PnL</p>
                  <p className={`font-medium ${trade.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {trade.pnl}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}