import type { NextConfig } from "next";

/**
 * Next.js configuration for Claude Assistant Platform frontend.
 */
const nextConfig: NextConfig = {
  // Output standalone build for Docker
  output: "standalone",

  // Environment variables exposed to the browser
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  },

  // Disable x-powered-by header for security
  poweredByHeader: false,
};

export default nextConfig;
