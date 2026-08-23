/**
 * API'nin adresi TEK yerden gelir. Once `127.0.0.1:8080` bu dosyada iki kez
 * sabitti ve backend'in `PORT`u degistiginde proxy onu IZLEYEMIYORDU:
 * `web_app.py` yeni portta acilir, arayuz eskisine konusmaya devam ederdi.
 *
 * `API_PORT` bir derleme-zamani degeridir (rewrite'lar derlemede gomulur),
 * bu yuzden `NEXT_PUBLIC_` onekine gerek yok — tarayiciya cikmaz.
 */
const API_PORT = process.env.API_PORT || "8080";
const API_HEDEF = `http://127.0.0.1:${API_PORT}`;

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_HEDEF}/api/:path*`,
      },
      {
        // Liveness. Disariya acilan tek port bu surectir; Flask'in /health'i
        // proxy'lenmezse "API sureci ayakta mi" sorusunun disaridan sorulacak
        // bir adresi olmaz. Hicbir degismez kosmaz (~2 ms), bu yuzden bir
        // probe'a baglanmasi guvenlidir — degismez raporu /api/health'tedir.
        source: "/health",
        destination: `${API_HEDEF}/health`,
      },
    ];
  },
};
export default nextConfig;
