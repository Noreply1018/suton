import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./frontend/e2e",
  timeout: 180_000,
  grep: process.env.SCENARIO ? new RegExp(process.env.SCENARIO) : undefined,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000",
    trace: "on-first-retry"
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] }
    }
  ]
});
