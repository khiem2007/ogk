# OpenGuard Kids — E2E Tests (Playwright)

## Yêu cầu

- Node.js 18+, npm
- Firefox (đã có sẵn tại `/usr/bin/firefox`)
- Dashboard dependencies đã install (`cd dashboard && npm install`)

## Cài đặt Playwright

```bash
cd dashboard
npm install --save-dev @playwright/test
npx playwright install firefox
```

## Chạy E2E Tests

```bash
# Từ thư mục dashboard (Vite server tự khởi động)
npx playwright test

# Với HTML report
npx playwright test --reporter=html
open playwright-report/index.html

# Chạy 1 file cụ thể
npx playwright test e2e/01-login.spec.ts
```

## Cấu hình

Xem: [`dashboard/playwright.config.ts`](../playwright.config.ts)
- baseURL: `http://localhost:5173`
- Browser: Firefox only
- `VITE_API_MODE=demo` (không cần backend)
- Screenshot on failure

## Danh sách Test Cases

| File | Test ID | Mô tả |
|------|---------|--------|
| `01-login.spec.ts` | T01a | Password < 10 chars → error |
| `01-login.spec.ts` | T01b | Valid login → overview |
| `02-children-pairing.spec.ts` | T02a | Enrollment code 8-char |
| `02-children-pairing.spec.ts` | T02b | Expired code → error |
| `03-schedule-policy.spec.ts` | T03a | 7×48 matrix loads |
| `03-schedule-policy.spec.ts` | T03b | 409 conflict handled |
| `04-requests.spec.ts` | T09a | Approve → status approved |
| `04-requests.spec.ts` | T09b | Double-approve → error (atomic) |
| `05-commands.spec.ts` | T10a | LOCK → queued (no premature success) |
| `05-commands.spec.ts` | T10b | Advance → executed confirmed |
| `06-webfilter.spec.ts` | T11a | 200+ domain entries |
| `06-webfilter.spec.ts` | T11b | NT6 protected domain locked |
| `06-webfilter.spec.ts` | T11c | SafeSearch unverified warning |
| `07-reports-childview.spec.ts` | T12 | Child-view hides edit buttons |
| `07-reports-childview.spec.ts` | T13 | Delete-all 2-step confirm |
| `07-reports-childview.spec.ts` | T14 | Mobile 390×844 no overflow |
| `07-reports-childview.spec.ts` | T15 | Tab keyboard navigation |
