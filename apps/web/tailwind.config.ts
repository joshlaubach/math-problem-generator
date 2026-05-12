import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg:           "var(--bg)",
        surface:      "var(--surface)",
        surface2:     "var(--surface2)",
        surface3:     "var(--surface3)",
        wborder:      "var(--border)",
        wborder2:     "var(--border2)",
        wtext:        "var(--text)",
        dim:          "var(--text-dim)",
        muted:        "var(--text-muted)",
        caramel:      "var(--caramel)",
        "caramel-dim":"var(--caramel-dim)",
        "caramel-glow":"var(--caramel-glow)",
        forest:       "var(--forest)",
        "forest-dim": "var(--forest-dim)",
        terracotta:   "var(--terracotta)",
        "terra-dim":  "var(--terra-dim)",
      },
      fontFamily: {
        display: ["var(--font-fraunces)", "Georgia", "serif"],
        body:    ["var(--font-instrument)", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
