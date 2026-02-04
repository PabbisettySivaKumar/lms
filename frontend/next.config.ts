import type { NextConfig } from "next";

// Expose backend_url to the browser as NEXT_PUBLIC_BACKEND_URL (Next.js only injects NEXT_PUBLIC_* client-side)
const backendUrl = process.env.backend_url || process.env.API_BACKEND_URL;

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_BACKEND_URL: process.env.backend_url || process.env.NEXT_PUBLIC_BACKEND_URL || process.env.NEXT_PUBLIC_API_URL,
  },
  /* config options here */
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${String(backendUrl).replace(/\/$/, '')}/:path*`,
      },
    ];
  },
  // Ensure error responses are properly forwarded
  async headers() {
    return [
      {
        source: '/api/:path*',
        headers: [
          { key: 'Access-Control-Allow-Credentials', value: 'true' },
          { key: 'Access-Control-Allow-Origin', value: '*' },
          { key: 'Access-Control-Allow-Methods', value: 'GET,OPTIONS,PATCH,DELETE,POST,PUT' },
          { key: 'Access-Control-Allow-Headers', value: 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version, Authorization' },
        ],
      },
    ]
  },
};

export default nextConfig;
