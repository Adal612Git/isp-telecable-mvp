/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: "#3fa9f5",
        surface: "#0b1220"
      }
    }
  },
  plugins: []
};
