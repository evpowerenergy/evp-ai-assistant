/** @type {import('next').NextConfig} */
const nextConfig = {
  // Verification builds may use .next-build so they never overwrite the
  // active development server's .next chunks.
  distDir: process.env.NEXT_DIST_DIR || '.next',
  output: 'standalone', // For Cloud Run deployment
  reactStrictMode: true,
  swcMinify: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
}

module.exports = nextConfig
