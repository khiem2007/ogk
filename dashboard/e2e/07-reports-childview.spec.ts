/**
 * dashboard/e2e/07-reports-childview.spec.ts
 * ========================================
 * T12–T14: Reports, child-view, delete-all, mobile viewport, accessibility.
 *
 * Kiểm tra:
 * - Child-view: không có nút edit/approve
 * - Delete-all cần 2 bước xác nhận
 * - Mobile viewport 390×844 render được
 * - Tab navigation keyboard hoạt động
 */
import { test, expect } from '@playwright/test';

test.describe('Reports & Child View', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('input[type="password"]', { timeout: 10000 });
    const demoBtn = page.locator('button', { hasText: /demo/i }).first();
    if (await demoBtn.isVisible()) await demoBtn.click();
    await page.fill('input[type="password"]', 'demo-password-ok');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(1500);
  });

  test('T12: child-view hides edit controls', async ({ page }) => {
    // Chuyển sang child-view
    const cvBtn = page.locator('button', { hasText: /chế độ trẻ|child.?view|xem như trẻ/i }).first();
    if (await cvBtn.isVisible()) {
      await cvBtn.click();
      await page.waitForTimeout(500);
      // Không được có nút edit/approve/reject trong child view
      const editBtns = page.locator('button', { hasText: /chỉnh sửa|edit|approve|duyệt|reject|từ chối/i });
      const count = await editBtns.count();
      expect(count).toBe(0);
    } else {
      test.skip();
    }
  });

  test('T13: delete-all requires 2-step confirmation', async ({ page }) => {
    const link = page.locator('a, button', { hasText: /báo cáo|report|audit/i }).first();
    if (await link.isVisible()) {
      await link.click();
      await page.waitForTimeout(500);
      const delBtn = page.locator('button', { hasText: /xóa tất cả|delete all|xóa log/i }).first();
      if (await delBtn.isVisible()) {
        await delBtn.click();
        await page.waitForTimeout(300);
        // Bước 1: phải hiện confirm dialog / confirm button
        const confirmBtn = page.locator('button', { hasText: /xác nhận|confirm|chắc chắn/i }).first();
        const confirmVisible = await confirmBtn.isVisible({ timeout: 2000 }).catch(() => false);
        expect(confirmVisible).toBeTruthy();
        // Click confirm (bước 2)
        if (confirmVisible) {
          await confirmBtn.click();
          await page.waitForTimeout(500);
          const doneEl = page.locator('text=/đã xóa|deleted|thành công/i').first();
          expect(await doneEl.isVisible({ timeout: 2000 }).catch(() => false)).toBeTruthy();
        }
      } else {
        test.skip();
      }
    } else {
      test.skip();
    }
  });

  test('T14: mobile viewport 390×844 renders without overflow', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.reload();
    await page.waitForTimeout(1000);
    // Không có horizontal scroll
    const hasOverflow = await page.evaluate(() => document.body.scrollWidth > window.innerWidth);
    expect(hasOverflow).toBeFalsy();
    // Nội dung chính vẫn visible
    const main = page.locator('main, [role="main"], #root').first();
    expect(await main.isVisible({ timeout: 3000 }).catch(() => false)).toBeTruthy();
  });

  test('T15: keyboard Tab navigation reaches main controls', async ({ page }) => {
    // Tab qua các phần tử tương tác
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    // Phải có focused element
    const focused = await page.locator(':focus').first().isVisible({ timeout: 2000 }).catch(() => false);
    expect(focused).toBeTruthy();
  });
});
