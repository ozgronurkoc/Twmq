import type { Config } from "tailwindcss";
const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1d1d1f",
        muted: "#6e6e73",
        line: "#d2d2d7",
        soft: "#f5f5f7",
        brand: "#0071e3",
      },
    },
  },
  plugins: [],
};
export default config;
