import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17201b",
        paper: "#f2f6ec",
        line: "#d6e1d2",
        accent: "#315f43",
        signal: "#b94f31",
        "teal-soft": "#cbd8c9"
      }
    }
  },
  plugins: []
};

export default config;
