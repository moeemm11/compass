/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./features/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: { DEFAULT: "#0B1F3A", 800: "#132947", 700: "#1C3D63" },
        ink: "#122033",
        muted: "#5C6B7A",
        line: "#E2E8F0",
        canvas: "#F3F5F8",
        teal: { DEFAULT: "#0F766E", soft: "#E7F5F2" },
        brand: "#1B4F8A",
      },
      fontFamily: { sans: ["IBM Plex Sans", "ui-sans-serif", "system-ui", "sans-serif"] },
      boxShadow: { card: "0 1px 2px rgba(11,31,58,0.05), 0 10px 28px rgba(11,31,58,0.05)" },
    },
  },
  plugins: [],
};
