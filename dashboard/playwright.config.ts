import { defineConfig, devices } from '@playwright/test';

/**
 * playwright.config.ts
 * ====================
 * Cấu hình Playwright cho E2E tests của OGK Dashboard.
 *
 * Chỉ dùng Firefox (đã có sẵn trên hệ thống tại /usr/bin/firefox).
 * Vite dev server được tự động khởi động trước khi chạy tests.
 *
 * Chạy: cd dashboard && npx playwright test
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,  // Chạy tuần tự để tránh xung đột demo state
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [['html', { outputFolder: 'playwright-report' }], ['list']],

  use: {
    baseURL: 'http://localhost:5173',
    // Demo mode: không cần server backend thật
    // Dashboard tự động dùng DemoOgkClient khi VITE_API_MODE=demo
    screenshot: 'only-on-failure',
    video: 'off',
    headless: true,
  },

  projects: [
    {
      name: 'firefox',
      use: {
        ...devices['Desktop Firefox'],
        channel: undefined,
        // Dùng Firefox system nếu Playwright chưa download binary
        executablePath: process.env.PLAYWRIGHT_FIREFOX_PATH || undefined,
      },
    },
  ],

  // Tự khởi động Vite dev server trước tests
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
    env: {
      VITE_API_MODE: 'demo',
    },
  },
});
