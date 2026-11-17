/** @type {import('next').NextConfig} */
const ADMIN_SEGMENTS = [
  "dashboard",
  "companies",
  "reports",
  "accounting",
  "service-requests",
  "leads",
  "opportunities",
  "directives",
  "hr",
  "website",
  "advisor",
  "assistant",
  "form-builder",
  "users",
  "audit",
  "login",
  "forgot-password",
  "reset-password",
];

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: `${process.env.BACKEND_URL || "http://localhost:8000"}/:path*`,
      },
    ];
  },
  // The admin console moved from the site root to `/platform/*` so the public
  // corporate website can own `/`. These keep old bookmarks working.
  async redirects() {
    return ADMIN_SEGMENTS.map((segment) => ({
      source: `/${segment}`,
      destination: `/platform/${segment}`,
      permanent: false,
    })).concat(
      ADMIN_SEGMENTS.map((segment) => ({
        source: `/${segment}/:path*`,
        destination: `/platform/${segment}/:path*`,
        permanent: false,
      })),
    );
  },
};

export default nextConfig;
