import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#f5b921",
          dark: "#c38e0f",
        },
        brandBlue: {
          DEFAULT: "#2a90c9",
          dark: "#1e78b4",
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
