// Docs media (see playwright.media.config.ts).
import { test } from "@playwright/test";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
test.use({ viewport: { width: 1280, height: 800 }, colorScheme: "dark", locale: "en-US", video: { mode: "on", size: { width: 1280, height: 800 } } });
test.setTimeout(180000);
test("tour", async ({ page }) => {
  const cvPng = path.join(os.tmpdir(), "cv.png"); const png = existsSync(cvPng) ? readFileSync(cvPng).toString("base64") : "";   // rendered by auth-and-cv.spec.ts
  const pause = (ms: number) => page.waitForTimeout(ms);
  await page.goto("/login"); await pause(1200);
  await page.locator("#e").pressSequentially("demo@example.com", { delay: 35 }); await page.locator("#p").pressSequentially("demo-password-1", { delay: 35 }); await pause(300);
  await page.getByRole("button", { name: "Sign in" }).click(); await page.waitForURL((u) => !u.pathname.startsWith("/login")); await pause(2200);
  await page.goto("/?scope=all"); await pause(1500);
  const box = page.getByLabel("Search jobs"); await box.click(); await box.pressSequentially("data engineer", { delay: 70 }); await box.press("Enter"); await pause(2500);
  const cards = page.locator(".list .job"); await cards.nth(1).click(); await pause(1800); await cards.nth(3).click(); await pause(1800);
  await page.locator(".list").hover(); await page.mouse.wheel(0, 500); await pause(1200);
  await page.getByRole("button", { name: "My feed" }).click(); await pause(2500);
  await page.goto("/jobs/23336"); await pause(1500); await page.mouse.wheel(0, 400); await pause(2000);
  await page.goto("/pipeline"); await pause(3000);
  await page.goto("/cv"); await pause(3500);
  if (png) await page.evaluate((b64) => { const f = document.querySelector("iframe.pdfview"); if (!f) return; const img = document.createElement("img"); img.src = "data:image/png;base64," + b64;
    img.style.cssText = "width:100%;height:100%;object-fit:contain;object-position:top;background:#fff;border-radius:10px"; f.replaceWith(img); }, png);
  await page.getByRole("button", { name: /Skills/ }).first().click().catch(() => {}); await pause(1500); await page.getByRole("radio", { name: "Classic layout" }).click().catch(() => {}); await pause(1500);
  await page.goto("/crawler"); await pause(2000);
  for (const s of [/Find employers/, /Understand postings/, /Keep what matters/]) { await page.getByRole("tab", { name: s }).click(); await pause(1700); }
  await page.getByRole("tab", { name: /Job boards/ }).click(); await pause(2200); await page.mouse.wheel(0, 700); await pause(1800);
  await page.goto("/profile"); await pause(2500);
  const v = page.video(); await page.close(); if (v) writeFileSync(path.join(os.tmpdir(), "video-path.txt"), await v.path());
});
