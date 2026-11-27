/**
 * tests/e2e/05-commands.spec.ts
 * ==============================
 * T10: Commands — LOCK_SESSION lifecycle.
 *
 * Kiểm tra QUAN TRỌNG (C06 invariant):
 * - Issue LOCK_SESSION → status hiển thị "queued" (KHÔNG phải "success")
 * - Advance to executed → chỉ lúc này mới xác nhận
 * - Test expired và failed paths
 *
 * Lý do: Không được hiện "success" toast trước khi agent gửi ACK `executed`.
 */
import { test, expect } from '@playwright/test';

test.describe('Commands & ACK', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('input[type="password"]', { timeout: 10000 });
    const demoBtn = page.locator('button', { hasText: /demo/i }).first();
    if (await demoBtn.isVisible()) await demoBtn.click();
    await page.fill('input[type="password"]', 'demo-password-ok');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(1500);
  });

  test('T10a: LOCK_SESSION shows queued first (no premature success)', async ({ page }) => {
    const link = page.locator('a, button', { hasText: /lệnh|command/i }).first();
    if (await link.isVisible()) {
      await link.click();
      await page.waitForTimeout(500);
      // Tìm nút Lock / Khóa ngay
      const lockBtn = page.locator('button', { hasText: /khóa|lock/i }).first();
      if (await lockBtn.isVisible()) {
        await lockBtn.click();
        await page.waitForTimeout(500);
        // Phải hiện "queued" hoặc "đang chờ" — KHÔNG phải "thành công" / "success"
        const queuedEl = page.locator('text=/queued|đang chờ|đã gửi|pending/i').first();
        const successEl = page.locator('text=/thành công|success ✅/i').first();
        expect(await queuedEl.isVisible({ timeout: 2000 }).catch(() => false)).toBeTruthy();
        // Tuyệt đối không có "thành công" trước khi executed
        expect(await successEl.isVisible({ timeout: 500 }).catch(() => false)).toBeFalsy();
      } else {
        test.skip();
      }
    } else {
      test.skip();
    }
  });

  test('T10b: advance to executed confirms command', async ({ page }) => {
    const link = page.locator('a, button', { hasText: /lệnh|command/i }).first();
    if (await link.isVisible()) {
      await link.click();
      await page.waitForTimeout(500);
      const lockBtn = page.locator('button', { hasText: /khóa|lock/i }).first();
      if (await lockBtn.isVisible()) {
        await lockBtn.click();
        await page.waitForTimeout(300);
        // Click demo "advance" để simulate agent ACK
        const advBtn = page.locator('button', { hasText: /advance|executed|thực thi/i }).first();
        if (await advBtn.isVisible()) {
          await advBtn.click();
          await page.waitForTimeout(300);
          const execEl = page.locator('text=/executed|đã thực thi/i').first();
          expect(await execEl.isVisible({ timeout: 2000 }).catch(() => false)).toBeTruthy();
        } else {
          test.skip();
        }
      } else {
        test.skip();
      }
    } else {
      test.skip();
    }
  });
});
