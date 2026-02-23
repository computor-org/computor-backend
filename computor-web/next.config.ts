import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable standalone output for Docker
  // This creates a minimal production build in .next/standalone
  output: 'standalone',

  // Optionally disable source maps in production for smaller bundle
  // productionBrowserSourceMaps: false,
};

export default nextConfig;
