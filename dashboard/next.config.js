/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    API_BASE_URL: process.env.API_BASE_URL || 'http://localhost:3001',
    WS_URL: process.env.WS_URL || 'ws://localhost:3002',
    JWT_SECRET: process.env.JWT_SECRET || 'your-secret-key'
  },
  images: {
    domains: [],
  },
  webpack: (config) => {
    config.resolve.fallback = { fs: false, net: false, tls: false };
    return config;
  }
}

module.exports = nextConfig