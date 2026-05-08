import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  images: {
    unoptimized: true,
  },
  poweredByHeader: false,
  compress: true,
  experimental: {
    viewTransition: true,
  },
};

export default nextConfig;
