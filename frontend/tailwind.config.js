/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: '#06b6d4',
          dark: '#0891b2',
          light: '#cffafe',
        },
        navy: {
          DEFAULT: '#0a1628',
          mid: '#0f2040',
          light: '#1e3a5f',
        },
        gold: {
          DEFAULT: '#f59e0b',
          dark: '#d97706',
          light: '#fef3c7',
        },
        violet: {
          DEFAULT: '#7c3aed',
          light: '#ede9fe',
        },
        surface: {
          DEFAULT: '#f8fafc',
          elevated: '#ffffff',
        },
      },
      fontFamily: {
        display: ['"Plus Jakarta Sans"', 'sans-serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        '3xl': '1.5rem',
        '4xl': '2rem',
      },
      boxShadow: {
        card: '0 1px 3px 0 rgb(0 0 0 / 0.04), 0 1px 2px -1px rgb(0 0 0 / 0.04)',
        'card-md': '0 4px 24px -4px rgb(6 182 212 / 0.12), 0 2px 8px -2px rgb(0 0 0 / 0.08)',
        'card-gold': '0 4px 24px -4px rgb(245 158 11 / 0.18), 0 2px 8px -2px rgb(0 0 0 / 0.08)',
        'glow-sm': '0 0 20px 0 rgb(6 182 212 / 0.30)',
      },
      animation: {
        shimmer: 'shimmer 1.8s infinite linear',
        'fade-up': 'fadeUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards',
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        fadeUp: {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      transitionTimingFunction: {
        spring: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
        'out-cubic': 'cubic-bezier(0.33, 1, 0.68, 1)',
      },
    },
  },
  plugins: [],
}

