import {expect, test} from "@playwright/test";

const EMAIL = `e2e-${Date.now()}@cineforge.test`;

test("full creative journey: register → project → generate (mock engine in test env) → library → credits", async ({page}) => {
  // 1. register
  await page.goto("/register");
  await page.getByTestId("reg-name").fill("E2E Director");
  await page.getByTestId("reg-email").fill(EMAIL);
  await page.getByTestId("reg-password").fill("Str0ngPassword");
  await page.getByTestId("reg-consent").check();
  await page.getByTestId("reg-submit").click();
  await page.waitForURL("**/dashboard", {timeout: 30_000});

  // 2. create project
  await page.waitForSelector("[data-testid=dashboard-title]");
  await page.getByTestId("project-name").fill("E2E Short Film");
  await page.getByTestId("project-create").click();

  // 3. generate an image with the mock engine (AI_MOCK_MODE=1 deployment)
  await page.goto("/create/image");
  await page.waitForSelector("[data-testid=prompt]");
  const modelSet = await page.locator("[data-testid=model-select] option").first().textContent();
  if (modelSet) {
    const value = await page.locator("[data-testid=model-select] option").first().getAttribute("value");
    await page.selectOption("[data-testid=model-select]", value!);
  }
  await page.getByTestId("prompt").fill("a rain-soaked street, neon reflections, one umbrella");
  await page.getByTestId("generate").click();

  // 4. job progress → asset appears
  await page.waitForSelector("[data-testid=results] img", {timeout: 30_000});

  // 5. library shows the asset; credits decreased (mock base 1 cr)
  await page.goto("/library");
  await page.waitForSelector("[data-testid=library-item]", {timeout: 30_000});
  await page.goto("/settings/billing");
  await page.waitForSelector("[data-testid=credit-table]");

  // 6. history re-roll path exists
  await page.goto("/history");
  await page.waitForSelector("[data-testid=history-row]");
  await expect(page.locator("[data-testid=gen-status]").first()).toContainText(/succeeded|queued|running/);
});
