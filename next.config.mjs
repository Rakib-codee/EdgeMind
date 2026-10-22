/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        // Same-origin API: in dev the FastAPI server runs on :8000 (prefix
        // stripped here); on Vercel, /api/* is served by the Python
        // serverless function in api/index.py, which strips the prefix
        // itself (the function receives the original request path).
        source: '/api/:path*',
        destination:
          process.env.NODE_ENV === 'development'
            ? 'http://localhost:8000/:path*'
            : '/api/',
      },
    ]
  },
}

export default nextConfig
