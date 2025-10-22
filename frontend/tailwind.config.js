/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Official Comviva brand colors
        comviva: {
          primary: '#dc2626',    // Comviva Red
          secondary: '#f97316',  // Comviva Orange
          accent: '#ea580c',     // Darker Orange
          blue: '#2563eb',       // Tech Blue
          dark: '#1F2937',       // Dark gray
          light: '#F8FAFC',      // Very light gray
        },
        // Dark theme colors
        dark: {
          bg: '#0f172a',         // slate-900
          surface: '#1e293b',    // slate-800
          border: '#334155',     // slate-700
          text: '#f1f5f9',       // slate-100
          muted: '#94a3b8',      // slate-400
        },
        gray: {
          50: '#f9fafb',
          100: '#f3f4f6',
          200: '#e5e7eb',
          300: '#d1d5db',
          400: '#9ca3af',
          500: '#6b7280',
          600: '#4b5563',
          700: '#374151',
          800: '#1f2937',
          900: '#111827',
        }
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      }
    },
  },
  plugins: [],
}