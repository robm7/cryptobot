import { useState, useEffect } from 'react';
import axios from 'axios';
import { useRouter } from 'next/router';
import { getCachedData, setCachedData } from '../utils/cache';

const STRATEGIES_CACHE_KEY = 'strategies_data';

export default function Strategies() {
  const [strategies, setStrategies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const router = useRouter();

  useEffect(() => {
    const fetchStrategies = async () => {
      setLoading(true);
      const cachedStrategies = getCachedData(STRATEGIES_CACHE_KEY);

      if (cachedStrategies) {
        setStrategies(cachedStrategies);
        setLoading(false);
        return;
      }

      try {
        const token = localStorage.getItem('token');
        const res = await axios.get(`${process.env.API_BASE_URL}/strategies`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setStrategies(res.data);
        setCachedData(STRATEGIES_CACHE_KEY, res.data);
      } catch (err) {
        setError(err.response?.data?.message || 'Failed to fetch strategies');
        if (err.response?.status === 401) {
          router.push('/login');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchStrategies();
  }, []);

  if (loading) return <div className="p-4">Loading strategies...</div>;
  if (error) return <div className="p-4 text-red-500">{error}</div>;

  return (
    <div className="container mx-auto px-2 sm:px-4 py-4 sm:py-8"> {/* Adjusted padding */}
      <h1 className="text-xl sm:text-2xl font-bold mb-4 sm:mb-6">Strategy Management</h1> {/* Adjusted font size & margin */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6"> {/* Adjusted gap */}
        {strategies.map((strategy) => (
          <div key={strategy.id} className="border rounded-lg p-3 sm:p-4 shadow-sm hover:shadow-md transition-shadow"> {/* Adjusted padding, added hover effect */}
            <h2 className="text-lg sm:text-xl font-semibold mb-1 sm:mb-2">{strategy.name}</h2> {/* Adjusted font size & margin */}
            <p className="text-sm text-gray-600 mb-2 sm:mb-3 h-10 overflow-hidden text-ellipsis"> {/* Adjusted font size, margin, added height limit and ellipsis for description */}
              {strategy.description || "No description available."}
            </p>
            <div className="flex justify-between items-center mt-3 sm:mt-4"> {/* Adjusted margin */}
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${ /* Added font-medium and rounded-full */
                strategy.active ? 'bg-green-100 text-green-700' : 'bg-gray-200 text-gray-700' /* Adjusted colors */
              }`}>
                {strategy.active ? 'Active' : 'Inactive'}
              </span>
              <button
                onClick={() => router.push(`/backtest?strategy=${strategy.id}`)}
                className="text-sm font-medium text-indigo-600 hover:text-indigo-800 transition-colors" /* Adjusted colors */
              >
                Backtest
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}