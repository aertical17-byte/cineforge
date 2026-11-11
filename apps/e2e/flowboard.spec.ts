import {expect, test} from "@playwright/test";

// Flowboard E2E: the whole point is that the WORKER advances the chain in a separate
// process — API-side unit tests cannot prove that. Mock engines are explicit and
// deliberate: this deployment has no live provider keys (see journey.spec.ts note).
const EMAIL = `flow-${Date.now()}@example.com`;

test("flowboard chain: image node → video node, worker advances, both assets render", async ({page}) => {
  page.on("pageerror", (e) => console.log("PAGEERROR:", e.message));
  page.on("console", (m) => {
    if (m.type() === "error") console.log("CONSOLE:", m.text());
  });

  // register
  await page.goto("/register");
  await page.getByTestId("reg-name").fill("Flow E2E");
  await page.getByTestId("reg-email").fill(EMAIL);
  await page.getByTestId("reg-password").fill("Str0ngPassword");
  await page.getByTestId("reg-consent").check();
  await page.getByTestId("reg-submit").click();
  await page.waitForURL("**/dashboard", {timeout: 30_000});

  // open flowboard (sidebar link exists)
  await page.goto("/flowboard");
  await page.waitForSelector("[data-testid=flow-builder]");

  // node 1: image step
  await page.selectOption("[data-testid=flow-model-0]", "mock-engine");
  await page.fill("[data-testid=flow-prompt-0]", "neon alley establishing frame, rain-soaked");

  // node 2: video step (fed by node 1's asset)
  await page.selectOption("[data-testid=flow-model-1]", "mock-engine");
  await page.fill("[data-testid=flow-prompt-1]", "push in on the alley as the rain starts");

  await page.getByTestId("flow-run").click();

  // chain detail appears and the worker walks it: first asset, then chain close
  await page.waitForSelector("[data-testid=flow-node-img]", {timeout: 90_000});
  await expect(page.getByTestId("flow-status")).toContainText("succeeded", {timeout: 90_000});
  await expect(page.locator("[data-testid=flow-node-img]")).toHaveCount(2);
});
