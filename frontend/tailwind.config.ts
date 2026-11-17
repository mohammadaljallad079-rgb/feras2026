import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  darkMode: ["selector", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        card: "var(--card)",
        ink: "var(--ink)",
        mut: "var(--mut)",
        line: "var(--line)",
        gold: "var(--gold)",
        goldink: "var(--goldink)",
        acc: "var(--acc)",
        accfg: "var(--accfg)",
        ok: "var(--ok)",
        warn: "var(--warn)",
        bad: "var(--bad)",
        okbg: "var(--okbg)",
        warnbg: "var(--warnbg)",
        badbg: "var(--badbg)",
        side: "var(--side)",
        sidefg: "var(--sidefg)",
        pearl: "var(--pearl)",
        // Public-website brand palette, taken from the official logo artwork
        // (deep teal #096b82, bright teal #0c8fad) and a warm sand accent.
        brand: {
          deep: "var(--brand-deep)",
          bright: "var(--brand-bright)",
          ink: "var(--brand-ink)",
          sand: "var(--brand-sand)",
          mist: "var(--brand-mist)",
          paper: "var(--brand-paper)",
          slate: "var(--brand-slate)",
          line: "var(--brand-line)",
        },
      },
      borderRadius: {
        card: "10px",
        control: "7px",
      },
      fontSize: {
        base: ["15px", { lineHeight: "1.7" }],
        page: ["22px", { lineHeight: "1.7" }],
        section: ["16px", { lineHeight: "1.7" }],
        secondary: ["13px", { lineHeight: "1.7" }],
      },
      spacing: {
        s1: "4px",
        s2: "8px",
        s3: "12px",
        s4: "16px",
        s6: "24px",
        s10: "40px",
      },
      width: { sidebar: "240px" },
      screens: {
        // Below 820px the sidebar becomes a mobile drawer.
        nav: "820px",
      },
    },
  },
  plugins: [],
};

export default config;
