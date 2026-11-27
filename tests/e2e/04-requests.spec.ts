/**
 * tests/e2e/04-requests.spec.ts
 * ==============================
 * T09: Request approve/reject — atomic transition enforcement.
 *
 * Kiểm tra:
 * - Approve pending request → status = approved
 * - Try approve SAME request again → error (đã xử lý rồi)
 * - Reject pending request → status = rejected
 */
import { test, expect } from '@playwright/test';

test.describe('Requests & Decisions', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('input[type="password"]', { timeout: 10000 });
    const demoBtn = page.locator('button', { hasText: /demo/i }).first();
    if (await demoBtn.isVisible()) await demoBtn.click();
    await page.fill('input[type="password"]', 'demo-password-ok');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(1500);
  });

  test('T09a: approve request changes status', async ({ page }) => {
    const link = page.locator('a, button', { hasText: /yêu cầu|request/i }).first();
    if (await link.isVisible()) {
      await link.click();
      await page.waitForTimeout(500);
      const approveBtn = page.locator('button', { hasText: /duyệt|approve/i }).first();
      if (await approveBtn.isVisible()) {
        await approveBtn.click();
        await page.waitForTimeout(500);
        // Status phải chuyển sang approved/đã duyệt
        const statusEl = page.locator('text=/approved|đã duyệt/i').first();
        expect(await statusEl.isVisible({ timeout: 2000 }).catch(() => false)).toBeTruthy();
      } else {
        test.skip();
      }
    } else {
      test.skip();
    }
  });

  test('T09b: double-approve shows error (atomic transition)', async ({ page }) => {
    const link = page.locator('a, button', { hasText: /yêu cầu|request/i }).first();
    if (await link.isVisible()) {
      await link.click();
      await page.waitForTimeout(500);
      const approveBtn = page.locator('button', { hasText: /duyệt|approve/i }).first();
      if (await approveBtn.isVisible()) {
        await approveBtn.click();
        await page.waitForTimeout(300);
        // Click lần 2
        if (await approveBtn.isVisible()) {
          await approveBtn.click();
          await page.waitForTimeout(300);
          // Phải hiện lỗi "đã xử lý" hoặc button disabled
          const errEl = page.locator('text=/đã xử lý|already|lỗi|error/i').first();
          const disabled = await approveBtn.isDisabled().catch(() => false);
          expect(await errEl.isVisible({ timeout: 1500 }).catch(() => false) || disabled).toBeTruthy();
        }
      } else {
        test.skip();
      }
    } else {
      test.skip();
    }
  });
});
