// Docs media (see playwright.media.config.ts).
import { test, type Page } from "@playwright/test";
import { execSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
const S = fileURLToPath(new URL("../../docs/screenshots", import.meta.url)), T = os.tmpdir(), API = `${process.env.MEDIA_URL ?? "http://localhost:8790"}/api/v1`;
const login = async (page: Page) => { await page.goto("/login"); await page.locator("#e").fill("demo@example.com"); await page.locator("#p").fill("demo-password-1"); await page.getByRole("button", { name: "Sign in" }).click(); await page.waitForURL((u) => !u.pathname.startsWith("/login")); };
test("auth", async ({ page }) => { await page.goto("/login"); await page.waitForTimeout(2500); await page.screenshot({ path: `${S}/web-auth.png` }); });
test("cv studio with its real PDF", async ({ page, request }) => {
  const tok = (await (await request.post(`${API}/auth/login`, { data: { email: "demo@example.com", password: "demo-password-1" } })).json()).access_token;
  const h = { Authorization: `Bearer ${tok}` };
  const draft = (await (await request.get(`${API}/me/cv/draft`, { headers: h })).json()).draft;
  const pdf = await (await request.post(`${API}/cv/preview`, { headers: h, data: { cv: draft.cv, template: "modern", paper: "a4" } })).json();
  writeFileSync(`${T}/cv.pdf`, Buffer.from(pdf.pdf_b64, "base64")); try { execSync(`sips -s format png -Z 1400 "${T}/cv.pdf" --out "${T}/cv.png"`); } catch { test.skip(true, "needs macOS sips to render the PDF page"); }   // headless Chromium cannot show PDFs inline
  const png = readFileSync(`${T}/cv.png`).toString("base64");
  await login(page); await page.goto("/cv"); await page.waitForTimeout(5000);
  await page.evaluate((b64) => { const f = document.querySelector("iframe.pdfview"); if (!f) return; const img = document.createElement("img"); img.src = "data:image/png;base64," + b64;
    img.style.cssText = "width:100%;height:100%;object-fit:contain;object-position:top;background:#fff;border-radius:10px"; f.replaceWith(img); }, png);
  await page.waitForTimeout(600); await page.screenshot({ path: `${S}/web-cv-studio.png` });
});
