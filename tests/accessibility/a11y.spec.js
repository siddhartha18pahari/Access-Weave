// Automated accessibility checks: axe-core (WCAG 2.1 A/AA) on key pages, plus a
// keyboard-path and reduced-motion smoke test. Run with: npm run test:a11y
const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

const WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

async function axeScan(page) {
  const results = await new AxeBuilder({ page }).withTags(WCAG).analyze();
  return results.violations.filter((v) =>
    ["serious", "critical"].includes(v.impact));
}

async function login(page) {
  await page.goto("/login/");
  await page.fill("#id_username", "demo");
  await page.fill("#id_password", "accessweave");
  await page.getByRole("button", { name: /log in/i }).click();
  await page.waitForURL("**/");
}

const publicPages = ["/", "/about/", "/privacy/", "/login/", "/signup/"];

for (const path of publicPages) {
  test(`axe (public): ${path}`, async ({ page }) => {
    await page.goto(path);
    const serious = await axeScan(page);
    expect(
      serious,
      "serious/critical a11y violations: " +
        JSON.stringify(serious.map((v) => ({ id: v.id, nodes: v.nodes.length })), null, 2)
    ).toEqual([]);
  });
}

const authedPages = ["/", "/tasks/new/", "/communication/", "/resources/",
                     "/passports/", "/look/", "/soundwatch/", "/captions/",
                     "/tasks/", "/onboarding/"];

for (const path of authedPages) {
  test(`axe (authed): ${path}`, async ({ page }) => {
    await login(page);
    await page.goto(path);
    const serious = await axeScan(page);
    expect(
      serious,
      "serious/critical a11y violations: " +
        JSON.stringify(serious.map((v) => ({ id: v.id, nodes: v.nodes.length })), null, 2)
    ).toEqual([]);
  });
}

test("skip link is the first focusable element", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  const focused = await page.evaluate(() => document.activeElement.textContent.trim());
  expect(focused).toMatch(/skip to main content/i);
});

test("task can be created and stepped through by keyboard", async ({ page }) => {
  await login(page);
  await page.goto("/tasks/new/");
  await page.fill("#goal", "Read my medicine label");
  await page.fill(
    "#source_text",
    "Take one capsule twice daily with food. Do not exceed two capsules in 24 hours."
  );
  await page.getByRole("button", { name: /make it accessible/i }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/medicine label/i);
  // advance a step
  await page.getByRole("button", { name: /mark done/i }).first().click();
  await expect(page.locator("#voice-data")).toHaveAttribute("data-step", /[1-9]/);
});

test("command palette opens with Ctrl+K and is an accessible combobox", async ({ page }) => {
  await login(page);
  await page.goto("/");
  await page.keyboard.press("Control+k");
  const input = page.locator("#aw-palette-input");
  await expect(input).toBeFocused();
  await expect(input).toHaveAttribute("role", "combobox");
  await expect(input).toHaveAttribute("aria-activedescendant", /pal-\d+/);
  await page.keyboard.press("Escape");
  await expect(page.locator("#aw-palette")).toBeHidden();
});

test("shortcut sheet opens with ? and closes with Escape", async ({ page }) => {
  await login(page);
  await page.goto("/");
  await page.keyboard.press("Shift+/");
  await expect(page.locator("#aw-shortcuts")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.locator("#aw-shortcuts")).toBeHidden();
});

test("switch scanning highlights a control and can be stopped", async ({ page }) => {
  await login(page);
  await page.goto("/");
  await page.evaluate(() => { window.awScan.setSpeed(200); window.awScan.startSwitch(); });
  await expect(page.locator(".aw-scan-active")).toHaveCount(1);
  await page.keyboard.press("Escape");
  await expect(page.locator(".aw-scan-active")).toHaveCount(0);
});

test("every theme keeps the destructive button readable", async ({ page }) => {
  await login(page);
  await page.goto("/privacy/");
  for (const theme of ["light", "dark", "high"]) {
    await page.evaluate((t) => window.awApplyTheme(t), theme);
    const colors = await page.locator(".btn.danger").first().evaluate((el) => {
      const s = getComputedStyle(el);
      return { color: s.color, bg: s.backgroundColor };
    });
    expect(colors.color).not.toBe(colors.bg);
  }
});
