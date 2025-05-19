import React from 'react';
import dynamic from 'next/dynamic';
import AdminLayout from '../../layouts/AdminLayout';

const UserManagement = dynamic(() => import('../../components/UserManagement'), {
  loading: () => <p>Loading user management...</p>,
  ssr: false // Optional: disable SSR for this component if it's client-side only
});

const UsersPage = () => {
  return (
    <AdminLayout>
      <div className="admin-content">
        <h1>User Management</h1>
        <UserManagement />
      </div>
    </AdminLayout>
  );
};

export default UsersPage;