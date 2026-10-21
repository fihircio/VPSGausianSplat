import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  devIndicators: false,
  // Allow the dev server (HMR / /_next/webpack-hmr) to be reached over Tailscale.
  // Without this, Next.js 16 blocks cross-origin dev resources from non-localhost hosts.
  allowedDevOrigins: [
    "desktop-578pjun.tail9e0bfc.ts.net", // Tailscale MagicDNS hostname (seen in frontend.err)
    "100.118.54.14", // Tailscale raw IPv4 (used in frontend/.env.local)
  ],
  async rewrites() {
    return [
      { source: "/scene", destination: "http://localhost:8002/scene" },
      { source: "/scene/:path*", destination: "http://localhost:8002/scene/:path*" },
      { source: "/vps/:path*", destination: "http://localhost:8002/vps/:path*" },
      { source: "/storage/:path*", destination: "http://localhost:8002/storage/:path*" },
    ];
  },
};

export default nextConfig;
