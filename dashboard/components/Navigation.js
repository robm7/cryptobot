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