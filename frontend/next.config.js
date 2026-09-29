/** @type {import('next').NextConfig} */
const nextConfig = {
  // Prevent Vercel stripping trailing slashes (causes redirect loop with FastAPI)
  skipTrailingSlashRedirect: true,
  // The public combine board is reachable on a share token alone, and its rows name
  // minors. Keep crawlers off it, and keep the token out of the Referer header of
  // anything the page loads.
  async headers() {
    return [
      {
        source: '/combine/live/:path*',
        headers: [
          { key: 'X-Robots-Tag', value: 'noindex, nofollow, noarchive' },
          { key: 'Referrer-Policy', value: 'no-referrer' },
        ],
      },
    ];
  },
  // Proxy API requests to backend
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    return [
      {
        // Use regex to preserve trailing slashes in proxied path
        source: '/api/:path(.*)',
        destination: `${apiUrl}/api/:path`,
      },
    ];
  },
};

module.exports = nextConfig;
