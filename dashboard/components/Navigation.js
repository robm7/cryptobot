import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { UserServiceClient } from '../proto/auth_grpc_web_pb';
import { GetUserRequest } from '../proto/auth_pb';

const Navigation = () => {
  const router = useRouter();
  const [user, setUser] = React.useState(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const client = new UserServiceClient('http://localhost:50051');
    const request = new GetUserRequest();
    
    // In a real app, you'd get the user ID from auth context or token
    request.setUserId('current-user-id'); 

    client.getUser(request, {}, (err, response) => {
      setLoading(false);
      if (err) {
        console.error(err);
        return;
      }
      setUser(response.toObject());
    });
  }, []);

  if (loading) return null;

  const isAdmin = user?.role === 'admin';

  return (
    <nav className="dashboard-nav">
      <ul>
        <li className={router.pathname === '/dashboard' ? 'active' : ''}>
          <Link href="/dashboard">Dashboard</Link>
        </li>
        <li className={router.pathname === '/strategies' ? 'active' : ''}>
          <Link href="/strategies">Strategies</Link>
        </li>
        <li className={router.pathname === '/trade' ? 'active' : ''}>
          <Link href="/trade">Trade</Link>
        </li>
        <li className={router.pathname === '/backtest' ? 'active' : ''}>
          <Link href="/backtest">Backtest</Link>
        </li>
        <li className={router.pathname === '/optimize' ? 'active' : ''}>
          <Link href="/optimize">Optimize</Link>
        </li>
        <li className={router.pathname === '/reconciliation' ? 'active' : ''}>
          <Link href="/reconciliation">Reconciliation</Link>
        </li>
        <li className={router.pathname === '/notification-preferences' ? 'active' : ''}>
          <Link href="/notification-preferences">
            <span className="flex items-center">
              <svg className="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
              Notifications
            </span>
          </Link>
        </li>
        <li className={router.pathname === '/config-wizard' ? 'active' : ''}>
          <Link href="/config-wizard">
            <span className="flex items-center">
              <svg className="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              Configuration
            </span>
          </Link>
        </li>
        {isAdmin && (
          <li className={router.pathname === '/admin/users' ? 'active' : ''}>
            <Link href="/admin/users">User Management</Link>
          </li>
        )}
      </ul>
    </nav>
  );
};

export default Navigation;