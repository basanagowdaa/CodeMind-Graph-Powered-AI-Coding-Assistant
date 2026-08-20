/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        darkBg: '#0b0f19',
        cardBg: '#131926',
        cardBorder: '#1f293d',
        accentPurple: '#8b5cf6',
        accentBlue: '#3b82f6',
        accentPink: '#ec4899',
        accentGreen: '#10b981',
      },
      fontFamily: {
        mono: ['Fira Code', 'Courier New', 'monospace'],
      }
    },
  },
  plugins: [],
}
