/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}", "./public/index.html"],
  theme: {
    extend: {
      colors: {
        clinical: {
          ink: "#102033",
          blue: "#1463ff",
          teal: "#10a6a0",
          mint: "#e8fbf7",
          surface: "#f6f9fc",
          line: "#dbe6ef",
        },
      },
      boxShadow: {
        clinical: "0 18px 50px rgba(16, 32, 51, 0.14)",
      },
      fontFamily: {
        sans: [
          "Aptos",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};
