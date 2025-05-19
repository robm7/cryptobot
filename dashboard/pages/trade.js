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
  const dataCache = useRef({
    position: null,
    balance: null,
    lastFetchTime: 0,
  });
  const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes in milliseconds

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      return;
    }

    // Fetch initial position and balance
    const fetchInitialData = async () => {
      const now = Date.now();
      if (dataCache.current.lastFetchTime && (now - dataCache.current.lastFetchTime < CACHE_DURATION) && dataCache.current.position && dataCache.current.balance) {
        console.log("Using cached initial data for trade page.");
        setPosition(dataCache.current.position);
        setBalance(dataCache.current.balance);
        return;
      }
      console.log("Fetching fresh initial data for trade page.");

      try {
        const [positionRes, balanceRes] = await Promise.all([
          axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/v1/trades/position`, { // Corrected API URL
            headers: { Authorization: `Bearer ${token}` }
          }),
          axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/v1/account/balance`, { // Corrected API URL
            headers: { Authorization: `Bearer ${token}` }
          })
        ]);
        
        const newPosition = positionRes.data;
        const newBalance = balanceRes.data.balance;

        setPosition(newPosition);
        setBalance(newBalance);

        // Update cache
        dataCache.current.position = newPosition;
        dataCache.current.balance = newBalance;
        dataCache.current.lastFetchTime = now;

      } catch (err) {
        setError(err.response?.data?.message || 'Failed to fetch initial data');
        // Potentially clear cache on error or handle specific errors differently
        if (err.response?.status === 401) {
            router.push('/login');
        }
      }
    };

    fetchInitialData();

    // Setup WebSocket connection
    // Ensure WS_URL is defined in your environment, e.g., process.env.NEXT_PUBLIC_WS_URL
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/api/v1/data/ws/ohlcv'; // Example default
    
    // Prevent multiple WebSocket connections if symbol changes rapidly or on re-renders
    if (socketRef.current && socketRef.current.readyState !== WebSocket.CLOSED) {
        socketRef.current.close();
    }

    socketRef.current = new WebSocket(`${wsUrl}/${symbol.replace('/',':')}/1m`); // Example: BTC:USDT/1m

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
      if (!token) {
        router.push('/login');
        setError("Authentication token not found. Please log in.");
        return;
      }
      const res = await axios.post(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/v1/trades/execute`, { // Corrected API URL
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
    <div className="container mx-auto px-2 sm:px-4 py-4 sm:py-8"> {/* Adjusted padding */}
      <h1 className="text-xl sm:text-2xl font-bold mb-4 sm:mb-6">Trading Panel</h1> {/* Adjusted font size and margin */}
      
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 sm:gap-6 mb-6 sm:mb-8"> {/* Adjusted gap and margin */}
        <div className="lg:col-span-3 bg-white p-3 sm:p-4 rounded-lg shadow"> {/* Adjusted padding */}
          <div className="h-64 sm:h-80 lg:h-96"> {/* Responsive chart height */}
            <Chart data={priceData} />
          </div>
        </div>

        <div className="bg-white p-3 sm:p-4 rounded-lg shadow"> {/* Adjusted padding */}
          <h2 className="text-lg sm:text-xl font-semibold mb-3 sm:mb-4">Account Summary</h2> {/* Adjusted font size and margin */}
          <div className="space-y-3 sm:space-y-4"> {/* Adjusted spacing */}
            <div>
              <p className="text-sm sm:text-base text-gray-600">Balance</p> {/* Adjusted font size */}
              <p className="text-xl sm:text-2xl font-bold">${balance.toFixed(2)}</p> {/* Adjusted font size */}
            </div>
            {position && (
              <div>
                <p className="text-sm sm:text-base text-gray-600">Current Position</p> {/* Adjusted font size */}
                <div className="flex items-center space-x-1 sm:space-x-2"> {/* Adjusted spacing */}
                  <span className={`text-md sm:text-lg font-bold ${ /* Adjusted font size */
                    position.side === 'long' ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {position.side} {position.size} {symbol.split('/')[0]}
                  </span>
                  <span className={`text-xs sm:text-sm ${ /* Adjusted font size */
                    position.unrealizedPnl >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    ({position.unrealizedPnl >= 0 ? '+' : ''}{position.unrealizedPnl.toFixed(2)})
                  </span>
                </div>
              </div>
            )}
          </div>

          <div className="mt-4 sm:mt-6"> {/* Adjusted margin */}
            <h2 className="text-lg sm:text-xl font-semibold mb-3 sm:mb-4">New Order</h2> {/* Adjusted font size and margin */}
            <div className="space-y-3 sm:space-y-4"> {/* Adjusted spacing */}
              <div>
                <label htmlFor="symbol-select" className="block text-sm font-medium text-gray-700 mb-1">Symbol</label>
                <select
                  id="symbol-select"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm sm:text-base" /* Adjusted font size */
                >
                  <option value="BTC/USDT">BTC/USDT</option>
                  <option value="ETH/USDT">ETH/USDT</option>
                  <option value="SOL/USDT">SOL/USDT</option>
                </select>
              </div>
              <div>
                <label htmlFor="quantity-input" className="block text-sm font-medium text-gray-700 mb-1">Quantity</label>
                <input
                  id="quantity-input"
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={quantity}
                  onChange={(e) => setQuantity(parseFloat(e.target.value))}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm sm:text-base" /* Adjusted font size */
                />
              </div>
              <div className="grid grid-cols-2 gap-2 sm:gap-3"> {/* Adjusted gap */}
                <button
                  onClick={() => executeTrade('buy')}
                  disabled={loading}
                  className="bg-green-600 hover:bg-green-700 text-white py-2 sm:py-2.5 px-3 sm:px-4 rounded-md disabled:opacity-50 text-sm sm:text-base" /* Adjusted padding and font size */
                >
                  Buy
                </button>
                <button
                  onClick={() => executeTrade('sell')}
                  disabled={loading}
                  className="bg-red-600 hover:bg-red-700 text-white py-2 sm:py-2.5 px-3 sm:px-4 rounded-md disabled:opacity-50 text-sm sm:text-base" /* Adjusted padding and font size */
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