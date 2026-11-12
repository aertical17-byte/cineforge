import {expect, test} from "@playwright/test";

test("full creative journey: open studio (auto guest) → project → generate (mock engine in test env) → library → credits", async ({page}) => {
  // Browser-level failures land in CI logs (cheap, high signal).
  page.on("pageerror", (e) => console.log("PAGEERROR:", e.message));
  page.on("console", (m) => {
    if (m.type() === "error") console.log("CONSOLE:", m.text());
  });

  // 1. open the studio — no signup: the web app mints a guest session automatically
  await page.goto("/dashboard");
  await page.waitForSelector("[data-testid=dashboard-title]", {timeout: 30_000});

  // 2. create project
  await page.getByTestId("project-name").fill("E2E Short Film");
  await page.getByTestId("project-create").click();

  // 3. generate an image with the mock engine
  await page.goto("/create/image");
  await page.waitForSelector("[data-testid=prompt]");
  // The mock engine is deliberate: this deployment has no live provider keys, so any
  // real engine would honestly end in provider_not_configured. The journey checks the
  // product flow (form → job → asset), not someone else's API.
  await page.selectOption("[data-testid=model-select]", "mock-engine");
  await page.getByTestId("prompt").fill("a rain-soaked street, neon reflections, one umbrella");
  await page.getByTestId("generate").click();

  // 4. job progress → asset appears (the worker loop process runs alongside the API)
  await page.waitForSelector("[data-testid=results] img", {timeout: 60_000});

  // 5. library shows the asset; billing table reflects the spend
  await page.goto("/library");
  await page.waitForSelector("[data-testid=library-item]", {timeout: 30_000});
  await page.goto("/settings/billing");
  await page.waitForSelector("[data-testid=credit-table]");

  // 6. history lists the run with a live status
  await page.goto("/history");
  await page.waitForSelector("[data-testid=history-row]");
  await expect(page.locator("[data-testid=gen-status]").first()).toContainText(/succeeded|queued|running/);
});
