import {expect, test} from "@playwright/test";

// D1.5: templates deep-link into studios (?template=slug) and prefill the form.
const EMAIL = `tpl-${Date.now()}@example.com`;
const TOKYO_PROMPT = "full-height fashion look in a rainy neon alley, reflections on asphalt";

test("template gallery deep-link prefills the image studio honestly", async ({page}) => {
  page.on("pageerror", (e) => console.log("PAGEERROR:", e.message));
  page.on("console", (m) => {
    if (m.type() === "error") console.log("CONSOLE:", m.text());
  });

  await page.goto("/register");
  await page.getByTestId("reg-name").fill("Template E2E");
  await page.getByTestId("reg-email").fill(EMAIL);
  await page.getByTestId("reg-password").fill("Str0ngPassword");
  await page.getByTestId("reg-consent").check();
  await page.getByTestId("reg-submit").click();
  await page.waitForURL("**/dashboard", {timeout: 30_000});

  await page.goto("/create/image?template=tokyo-street-fashion");
  await page.waitForSelector("[data-testid=prompt]");
  await expect(page.getByTestId("prompt")).toHaveValue(TOKYO_PROMPT);
  await expect(page.getByTestId("template-applied")).toContainText("Tokyo Street Fashion");
  // the template's aspect choice (3:4) is preselected — the button carries the active style
  await expect(page.locator("[data-testid=aspect-3\\:4]")).toHaveClass(/border-byz-400/);
});
