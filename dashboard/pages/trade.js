import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';
import dynamic from 'next/dynamic';

// Dynamically import Chart component to avoid SSR issues
const Chart = dynamic(() => import('../components/Chart'), { ssr: false });

export default function Trade() {
  const [priceData, setPriceData] = useState([]);
  const [position, setPosition] = useState(null);
  const [balance, setBalance] = useState(0);
  const [symbol, setSymbol] = useState('BTC/USDT');
  const [quantity, setQuantity] = useState(0.1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const socketRef = useRef(null);
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      return;
    }

    // Fetch initial position and balance
    const fetchInitialData = async () => {
      try {
        const [positionRes, balanceRes] = await Promise.all([
          axios.get(`${process.env.API_BASE_URL}/trades/position`, {
            headers: { Authorization: `Bearer ${token}` }
          }),
          axios.get(`${process.env.API_BASE_URL}/account/balance`, {
            headers: { Authorization: `Bearer ${token}` }
          })
        ]);
        setPosition(positionRes.data);
        setBalance(balanceRes.data.balance);
      } catch (err) {
        setError(err.response?.data?.message || 'Failed to fetch initial data');
      }
    };

    fetchInitialData();

    // Setup WebSocket connection
    socketRef.current = new WebSocket(process.env.WS_URL);

    socketRef.current.onopen = () => {
      console.log('WebSocket connected');
      socketRef.current.send(JSON.stringify({
        type: 'subscribe',
        symbol: symbol
      }));
    };

    socketRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'price') {
        setPriceData(prev => [...prev.slice(-100), data]);
      }
    };

    socketRef.current.onclose = () => {
      console.log('WebSocket disconnected');
    };

    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [symbol]);

  const executeTrade = async (type) => {
    setLoading(true);
    setError('');
    try {
      const token = localStorage.getItem('token');
      const res = await axios.post(`${process.env.API_BASE_URL}/trades/execute`, {
        symbol,
        quantity,
        type
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setPosition(res.data.position);
      setBalance(res.data.balance);
    } catch (err) {
      setError(err.response?.data?.message || 'Trade execution failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Trading Panel</h1>
      
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-8">
        <div className="lg:col-span-3 bg-white p-4 rounded-lg shadow">
          <div className="h-96">
            <Chart data={priceData} />
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Account Summary</h2>
          <div className="space-y-4">
            <div>
              <p className="text-gray-600">Balance</p>
              <p className="text-2xl font-bold">${balance.toFixed(2)}</p>
            </div>
            {position && (
              <div>
                <p className="text-gray-600">Current Position</p>
                <div className="flex items-center space-x-2">
                  <span className={`text-lg font-bold ${
                    position.side === 'long' ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {position.side} {position.size} {symbol.split('/')[0]}
                  </span>
                  <span className={`text-sm ${
                    position.unrealizedPnl >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    ({position.unrealizedPnl >= 0 ? '+' : ''}{position.unrealizedPnl.toFixed(2)})
                  </span>
                </div>
              </div>
            )}
          </div>

          <div className="mt-6">
            <h2 className="text-xl font-semibold mb-4">New Order</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Symbol</label>
                <select
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                >
                  <option value="BTC/USDT">BTC/USDT</option>
                  <option value="ETH/USDT">ETH/USDT</option>
                  <option value="SOL/USDT">SOL/USDT</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Quantity</label>
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={quantity}
                  onChange={(e) => setQuantity(parseFloat(e.target.value))}
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => executeTrade('buy')}
                  disabled={loading}
                  className="bg-green-600 hover:bg-green-700 text-white py-2 px-4 rounded-md disabled:opacity-50"
                >
                  Buy
                </button>
                <button
                  onClick={() => executeTrade('sell')}
                  disabled={loading}
                  className="bg-red-600 hover:bg-red-700 text-white py-2 px-4 rounded-md disabled:opacity-50"
                >
                  Sell
                </button>
              </div>
              {error && <p className="text-red-500 text-sm">{error}</p>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}