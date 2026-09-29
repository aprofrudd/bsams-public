import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        heading: ['var(--font-chakra)', 'sans-serif'],
        body: ['var(--font-roboto)', 'sans-serif'],
      },
      colors: {
        // BSAMS Design System
        primary: {
          DEFAULT: '#090A3D',
          dark: '#07083D',
        },
        accent: {
          DEFAULT: '#33CBF4',
          hover: '#2BB8E0',
        },
        secondary: {
          DEFAULT: '#2074AA',
          muted: '#2D5585',
        },
      },
    },
  },
  plugins: [],
};

export default config;
