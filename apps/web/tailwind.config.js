/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
    '../../packages/ui/src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Cascadia Code"', '"Fira Code"', 'monospace'],
      },
      colors: {
        brand: {
          50: 'hsl(263 100% 97%)',
          100: 'hsl(263 100% 94%)',
          200: 'hsl(263 96% 86%)',
          300: 'hsl(263 92% 74%)',
          400: 'hsl(263 85% 62%)',
          500: 'hsl(263 70% 50%)',
          600: 'hsl(263 72% 42%)',
          700: 'hsl(263 74% 34%)',
          800: 'hsl(263 76% 26%)',
          900: 'hsl(263 78% 18%)',
          950: 'hsl(263 80% 10%)',
        },
      },
      animation: {
        'glow-pulse': 'glow-pulse 2.5s ease-in-out infinite',
        'slide-in-right': 'slide-in-right 0.3s ease-out',
        'fade-up': 'fade-up 0.4s ease-out',
      },
      keyframes: {
        'glow-pulse': {
          '0%, 100%': { boxShadow: '0 0 8px rgba(124, 58, 237, 0.3)' },
          '50%': { boxShadow: '0 0 18px rgba(124, 58, 237, 0.6)' },
        },
        'slide-in-right': {
          from: { transform: 'translateX(20px)', opacity: 0 },
          to: { transform: 'translateX(0)', opacity: 1 },
        },
        'fade-up': {
          from: { transform: 'translateY(10px)', opacity: 0 },
          to: { transform: 'translateY(0)', opacity: 1 },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
      boxShadow: {
        glass: '0 8px 32px 0 rgba(0, 0, 0, 0.5)',
        'glow-purple': '0 0 20px rgba(124, 58, 237, 0.4)',
        'glow-indigo': '0 0 20px rgba(79, 70, 229, 0.4)',
      },
    },
  },
  plugins: [],
};
