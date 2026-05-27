/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))'
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))'
        },
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))'
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))'
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))'
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))'
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))'
        },
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        
        // Sentiment specific colors
        bullish: {
          DEFAULT: '#10b981', // emerald-500
          glow: 'rgba(16, 185, 129, 0.15)',
        },
        bearish: {
          DEFAULT: '#f43f5e', // rose-500
          glow: 'rgba(244, 63, 94, 0.15)',
        },
        neutral: {
          DEFAULT: '#6b7280', // gray-500
          glow: 'rgba(107, 114, 128, 0.15)',
        }
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)'
      },
      keyframes: {
        'pulse-glow-bullish': {
          '0%, 100%': { boxShadow: '0 0 4px rgba(16, 185, 129, 0.2)' },
          '50%': { boxShadow: '0 0 16px rgba(16, 185, 129, 0.5)' }
        },
        'pulse-glow-bearish': {
          '0%, 100%': { boxShadow: '0 0 4px rgba(244, 63, 94, 0.2)' },
          '50%': { boxShadow: '0 0 16px rgba(244, 63, 94, 0.5)' }
        },
        'fade-in-up': {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' }
        },
        'slide-in-right': {
          '0%': { transform: 'translateX(100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' }
        }
      },
      animation: {
        'glow-bullish': 'pulse-glow-bullish 2.5s infinite ease-in-out',
        'glow-bearish': 'pulse-glow-bearish 2.5s infinite ease-in-out',
        'fade-in-up': 'fade-in-up 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'slide-in-right': 'slide-in-right 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards'
      }
    },
  },
  plugins: [],
}
