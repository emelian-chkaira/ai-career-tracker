import { defineConfig } from "@playwright/test";

/** End-to-end smoke tests against a running stack (API serving the built web app). Start it with `./run.sh api` in backend/. */
export default defineConfig({
  testDir: "./e2e", timeout: 45_000, retries: process.env.CI ? 1 : 0, reporter: [["list"]],
  use: { baseURL: process.env.E2E_URL ?? "http://localhost:8787", trace: "retain-on-failure" },
});
