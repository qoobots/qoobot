import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Brain OS brand colors
        brain: {
          bg:     "#0a0a1a",
          panel:  "#12122a",
          border: "#1e1e3a",
          accent: "#6366f1",
          gold:   "#f59e0b",
          safe:   "#22c55e",
          warning:"#eab308",
          danger: "#ef4444",
          text:   "#e2e8f0",
          muted:  "#64748b",
        },
        // Trajectory strategy colors
        strategy: {
          optimal:      "#f59e0b",  // gold
          conservative: "#22c55e",  // green
          aggressive:   "#ef4444",  // red
          exploratory:  "#3b82f6",  // blue
          reverse:      "#8b5cf6",  // purple
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "ghost-flow": "ghost-flow 2s ease-in-out infinite",
      },
      keyframes: {
        "ghost-flow": {
          "0%, 100%": { opacity: "0.3" },
          "50%":      { opacity: "0.6" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
