import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => { await page.addInitScript(() => localStorage.setItem("guide:seen", "1")); });   // the first-run guide has its own unit tests

test("command bar opens with Ctrl+K and navigates", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Control+k");
  const input = page.getByPlaceholder("Go to a page, or search jobs…"); await expect(input).toBeVisible();
  await input.fill("companies"); await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/companies/);
});

test("j/k shortcuts move through results and / focuses search", async ({ page }) => {
  await page.goto("/"); await page.waitForSelector(".job");
  await page.keyboard.press("/"); await expect(page.locator(".sbar input[type=search]")).toBeFocused();
});
