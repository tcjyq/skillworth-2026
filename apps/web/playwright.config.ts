import { defineConfig, devices } from "@playwright/test";

const webPort = process.env.SKILLWORTH_E2E_WEB_PORT ?? "13001";
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? `http://127.0.0.1:${webPort}`;
const e2eMode = process.env.SKILLWORTH_E2E_MODE ?? "demo";

export default defineConfig({
  testDir: "./e2e",
  testMatch: e2eMode === "demo" ? ["navigation.spec.ts", "demo.spec.ts"] : "**/*.spec.ts",
  testIgnore: e2eMode === "real" ? ["demo.spec.ts"] : [],
  timeout: 30_000,
  use: { baseURL, trace: "retain-on-failure" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], channel: "msedge", viewport: { width: 1440, height: 900 } } },
    { name: "mobile", use: { ...devices["Pixel 7"], channel: "msedge" } },
  ],
});
