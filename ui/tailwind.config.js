/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["Space Grotesk", "Avenir Next", "sans-serif"],
        body: ["Work Sans", "Helvetica", "sans-serif"],
      },
      colors: {
        ink: "#0f172a",
        mist: "#e2e8f0",
        glow: "#f59e0b",
        surge: "#14b8a6",
        blaze: "#ef4444",
      },
      boxShadow: {
        glow: "0 10px 30px rgba(245, 158, 11, 0.2)",
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
