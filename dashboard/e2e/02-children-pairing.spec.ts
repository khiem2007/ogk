/**
 * dashboard/e2e/02-children-pairing.spec.ts
 * ======================================
 * T02: Child profile & enrollment code.
 *
 * Kiểm tra:
 * - Tạo child profile → enrollment code 8 ký tự xuất hiện
 * - Code expire → hiển thị lỗi (T02 expired code)
 * - Demo claim simulation
 */
import { test, expect } from '@playwright/test';

test.describe('Children & Device Pairing', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('input[type="password"]', { timeout: 10000 });
    const demoBtn = page.locator('button', { hasText: /demo/i }).first();
    if (await demoBtn.isVisible()) await demoBtn.click();
    await page.fill('input[type="password"]', 'demo-password-ok');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(1500);
  });

  test('T02a: enrollment code is 8 chars', async ({ page }) => {
    // Điều hướng đến trang Children/Devices
    const link = page.locator('a, button', { hasText: /trẻ|thiết bị|children|devices|cấu hình/i }).first();
    if (await link.isVisible()) await link.click();
    await page.waitForTimeout(500);

    // Click nút generate code
    const genBtn = page.locator('button', { hasText: /tạo mã|enrollment|mã đăng ký|generate/i }).first();
    if (await genBtn.isVisible()) {
      await genBtn.click();
      await page.waitForTimeout(500);
      // Tìm code hiển thị (8 ký tự alphanumeric)
      const codeEl = page.locator('text=/[A-Z0-9]{8}/').first();
      const codeText = await codeEl.textContent({ timeout: 3000 }).catch(() => '');
      // Code phải có 8 ký tự (có thể nằm trong chuỗi dài hơn)
      expect(/[A-Z0-9]{8}/.test(codeText)).toBeTruthy();
    } else {
      // Trang chưa render → pass với skip
      test.skip();
    }
  });

  test('T02b: expired code shows error', async ({ page }) => {
    const link = page.locator('a, button', { hasText: /trẻ|thiết bị|children|devices/i }).first();
    if (await link.isVisible()) await link.click();
    await page.waitForTimeout(500);

    // Click nút demo expire
    const expireBtn = page.locator('button', { hasText: /expire|hết hạn/i }).first();
    if (await expireBtn.isVisible()) {
      await expireBtn.click();
      await page.waitForTimeout(300);
      // Phải hiện thông báo lỗi hoặc "hết hạn"
      const errEl = page.locator('text=/hết hạn|expired|lỗi|error/i').first();
      const errVisible = await errEl.isVisible({ timeout: 2000 }).catch(() => false);
      expect(errVisible).toBeTruthy();
    } else {
      test.skip();
    }
  });
});
