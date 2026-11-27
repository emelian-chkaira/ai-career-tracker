// Docs media (see playwright.media.config.ts).
import { test, type Page } from "@playwright/test";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
const S = fileURLToPath(new URL("../../docs/screenshots", import.meta.url));
test.describe.configure({ timeout: 120000 });
const login = async (page: Page) => { await page.goto("/login"); await page.locator("#e").fill("demo@example.com"); await page.locator("#p").fill("demo-password-1"); await page.getByRole("button", { name: "Sign in" }).click(); await page.waitForURL((u) => !u.pathname.startsWith("/login")); };
const shot = async (page: Page, url: string, name: string, ms = 2500) => { await page.goto(url); await page.waitForTimeout(ms); await page.screenshot({ path: `${S}/${name}.png` }); };
test("jobs", async ({ page }) => {
  await login(page);
  await shot(page, "/?scope=all&q=data%20engineer", "web-jobs", 3500);
  await shot(page, "/", "web-my-feed", 3500);
  await shot(page, "/jobs/29899", "web-job-one-role");
  await shot(page, "/sponsors", "web-sponsors");
});
test("pipeline, settings, inbox", async ({ page }) => {
  await login(page);
  await shot(page, "/pipeline", "web-pipeline");
  await shot(page, "/profile", "web-settings"); await shot(page, "/inbox", "web-inbox");
});
test("crawler", async ({ page }) => {
  await login(page);
  await shot(page, "/crawler", "web-crawler", 3000);
  await page.getByRole("tab", { name: /Keep what matters/ }).click(); await page.waitForTimeout(700); await page.screenshot({ path: `${S}/web-crawler-step.png` });
  await shot(page, "/crawler?tab=boards", "web-job-boards", 3000); await shot(page, "/crawler?tab=jobs", "web-crawler-jobs", 3000);
});
test("setup dialog", async ({ page }) => {
  await page.goto("/register"); await page.locator("#n").fill("Sam"); await page.locator("#e").fill(`sam+${Date.now()}@example.com`); await page.locator("#p").fill("demo-password-1");
  await page.getByRole("checkbox").check(); await page.getByRole("button", { name: "Create account" }).click();
  const wiz = page.getByRole("dialog", { name: /Set up your search/ }); await wiz.waitFor({ timeout: 30000 });
  await wiz.getByRole("button", { name: /Software, IT & data/ }).click(); await page.waitForTimeout(500); await page.screenshot({ path: `${S}/web-setup-field.png` });
  await wiz.getByRole("button", { name: "Next" }).click(); await wiz.getByRole("button", { name: /^DACH/ }).click();
  await wiz.getByRole("button", { name: /Choose countries|Add country/ }).click(); await wiz.getByRole("button", { name: /United Arab Emirates/ }).click();
  await wiz.getByRole("button", { name: /Remote$/ }).click(); await page.waitForTimeout(500); await page.screenshot({ path: `${S}/web-setup-places.png` });
});
