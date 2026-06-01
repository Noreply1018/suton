import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "var(--color-text-main)",
        muted: "var(--color-text-muted)",
        subtle: "var(--color-text-subtle)",
        page: "var(--color-page-bg)",
        paper: "var(--color-paper-bg)",
        line: "var(--color-line)",
        accent: "var(--color-accent)",
        "accent-hover": "var(--color-accent-hover)",
        "accent-soft": "var(--color-accent-soft)",
        warning: "var(--color-warning)",
        danger: "var(--color-danger)",
        info: "var(--color-info)"
      },
      fontSize: {
        "page-title": ["22px", "30px"],
        "section-title": ["16px", "24px"],
        body: ["14px", "22px"],
        assist: ["12px", "18px"],
        label: ["11px", "16px"]
      },
      borderRadius: {
        control: "var(--radius-control)",
        card: "var(--radius-card)"
      },
      boxShadow: {
        floating: "var(--shadow-floating)"
      }
    }
  },
  plugins: []
};

export default config;
