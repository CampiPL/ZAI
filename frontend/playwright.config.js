import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  timeout: 30000,
  use: {
    baseURL: process.env.SPLOT_API_URL || "http://127.0.0.1:8000",
    headless: true,
    trace: "retain-on-failure",
  },
});
