/** @type {import('next').NextConfig} */
const nextConfig = {
  // Keeps styles intact inside deep monorepo dependency chains
  productionBrowserSourceMaps: false,
  // Tells Next.js to scan and bundle shared monorepo components
  transpilePackages: ["@digitalq/shared"],
};

module.exports = nextConfig;
