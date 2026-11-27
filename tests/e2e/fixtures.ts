/**
 * tests/e2e/fixtures.ts
 * =====================
 * Shared Playwright test fixtures cho OGK E2E suite.
 *
 * DemoPage fixture:
 * - Mở app ở chế độ Demo (VITE_API_MODE=demo)
 * - Đăng nhập tự động với tài khoản demo
 * - Trả về `page` đã authenticated sẵn
 *
 * Cách dùng trong spec:
 *   import { test, expect } from './fixtures';
 *   test('my test', async ({ authedPage }) => { ... });
 */

import { test as base, expect, Page } from '@playwright/test';

export { expect };

type OgkFixtures = {
  /** Page đã đăng nhập sẵn vào demo account */
  authedPage: Page;
};

export const test = base.extend<OgkFixtures>({
  authedPage: async ({ page }, use) => {
    // Vào trang login
    await page.goto('/');

    // Điền thông tin demo
    const passwordInput = page.locator('input[type="password"]');
    if (await passwordInput.isVisible()) {
      await passwordInput.fill('demo-password-ok');
      await page.locator('button[type="submit"]').click();
      // Chờ sidebar xuất hiện (đã login)
      await page.waitForSelector('nav', { timeout: 5000 }).catch(() => {});
    }

    await use(page);
  },
});
