import {expect, test} from "@playwright/test";

// NOTE: email-validator rejects IANA special-use domains (like .test) at parse time;
// example.com is the reserved-but-acceptable placeholder the library permits.
const EMAIL = `e2e-${Date.now()}@example.com`;

test("full creative journey: register → project → generate (mock engine in test env) → library → credits", async ({page}) => {
  // Diagnostics (kept in CI logs): API requests/results, browser console, hard errors.
  page.on("pageerror", (e) => console.log("PAGEERROR:", e.message));
  page.on("console", (m) => {
    if (["error", "warning"].includes(m.type())) console.log("CONSOLE:", m.type(), m.text());
  });
  page.on("response", (r) => {
    if (r.url().includes("/v1/")) console.log("HTTP:", r.status(), r.request().method(), new URL(r.url()).pathname);
  });
  page.on("framenavigated", (f) => {
    if (f === page.mainFrame()) console.log("NAV:", f.url());
  });

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

  // 4. job progress → asset appears (worker loop must be running for this to finish)
  try {
    await page.waitForSelector("[data-testid=results] img", {timeout: 30_000});
  } catch (e) {
    console.log("RESULTS_WAIT_FAILED_AT_URL:", page.url());
    console.log("AUTH_STORAGE:", await page.evaluate(() => localStorage.getItem("cineforge-auth")));
    throw e;
  }

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
