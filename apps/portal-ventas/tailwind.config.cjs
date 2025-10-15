/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#5ef2c0",
          dark: "#4bd2a7"
        }
      }
    }
  },
  plugins: []
};
