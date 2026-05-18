import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Paleta REPSE — FR-016 del spec 001: confianza y robustez.
        brand: {
          50: "#F0F4FA",
          100: "#D9E2F0",
          200: "#B3C6E0",
          300: "#7C9AC8",
          400: "#3D67A8",
          500: "#1A4480",
          600: "#0F3266",
          700: "#0B2545",  // azul profundo principal
          800: "#091B33",
          900: "#061122",
        },
        // Estados de cumplimiento (FR-012)
        status: {
          valid: "#15803D",      // green-700
          expiring: "#B45309",   // amber-700
          expired: "#B91C1C",    // red-700
          missing: "#525252",    // neutral-600
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
} satisfies Config;
