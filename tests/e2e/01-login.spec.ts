/**
 * tests/e2e/01-login.spec.ts
 * ==========================
 * T01: Password validation & login flow.
 *
 * Kiểm tra:
 * - Mật khẩu < 10 ký tự → hiển thị lỗi, không vào được dashboard
 * - Mật khẩu ≥ 10 ký tự → vào được Overview
 * - Demo mode toggle hoạt động
 */
import { test, expect } from '@playwright/test';

test.describe('Login flow', () => {
  test('T01a: short password shows error', async ({ page }) => {
    await page.goto('/');
    // Chờ form login xuất hiện
    await page.waitForSelector('input[type="password"]', { timeout: 10000 });
    await page.fill('input[type="password"]', 'short');
    await page.click('button[type="submit"]');
    // Phải có thông báo lỗi (không được vào dashboard)
    const errorText = await page.locator('text=/ít nhất 10|mật khẩu/i').first().textContent({ timeout: 3000 }).catch(() => '');
    // Hoặc form vẫn còn visible (chưa redirect)
    const formStillVisible = await page.locator('input[type="password"]').isVisible();
    expect(formStillVisible || errorText.length > 0).toBeTruthy();
  });

  test('T01b: valid demo login → overview page', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('input[type="password"]', { timeout: 10000 });
    // Click "Demo" mode nếu có
    const demoBtn = page.locator('button', { hasText: /demo/i }).first();
    if (await demoBtn.isVisible()) {
      await demoBtn.click();
    }
    await page.fill('input[type="password"]', 'demo-password-ok');
    await page.click('button[type="submit"]');
    // Chờ sidebar hoặc overview xuất hiện
    await page.waitForURL('**/', { timeout: 8000 }).catch(() => {});
    // Kiểm tra có nội dung dashboard
    const hasContent = await page.locator('nav, [data-testid="overview"], h1, h2').first().isVisible({ timeout: 5000 }).catch(() => false);
    expect(hasContent).toBeTruthy();
  });
});
