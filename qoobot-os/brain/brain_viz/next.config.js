/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['three'],
  webpack: (config) => {
    // Support for GLSL shaders
    config.module.rules.push({
      test: /\.(glsl|vs|fs|vert|frag)$/,
      exclude: /node_modules/,
      use: ['raw-loader'],
    });
    return config;
  },
  // Proxy gRPC-Web / WebSocket to brain_ai backend in dev
  async rewrites() {
    return [
      {
        source: '/api/grpc/:path*',
        destination: 'http://localhost:50052/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
