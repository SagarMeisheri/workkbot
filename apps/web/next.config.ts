import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@workkbot/shared-types"],
  serverExternalPackages: ["@google/adk"],
};

export default nextConfig;
