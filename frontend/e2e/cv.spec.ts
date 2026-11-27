import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => { await page.addInitScript(() => localStorage.setItem("guide:seen", "1")); });   // the first-run guide has its own unit tests

const CV = `Sam Doe
sam@example.com | Utrecht
Summary
Backend developer who builds APIs in Python.
Experience
Backend Developer  Acme  2021 - 2024
- Built REST APIs in Python and SQL
- Cut query time by 60%
Skills
Python, SQL, Docker
Education
BSc Computer Science  TU Delft  2017 - 2021
`;

test("CV Studio: import, live preview, switch layout, export Reactive Resume JSON", async ({ page }) => {
  await page.goto("/cv");
  await page.locator('input[type="file"]').last().setInputFiles({ name: "cv.txt", mimeType: "text/plain", buffer: Buffer.from(CV) });
  await page.getByRole("tab", { name: /Layout/ }).click({ timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Layout & PDF" })).toBeVisible();
  const frame = page.locator("iframe.pdfview");
  await expect(frame).toBeVisible({ timeout: 30_000 });                       // live preview appears without pressing anything
  const first = await frame.getAttribute("src");
  await page.getByRole("radio", { name: "Modern layout" }).click();
  await expect.poll(async () => frame.getAttribute("src"), { timeout: 30_000 }).not.toBe(first);   // and rebuilds on change
  await page.getByRole("button", { name: "Experience", exact: true }).click();                // icon rail: one section at a time
  await page.getByRole("button", { name: "Edit", exact: true }).first().click();
  await page.getByLabel("Role").fill("Senior Backend Developer");
  await page.getByRole("button", { name: "Bold" }).first().click();
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("Senior Backend Developer")).toBeVisible();
  const [dl] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "Reactive Resume JSON" }).click()]);
  expect(dl.suggestedFilename()).toContain("reactive-resume");
});

test("each account has its own CV: a second account on the same browser starts empty", async ({ page }) => {
  const signUp = async (who: string) => {
    await page.goto("/register"); await page.locator("#n").fill(who); await page.locator("#e").fill(`${who.toLowerCase()}+${Date.now()}@example.com`); await page.locator("#p").fill("correct-horse-1");
    await page.getByRole("checkbox").check(); await page.getByRole("button", { name: "Create account" }).click();
    await page.getByRole("button", { name: "Skip setup" }).click({ timeout: 15_000 });
  };
  const signOut = async () => { await page.getByRole("button", { name: "Account menu" }).first().click(); await page.getByRole("menuitem", { name: "Sign out" }).click(); };
  await signUp("Alice");
  await page.goto("/cv");
  await page.locator('input[type="file"]').last().setInputFiles({ name: "cv.txt", mimeType: "text/plain", buffer: Buffer.from(CV) });
  await expect(page.getByText("Saved to your account")).toBeVisible({ timeout: 15_000 });
  await page.waitForTimeout(1500);                                                               // the debounced save reaches the server
  await signOut();
  await signUp("Bob"); await page.goto("/cv");
  await expect(page.getByRole("heading", { name: /Drop your CVs? here/ })).toBeVisible(); await expect(page.getByText("Sam Doe")).toHaveCount(0);   // Bob never sees Alice's CV
});
