import {expect, test} from "@playwright/test";

// D1.5: templates deep-link into studios (?template=slug) and prefill the form.
const TOKYO_PROMPT = "full-height fashion look in a rainy neon alley, reflections on asphalt";

test("template gallery deep-link prefills the image studio honestly", async ({page}) => {
  page.on("pageerror", (e) => console.log("PAGEERROR:", e.message));
  page.on("console", (m) => {
    if (m.type() === "error") console.log("CONSOLE:", m.text());
  });

  // open the studio first (mints the guest session), then deep-link into a template
  await page.goto("/dashboard");
  await page.waitForSelector("[data-testid=dashboard-title]", {timeout: 30_000});
  await page.goto("/create/image?template=tokyo-street-fashion");
  await page.waitForSelector("[data-testid=prompt]");
  await expect(page.getByTestId("prompt")).toHaveValue(TOKYO_PROMPT);
  await expect(page.getByTestId("template-applied")).toContainText("Tokyo Street Fashion");
  // the template's aspect choice (3:4) is preselected — the button carries the active style
  await expect(page.locator("[data-testid=aspect-3\\:4]")).toHaveClass(/border-byz-400/);
});
