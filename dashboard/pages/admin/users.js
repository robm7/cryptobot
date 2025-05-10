import React from 'react';
import UserManagement from '../../components/UserManagement';
import AdminLayout from '../../layouts/AdminLayout';

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