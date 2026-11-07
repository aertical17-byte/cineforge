/** @type {import('tailwindcss').TailwindConfig} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#08080c", 900: "#0d0d13", 850: "#13131b", 800: "#191922",
          700: "#23232f", 600: "#30303e", 500: "#464656", 300: "#7d7d8e", 200: "#a5a5b4", 100: "#d4d4de",
        },
        byz: {
          DEFAULT: "#7c5cff", 600: "#5b3ff0", 500: "#7c5cff", 400: "#967bff", 300: "#b3a2ff",
          200: "#cfc5ff", 100: "#e9e4ff", 50: "#f4f1ff"
        },
        ember: {DEFAULT: "#ff5c7a", 600: "#e5405e"}
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        display: ["Inter", "system-ui", "sans-serif"]
      },
      borderRadius: {xl2: "1.125rem"},
      boxShadow: {
        card: "0 1px 0 0 rgba(255,255,255,0.04) inset, 0 8px 30px rgba(0,0,0,0.35)",
        glow: "0 0 0 1px rgba(124,92,255,0.35), 0 8px 40px rgba(124,92,255,0.25)"
      }
    },
  },
  plugins: [],
};
