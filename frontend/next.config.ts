import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  devIndicators: false,
  async rewrites() {
    return [
      { source: "/scene", destination: "http://localhost:8000/scene" },
      { source: "/scene/:path*", destination: "http://localhost:8000/scene/:path*" },
      { source: "/vps/:path*", destination: "http://localhost:8000/vps/:path*" },
      { source: "/storage/:path*", destination: "http://localhost:8000/storage/:path*" },
    ];
  },
};

export default nextConfig;
