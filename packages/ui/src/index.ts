// Design Tokens & HSL Curated Palettes for DigitalQ Labs
export const tailwindThemePreset = {
  theme: {
    extend: {
      colors: {
        background: 'hsl(224 71% 4%)', // Deep modern SaaS dark theme background
        foreground: 'hsl(210 20% 98%)',
        card: {
          DEFAULT: 'hsl(224 71% 7%)',
          foreground: 'hsl(210 20% 98%)',
        },
        popover: {
          DEFAULT: 'hsl(224 71% 4%)',
          foreground: 'hsl(210 20% 98%)',
        },
        primary: {
          DEFAULT: 'hsl(263.4 70% 50.4%)', // Slate Purple
          foreground: 'hsl(210 20% 98%)',
        },
        secondary: {
          DEFAULT: 'hsl(215 27.9% 16.9%)',
          foreground: 'hsl(210 20% 98%)',
        },
        muted: {
          DEFAULT: 'hsl(215 27.9% 16.9%)',
          foreground: 'hsl(210 40% 96.1%)',
        },
        accent: {
          DEFAULT: 'hsl(263.4 70% 50.4%)',
          foreground: 'hsl(210 20% 98%)',
        },
        border: 'hsl(215 27.9% 16.9%)',
        input: 'hsl(215 27.9% 16.9%)',
        ring: 'hsl(263.4 70% 50.4%)',
      },
      borderRadius: {
        lg: '0.75rem',
        md: '0.5rem',
        sm: '0.25rem',
      },
      boxShadow: {
        glass: '0 8px 32px 0 rgba(0, 0, 0, 0.37)', // Modern premium glassmorphism shadow
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
};
export default tailwindThemePreset;
