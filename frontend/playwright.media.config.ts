import { defineConfig } from "@playwright/test";

// Screenshots and the demo video for the README (docs/screenshots, docs/media). Not part of the test suite.
// 1. Start a local API without Firebase so the demo account stays local:  CAREERS_FIREBASE_API_KEY= .venv/bin/uvicorn app.main:app --port 8790
// 2. Seed the demo account:  cd backend && PYTHONPATH=. .venv/bin/python scripts/seed_demo.py
// 3. npm run media
export default defineConfig({
  testDir: "docs-media", timeout: 180_000, workers: 1, reporter: "list",
  use: { baseURL: process.env.MEDIA_URL ?? "http://localhost:8790", colorScheme: "dark", locale: "en-US", viewport: { width: 1440, height: 900 } },
});
