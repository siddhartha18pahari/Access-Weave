// Playwright config for AccessWeave's accessibility checks.
// Boots the Django app, then runs axe-core + keyboard tests against it.
const { defineConfig, devices } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./tests/accessibility",
  timeout: 60000,   // axe scans on CI runners can exceed 30s under parallel load
  fullyParallel: true,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://127.0.0.1:8000",
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: {
    command:
      "python manage.py migrate --noinput && python manage.py seed_demo && python manage.py runserver 127.0.0.1:8000 --noreload",
    url: "http://127.0.0.1:8000/",
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
    env: { DJANGO_DEBUG: "1" },
  },
});
