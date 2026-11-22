import { expect, test } from "@playwright/test";

test("panes can be resized by dragging the divider, and the width is remembered", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 800 });
  await page.goto("/"); await expect(page.locator(".job").first()).toBeVisible({ timeout: 15_000 });
  const list = page.locator(".jfull .list"); const before = (await list.boundingBox())!.width;
  const bar = (await page.locator(".jfull .split").boundingBox())!; const y = bar.y + bar.height / 2, x = bar.x + bar.width / 2;
  await page.mouse.move(x, y); await page.mouse.down(); await page.mouse.move(x + 120, y, { steps: 6 }); await page.mouse.up();
  const after = (await list.boundingBox())!.width; expect(after).toBeGreaterThan(before + 80);
  await page.reload(); await expect(page.locator(".job").first()).toBeVisible({ timeout: 15_000 });
  expect((await page.locator(".jfull .list").boundingBox())!.width).toBeGreaterThan(before + 80);          // remembered
  await page.locator(".jfull .split").dblclick(); await expect.poll(async () => (await page.locator(".jfull .list").boundingBox())!.width).toBeLessThan(after - 80);   // double-click resets
});

test("job list loads more results while you scroll (no pager)", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 800 });
  await page.goto("/"); await expect(page.locator(".job").first()).toBeVisible({ timeout: 15_000 });
  await expect(page.locator(".pager")).toHaveCount(0);
  const n0 = await page.locator(".job").count();
  await page.locator(".jfull .list").evaluate((el) => { el.scrollTop = el.scrollHeight; });
  await expect.poll(() => page.locator(".job").count(), { timeout: 15_000 }).toBeGreaterThan(n0);
});
