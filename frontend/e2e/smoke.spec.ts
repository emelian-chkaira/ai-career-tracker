import { expect, test } from "@playwright/test";

const stamp = Date.now();
const email = `e2e+${stamp}@example.com`;
const password = "correct-horse-1";

test("search, sign up, track a job and open the AI panels", async ({ page }) => {
  // public: the job list renders with real results
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
  await expect(page.locator(".job").first()).toBeVisible({ timeout: 15_000 });

  // sign up
  await page.goto("/register");
  await page.locator("#n").fill("E2E User");
  await page.locator("#e").fill(email);
  await page.locator("#p").fill(password);
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Create account" }).click();
  // the setup dialog opens after sign-up: pick a field, a city, a title, then see "My feed"
  const wiz = page.getByRole("dialog", { name: /Set up your search/ });
  await expect(wiz).toBeVisible({ timeout: 15_000 });
  await expect(wiz.getByRole("button", { name: "Next" })).toBeDisabled();                         // a field is required
  await wiz.getByRole("button", { name: /Software, IT & data/ }).click();
  await wiz.getByRole("button", { name: "Next" }).click();
  await wiz.getByRole("button", { name: "+ Amsterdam" }).click(); await wiz.getByRole("button", { name: "Next" }).click();
  await wiz.getByRole("button", { name: "+ Backend Developer" }).click(); await wiz.getByRole("button", { name: "Next" }).click();
  await wiz.getByRole("button", { name: "+ Python" }).click(); await wiz.getByRole("button", { name: "Next" }).click();
  const done = page.getByRole("dialog", { name: "Your feed is ready" }); await expect(done.getByText("Software, IT & data")).toBeVisible();
  await done.getByRole("button", { name: "Show my jobs" }).click(); await expect(done).toHaveCount(0);
  await expect(page.getByRole("button", { name: "My feed" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByText(/From your profile: .*Software, IT & data.*Amsterdam or remote/)).toBeVisible();
  await page.reload(); await expect(page.getByRole("dialog")).toHaveCount(0);                       // finished: never pops up again

  // open a job, see the AI fit box, track it
  await page.goto("/");
  await page.locator(".job").first().click();
  await expect(page.getByRole("button", { name: /AI fit/ })).toBeVisible();
  await page.locator("select").filter({ hasText: "Track…" }).first().selectOption("applied");
  await expect(page.getByRole("button", { name: /Tracking/ })).toBeVisible();
  await page.getByPlaceholder("Add to the timeline…").fill("Sent the application");
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page.getByText("Sent the application")).toBeVisible();

  // the pipeline shows it
  await page.goto("/pipeline");
  await expect(page.getByText("Applied").first()).toBeVisible();
  const col = page.getByRole("button", { name: /Minimise Applied/ }); await col.click();
  await expect(page.getByRole("button", { name: /Expand Applied/ })).toBeVisible(); await expect(page.locator(".pcard")).toHaveCount(0);
  await page.getByRole("button", { name: "Account menu" }).click(); await expect(page.getByRole("menuitem", { name: "Sign out" })).toBeVisible();
});

test("panels minimise and the assistant docks, minimises and closes", async ({ page }) => {
  await page.goto("/register"); await page.locator("#n").fill("Dock User"); await page.locator("#e").fill(`dock+${Date.now()}@example.com`); await page.locator("#p").fill("correct-horse-1");
  await page.getByRole("checkbox").check(); await page.getByRole("button", { name: "Create account" }).click();
  await page.getByRole("button", { name: "Skip setup" }).click({ timeout: 15_000 }); await expect(page.getByRole("button", { name: "Account menu" }).first()).toBeVisible();
  await page.goto("/"); await page.locator(".job").first().click();
  const fit = page.getByRole("button", { name: /AI fit/ }); await expect(fit).toHaveAttribute("aria-expanded", "true"); await fit.click(); await expect(fit).toHaveAttribute("aria-expanded", "false");
  await page.getByRole("button", { name: /Ask the assistant/ }).click();
  const dock = page.getByRole("region", { name: /Assistant/ }); await expect(dock).toBeVisible();
  await dock.getByRole("button", { name: "Minimise" }).click(); await expect(dock.getByLabel("Message")).toHaveCount(0);
  await dock.getByRole("button", { name: "Expand" }).click(); await expect(dock.getByLabel("Message")).toBeVisible();
  await dock.getByRole("button", { name: "Close" }).click(); await expect(dock).toHaveCount(0);
});
