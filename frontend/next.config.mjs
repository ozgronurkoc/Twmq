/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8080/api/:path*",
      },
      {
        // Liveness. Disariya acilan tek port bu surectir; Flask'in /health'i
        // proxy'lenmezse "API sureci ayakta mi" sorusunun disaridan sorulacak
        // bir adresi olmaz. Hicbir degismez kosmaz (~2 ms), bu yuzden bir
        // probe'a baglanmasi guvenlidir — degismez raporu /api/health'tedir.
        source: "/health",
        destination: "http://127.0.0.1:8080/health",
      },
    ];
  },
};
export default nextConfig;
