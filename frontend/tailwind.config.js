/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        wizz: {
          pink: '#c6007e',
          dark: '#1b0c38',
          light: '#fdf2f8',
        },
        ryanair: {
          blue: '#0d2c6c',
          yellow: '#f1c40f',
          light: '#eff6ff',
        },
        google: {
          blue: '#1a73e8',
          hover: '#1765cc',
          bg: '#f8f9fa',
          surface: '#ffffff',
          border: '#dadce0',
          text: '#202124',
          muted: '#5f6368',
        }
      }
    },
  },
  plugins: [],
}
