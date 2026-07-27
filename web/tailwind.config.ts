import type { Config } from 'tailwindcss'

/**
 * Every colour resolves to a CSS variable holding an `R G B` triplet, which is
 * what lets `bg-card/60` and `text-gold/80` work while themes swap underneath.
 *
 * The scales below are deliberately short. A type scale with twenty sizes gets
 * used inconsistently; one with eight gets used correctly.
 */
const rgb = (name: string) => `rgb(var(--${name}) / <alpha-value>)`

const config: Config = {
  darkMode: ['class', '[data-theme="dark"]'],
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        canvas: rgb('canvas'),
        surface: rgb('surface'),
        card: rgb('card'),
        raised: rgb('raised'),
        overlay: rgb('overlay'),
        sunken: rgb('sunken'),
        page: rgb('page'),

        ink: {
          DEFAULT: rgb('ink'),
          2: rgb('ink-2'),
          3: rgb('ink-3'),
          4: rgb('ink-4'),
          page: rgb('page-ink'),
        },

        gold: { DEFAULT: rgb('gold'), soft: rgb('gold-soft') },
        indigo: { DEFAULT: rgb('indigo'), soft: rgb('indigo-soft') },
        success: rgb('success'),
        warning: rgb('warning'),
        danger: rgb('danger'),
        info: rgb('info'),

        line: { DEFAULT: rgb('line'), strong: rgb('line-strong') },
      },

      borderRadius: {
        sm: 'var(--r-sm)',
        DEFAULT: 'var(--r)',
        md: 'var(--r)',
        lg: 'var(--r-lg)',
        xl: 'var(--r-xl)',
        '2xl': 'var(--r-2xl)',
      },

      boxShadow: {
        sm: 'var(--shadow-sm)',
        DEFAULT: 'var(--shadow)',
        lg: 'var(--shadow-lg)',
        xl: 'var(--shadow-xl)',
        glow: 'var(--shadow-glow)',
        // The inset highlight that makes a surface look lit from above.
        lift: 'var(--shadow), inset 0 1px 0 0 rgb(255 255 255 / 0.05)',
      },

      fontFamily: {
        sans: ['var(--font-sans)', 'Inter', 'Segoe UI Variable Text', 'Segoe UI',
               'system-ui', 'sans-serif'],
        serif: ['var(--font-serif)', 'Literata', 'Source Serif 4', 'Georgia',
                'serif'],
        mono: ['var(--font-mono)', 'JetBrains Mono', 'Cascadia Code',
               'Consolas', 'monospace'],
      },

      fontSize: {
        // [size, { lineHeight, letterSpacing }] - tracking tightens as size
        // grows, which is what stops large text looking loose and amateur.
        '2xs': ['0.6875rem', { lineHeight: '1rem', letterSpacing: '0.02em' }],
        xs: ['0.75rem', { lineHeight: '1.125rem', letterSpacing: '0.01em' }],
        sm: ['0.8125rem', { lineHeight: '1.25rem', letterSpacing: '0.005em' }],
        base: ['0.875rem', { lineHeight: '1.4rem', letterSpacing: '0' }],
        md: ['0.9375rem', { lineHeight: '1.5rem', letterSpacing: '-0.005em' }],
        lg: ['1.0625rem', { lineHeight: '1.6rem', letterSpacing: '-0.01em' }],
        xl: ['1.25rem', { lineHeight: '1.75rem', letterSpacing: '-0.015em' }],
        '2xl': ['1.625rem', { lineHeight: '2.05rem', letterSpacing: '-0.02em' }],
        '3xl': ['2.125rem', { lineHeight: '2.5rem', letterSpacing: '-0.025em' }],
        '4xl': ['2.875rem', { lineHeight: '3.15rem', letterSpacing: '-0.03em' }],
      },

      spacing: {
        // 4px grid, plus the few odd values a real layout always needs.
        0.75: '0.1875rem',
        1.25: '0.3125rem',
        1.75: '0.4375rem',
        2.25: '0.5625rem',
        4.5: '1.125rem',
        13: '3.25rem',
        15: '3.75rem',
        18: '4.5rem',
        22: '5.5rem',
        sidebar: '17rem',
        'sidebar-collapsed': '3.75rem',
        inspector: '20rem',
        titlebar: '2.75rem',
        statusbar: '1.875rem',
      },

      transitionTimingFunction: {
        DEFAULT: 'var(--ease)',
        out: 'var(--ease-out)',
        spring: 'var(--spring)',
      },
      transitionDuration: {
        fast: '120ms',
        DEFAULT: '200ms',
        slow: '320ms',
      },

      keyframes: {
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'fade-up': {
          from: { opacity: '0', transform: 'translateY(6px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'scale-in': {
          from: { opacity: '0', transform: 'scale(0.97)' },
          to: { opacity: '1', transform: 'scale(1)' },
        },
        'slide-from-right': {
          from: { transform: 'translateX(100%)' },
          to: { transform: 'translateX(0)' },
        },
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
        breathe: {
          '0%, 100%': { opacity: '0.55' },
          '50%': { opacity: '1' },
        },
      },
      animation: {
        'fade-in': 'fade-in var(--normal) var(--ease) both',
        'fade-up': 'fade-up var(--normal) var(--ease-out) both',
        'scale-in': 'scale-in var(--fast) var(--ease-out) both',
        'slide-from-right': 'slide-from-right var(--normal) var(--ease-out) both',
        'accordion-down': 'accordion-down var(--fast) var(--ease)',
        'accordion-up': 'accordion-up var(--fast) var(--ease)',
        breathe: 'breathe 2.4s var(--ease) infinite',
      },

      backgroundImage: {
        'gold-sheen':
          'linear-gradient(135deg, rgb(var(--gold) / 0.9), rgb(var(--gold) / 0.62))',
        'indigo-sheen':
          'linear-gradient(135deg, rgb(var(--indigo) / 0.9), rgb(var(--indigo) / 0.6))',
        'surface-sheen':
          'linear-gradient(180deg, rgb(255 255 255 / 0.035), transparent 60%)',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
}

export default config
