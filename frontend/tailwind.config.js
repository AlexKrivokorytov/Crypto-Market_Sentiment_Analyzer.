/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        // Display / heading font — Space Grotesk
        display: ['Space Grotesk', 'Plus Jakarta Sans', '-apple-system', 'sans-serif'],
        // Monospaced data / price font — JetBrains Mono
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
        // Body fallback — existing Plus Jakarta Sans
        sans: ['Plus Jakarta Sans', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
      },
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
        },

        // ── Sprint 5 Design System Tokens ──────────────────────────────
        // Gold accent — Fintech/Crypto primary (UI-UX Pro Max: Fintech/Crypto palette)
        gold: {
          50:  '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          DEFAULT: '#f59e0b', // amber-500 — primary brand token
          600: '#d97706',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f',
        },
        // Violet CTA — secondary accent
        violet: {
          300: '#c4b5fd',
          400: '#a78bfa',
          DEFAULT: '#8b5cf6', // violet-500 — CTA token
          600: '#7c3aed',
          700: '#6d28d9',
          800: '#5b21b6',
        },
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)'
      },
      keyframes: {
        'pulse-glow-bullish': {
          '0%, 100%': { boxShadow: '0 0 4px rgba(16, 185, 129, 0.2)' },
          '50%':       { boxShadow: '0 0 16px rgba(16, 185, 129, 0.5)' }
        },
        'pulse-glow-bearish': {
          '0%, 100%': { boxShadow: '0 0 4px rgba(244, 63, 94, 0.2)' },
          '50%':       { boxShadow: '0 0 16px rgba(244, 63, 94, 0.5)' }
        },
        'pulse-glow-gold': {
          '0%, 100%': { boxShadow: '0 0 4px rgba(245, 158, 11, 0.2)' },
          '50%':       { boxShadow: '0 0 20px rgba(245, 158, 11, 0.45)' }
        },
        'fade-in-up': {
          '0%':   { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' }
        },
        'slide-in-right': {
          '0%':   { transform: 'translateX(100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)',    opacity: '1' }
        },
        // Hardware-accelerated infinite ticker scroll (duplicated DOM for seamless loop)
        'ticker-scroll': {
          '0%':   { transform: 'translateX(0)' },
          '100%': { transform: 'translateX(-50%)' }
        },
        // Shimmer loading skeleton effect
        'shimmer': {
          '0%':   { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' }
        },
        // Slow ambient nebula background rotation
        'nebula-rotate': {
          '0%':   { transform: 'rotate(0deg) scale(1)' },
          '50%':  { transform: 'rotate(180deg) scale(1.05)' },
          '100%': { transform: 'rotate(360deg) scale(1)' }
        },
      },
      animation: {
        'glow-bullish':   'pulse-glow-bullish 2.5s infinite ease-in-out',
        'glow-bearish':   'pulse-glow-bearish 2.5s infinite ease-in-out',
        'glow-gold':      'pulse-glow-gold 3s infinite ease-in-out',
        'fade-in-up':     'fade-in-up 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'slide-in-right': 'slide-in-right 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'ticker':         'ticker-scroll 40s linear infinite',
        'shimmer':        'shimmer 1.8s ease-in-out infinite',
        'nebula':         'nebula-rotate 60s linear infinite',
      }
    },
  },
  plugins: [],
}
