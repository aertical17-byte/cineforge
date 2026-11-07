/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async redirects() {
    return [{source: "/create", destination: "/create/image", permanent: false}];
  },
};

module.exports = nextConfig;
