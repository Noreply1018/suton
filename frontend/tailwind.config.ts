import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17201b",
        paper: "#f7f4ed",
        line: "#d8d0c2",
        accent: "#2f6f5e",
        signal: "#b94f31"
      }
    }
  },
  plugins: []
};

export default config;
