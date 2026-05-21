import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      boxShadow: {
        soft: "0 10px 40px rgba(0,0,0,0.5)",
        glow: "0 0 24px rgba(139,92,246,0.35)",
        "glow-sm": "0 0 12px rgba(139,92,246,0.25)",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pingOnce: {
          "0%": { transform: "scale(1)", opacity: "0.8" },
          "100%": { transform: "scale(1.8)", opacity: "0" },
        },
      },
      animation: {
        "fade-in": "fadeIn 0.25s ease-out",
        "ping-once": "pingOnce 0.8s ease-out forwards",
      },
    },
  },
  plugins: [],
};

export default config;
