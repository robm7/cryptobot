import React from 'react';
import Navigation from '../components/Navigation';
import Head from 'next/head';

const AdminLayout = ({ children }) => {
  return (
    <div className="admin-layout">
      <Head>
        <title>CryptoBot Admin</title>
      </Head>
      <Navigation />
      <main className="admin-main">
        {children}
      </main>
    </div>
  );
};

export default AdminLayout;