/** @type {import('next').NextConfig} */

// The browser only talks to the web origin:
// - /api/* is proxied to the API container, so the refresh and CSRF cookies stay same-origin.
// - /s3/* is proxied to object storage, so presigned POST uploads need no CORS. A POST policy
//   signs the policy document, not the host, so proxying does not break the signature.
const apiInternalUrl = process.env.API_INTERNAL_URL ?? "http://api:8000";
const s3InternalUrl = process.env.S3_INTERNAL_URL ?? "http://s3:9000";

const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${apiInternalUrl}/api/:path*` },
      { source: "/s3/:path*", destination: `${s3InternalUrl}/:path*` },
    ];
  },
};

export default nextConfig;
