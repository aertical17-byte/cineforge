import {expect, test} from "@playwright/test";

// Real-UI screenshot capture for the public site (one honest product, no mockups).
// The mock engine is deliberate (no live keys in this environment): tiles labeled
// as test data on the site. Screenshots land in apps/e2e/shots → CI artifact ui-shots.

test.use({viewport: {width: 1440, height: 900}, deviceScaleFactor: 2});

test("capture real UI screenshots", async ({page}) => {
  page.on("pageerror", (e) => console.log("PAGEERROR:", e.message));

  // open the studio — no signup: a guest session is minted automatically
  await page.goto("/dashboard");
  await page.waitForSelector("[data-testid=dashboard-title]", {timeout: 30_000});
  await page.getByTestId("project-name").fill("Neon Streets — short");
  await page.getByTestId("project-create").click();

  // 1. dashboard
  await page.waitForTimeout(600);
  await page.screenshot({path: "shots/01-dashboard.png"});

  // 2. image studio, prompt ready
  await page.goto("/create/image");
  await page.waitForSelector("[data-testid=prompt]");
  await page.selectOption("[data-testid=model-select]", "mock-engine");
  await page.getByTestId("prompt").fill("a rain-soaked street, neon reflections, one umbrella");
  await page.waitForTimeout(600);
  await page.screenshot({path: "shots/02-studio.png"});

  // generate + wait for the asset so the library shot is real
  await page.getByTestId("generate").click();
  await page.waitForSelector("[data-testid=results] img", {timeout: 60_000});

  // 3. library
  await page.goto("/library");
  await page.waitForSelector("[data-testid=library-item]", {timeout: 30_000});
  await page.waitForTimeout(600);
  await page.screenshot({path: "shots/03-library.png"});

  // 4. history
  await page.goto("/history");
  await page.waitForSelector("[data-testid=history-row]");
  await page.waitForTimeout(400);
  await page.screenshot({path: "shots/04-history.png"});

  // 5. flowboard with a configured 2-step chain, run to success
  await page.goto("/flowboard");
  await page.waitForSelector("[data-testid=flow-builder]");
  await page.selectOption("[data-testid=flow-model-0]", "mock-engine");
  await page.fill("[data-testid=flow-prompt-0]", "neon alley establishing frame, rain-soaked");
  await page.selectOption("[data-testid=flow-model-1]", "mock-engine");
  await page.fill("[data-testid=flow-prompt-1]", "push in on the alley as the rain starts");
  await page.getByTestId("flow-run").click();
  await expect(page.getByTestId("flow-status")).toContainText("succeeded", {timeout: 90_000});
  await page.waitForTimeout(600);
  await page.screenshot({path: "shots/05-flowboard.png"});

  // 6. billing (credit ledger)
  await page.goto("/settings/billing");
  await page.waitForSelector("[data-testid=credit-table]");
  await page.waitForTimeout(400);
  await page.screenshot({path: "shots/06-billing.png"});

  // sanity: every shot exists and is non-trivial
  for (const name of ["01-dashboard", "02-studio", "03-library", "04-history", "05-flowboard", "06-billing"]) {
    expect((await import("fs")).statSync(`shots/${name}.png`).size).toBeGreaterThan(20_000);
  }
});
