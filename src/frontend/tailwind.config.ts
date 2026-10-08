import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./services/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "#0B0F17", // Deep obsidian slate
        surface: {
          DEFAULT: "#111827",  // Gray-900 (primary card surface)
          secondary: "#1F2937",// Gray-800 (sidebar/header surface)
          tertiary: "#374151", // Gray-700 (input/hover surface)
          subtle: "#1e293b",   // Slate-800
          border: "rgba(255, 255, 255, 0.08)",
          hover: "rgba(255, 255, 255, 0.04)",
        },
        brand: {
          50: "#eef2ff",
          100: "#e0e7ff",
          200: "#c7d2fe",
          300: "#a5b4fc",
          400: "#818cf8",
          500: "#3B82F6", // Professional Electric Blue
          600: "#2563EB",
          700: "#1D4ED8",
          800: "#1E40AF",
          900: "#1E3A8A",
        },
        // Accessible 6-series Data Viz Palette
        viz: {
          1: "#3B82F6", // Electric Blue (Primary Metrics)
          2: "#10B981", // Emerald Teal (Growth / Margin)
          3: "#F59E0B", // Warm Amber (Returns / Cost)
          4: "#8B5CF6", // Royal Violet (Secondary Channel)
          5: "#06B6D4", // Bright Cyan (Volume / Orders)
          6: "#EC4899", // Vibrant Coral (Benchmark / Target)
        },
        success: {
          DEFAULT: "#10b981", // Emerald
          subtle: "rgba(16, 185, 129, 0.15)",
        },
        warning: {
          DEFAULT: "#f59e0b", // Amber
          subtle: "rgba(245, 158, 11, 0.15)",
        },
        danger: {
          DEFAULT: "#ef4444", // Rose/Red
          subtle: "rgba(239, 68, 68, 0.15)",
        },
      },
      fontFamily: {
        sans: [
          "var(--font-jakarta)",
          "Plus Jakarta Sans",
          "var(--font-inter)",
          "Inter",
          "system-ui",
          "sans-serif",
        ],
        mono: [
          "var(--font-jetbrains-mono)",
          "JetBrains Mono",
          "var(--font-mono)",
          "Fira Code",
          "monospace",
        ],
      },
      boxShadow: {
        card: "0 1px 3px 0 rgba(0, 0, 0, 0.3), 0 1px 2px -1px rgba(0, 0, 0, 0.3)",
        elevated: "0 4px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px -2px rgba(0, 0, 0, 0.4)",
        modal: "0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5)",
      },
    },
  },
  plugins: [],
};

export default config;
