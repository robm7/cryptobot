import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';
import dynamic from 'next/dynamic';

// Dynamically import components to avoid SSR issues
const NotificationPreferences = dynamic(() => import('../components/NotificationPreferences'), { ssr: false });

export default function NotificationPreferencesPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      return;
    }

    // Check if user is authenticated
    const checkAuth = async () => {
      try {
        await axios.get(`${process.env.API_BASE_URL}/auth/me`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setLoading(false);
      } catch (err) {
        console.error('Authentication error:', err);
        setError('Authentication failed. Please log in again.');
        localStorage.removeItem('token');
        router.push('/login');
      }
    };

    checkAuth();
  }, []);

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Notification Preferences</h1>
      
      {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">{error}</div>}
      
      {loading ? (
        <div className="text-center py-8">Loading...</div>
      ) : (
        <div className="grid grid-cols-1 gap-6">
          <div className="bg-white p-4 rounded-lg shadow mb-6">
            <p className="text-gray-700 mb-4">
              Configure your notification preferences to control how and when you receive alerts from the system.
              You can customize notification channels, alert types, and quiet hours to suit your needs.
            </p>
            <div className="flex items-center text-sm text-gray-600">
              <svg className="h-5 w-5 text-yellow-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <span>
                Critical alerts may still be delivered during quiet hours if you enable the override option.
              </span>
            </div>
          </div>
          
          <NotificationPreferences />
          
          <div className="bg-white p-4 rounded-lg shadow">
            <h2 className="text-lg font-semibold mb-4">Notification History</h2>
            <p className="text-gray-500">
              Your notification history will be displayed here in a future update.
              This will allow you to see all notifications that have been sent to you,
              including those you might have missed.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}