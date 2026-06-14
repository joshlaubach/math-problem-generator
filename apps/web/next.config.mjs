/** @type {import('next').NextConfig} */
const securityHeaders = [
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
  { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains; preload' },
  // microphone=(self): voice tutoring needs the mic on our own origin.
  { key: 'Permissions-Policy', value: 'geolocation=(), microphone=(self), camera=()' },
  // CSP intentionally deferred until the CalculatorWidget eval (M2) is removed,
  // so we don't have to allow 'unsafe-eval'. Add Content-Security-Policy here
  // once mathjs replaces new Function().
];

const nextConfig = {
  pageExtensions: ['js', 'jsx', 'md', 'mdx', 'ts', 'tsx'],
  async headers() {
    return [{ source: '/(.*)', headers: securityHeaders }];
  },
};

export default nextConfig;
