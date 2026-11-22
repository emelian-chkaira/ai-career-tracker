// Docs media (see playwright.media.config.ts).
import { test, type Page } from "@playwright/test";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
const S = fileURLToPath(new URL("../../docs/screenshots", import.meta.url));
const login = async (page: Page) => { await page.goto("/login"); await page.locator("#e").fill("demo@example.com"); await page.locator("#p").fill("demo-password-1"); await page.getByRole("button", { name: "Sign in" }).click(); await page.waitForURL((u) => !u.pathname.startsWith("/login")); };
test.describe("light", () => {
  test.use({ viewport: { width: 1440, height: 900 }, colorScheme: "light" });
  test("jobs light", async ({ page }) => { await login(page); await page.goto("/?scope=all&q=data%20engineer"); await page.waitForTimeout(3500); await page.screenshot({ path: `${S}/web-jobs-light.png` }); });
});
test.describe("phone", () => {
  test.use({ viewport: { width: 390, height: 844 }, colorScheme: "dark", isMobile: true, hasTouch: true });
  test("phone", async ({ page }) => { await login(page); await page.goto("/?scope=all&q=python"); await page.waitForTimeout(3500); await page.screenshot({ path: `${S}/web-mobile.png` }); });
});
