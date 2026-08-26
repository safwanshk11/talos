/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Near-black surfaces — the whole app is built on these, not on blue.
        dark: "#050505",
        sidebar: "#030303",
        card: "#0d0d0f",
        "card-hover": "#141416",
        input: "#020202",
        subtle: "rgba(255,255,255,0.07)",
        muted: "rgba(255,255,255,0.14)",
        // Explicit text tiers (also mirrored as CSS vars for non-Tailwind usage)
        "text-primary": "#f5f5f5",
        "text-secondary": "#a0a0a6",
        "text-muted": "#68686f",
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      boxShadow: {
        subtle: '0 4px 24px -8px rgba(0,0,0,0.5)',
        lift: '0 12px 32px -12px rgba(0,0,0,0.6)',
      },
      keyframes: {
        'fade-up': { '0%': { opacity: 0, transform: 'translateY(24px)' }, '100%': { opacity: 1, transform: 'translateY(0)' } },
        'breathe': { '0%,100%': { opacity: 1 }, '50%': { opacity: 0.55 } },
      },
      animation: {
        'fade-up': 'fade-up 0.6s cubic-bezier(0.16,1,0.3,1) both',
        breathe: 'breathe 2.4s ease-in-out infinite',
      },
    },
  },
  plugins: [],
};
