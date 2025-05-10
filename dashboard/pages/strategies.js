import { useState, useEffect } from 'react';
import axios from 'axios';
import { useRouter } from 'next/router';

export default function Strategies() {
  const [strategies, setStrategies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const router = useRouter();

  useEffect(() => {
    const fetchStrategies = async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await axios.get(`${process.env.API_BASE_URL}/strategies`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setStrategies(res.data);
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

  if (loading) return <div className="p-4">Loading...</div>;
  if (error) return <div className="p-4 text-red-500">{error}</div>;

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Strategy Management</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {strategies.map((strategy) => (
          <div key={strategy.id} className="border rounded-lg p-4 shadow-sm">
            <h2 className="text-xl font-semibold mb-2">{strategy.name}</h2>
            <p className="text-gray-600 mb-2">{strategy.description}</p>
            <div className="flex justify-between items-center">
              <span className={`px-2 py-1 rounded text-xs ${
                strategy.active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
              }`}>
                {strategy.active ? 'Active' : 'Inactive'}
              </span>
              <button
                onClick={() => router.push(`/backtest?strategy=${strategy.id}`)}
                className="text-sm text-blue-600 hover:text-blue-800"
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