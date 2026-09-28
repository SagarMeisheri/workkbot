import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  transpilePackages: ["@workkbot/shared-types"],
  serverExternalPackages: ["@google/adk"],
  outputFileTracingRoot: path.join(__dirname, "../../"),
};

export default nextConfig;
