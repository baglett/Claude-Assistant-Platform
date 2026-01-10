import type { Config } from "tailwindcss";
import daisyui from "daisyui";

/**
 * Tailwind CSS configuration with DaisyUI plugin.
 */
const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      // Custom theme extensions can be added here
    },
  },
  plugins: [daisyui],
  daisyui: {
    themes: [
      "light",
      "dark",
      "cyberpunk",
      "synthwave",
      {
        // Custom Claude-themed dark mode
        claude: {
          "primary": "#d97706",        // Amber/Orange (Claude brand)
          "primary-content": "#ffffff",
          "secondary": "#6366f1",      // Indigo
          "secondary-content": "#ffffff",
          "accent": "#10b981",         // Emerald
          "accent-content": "#ffffff",
          "neutral": "#1f2937",        // Gray-800
          "neutral-content": "#f3f4f6",
          "base-100": "#111827",       // Gray-900
          "base-200": "#1f2937",       // Gray-800
          "base-300": "#374151",       // Gray-700
          "base-content": "#f9fafb",   // Gray-50
          "info": "#3b82f6",           // Blue
          "success": "#22c55e",        // Green
          "warning": "#f59e0b",        // Amber
          "error": "#ef4444",          // Red
        },
      },
    ],
    darkTheme: "claude",
    base: true,
    styled: true,
    utils: true,
    logs: false,
  },
};

export default config;
