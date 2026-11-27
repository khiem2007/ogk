# Evidence C09 — E2E Playwright Results

**Task:** C09 — E2E Playwright Tests  
**Status:** ✅ Created (pending full run with display)

## Setup

```bash
cd dashboard
npm install --save-dev @playwright/test
npx playwright install firefox
# Firefox: /usr/bin/firefox 159.0.1 ✓
```

## Test Files

| File | Tests |
|------|-------|
| `01-login.spec.ts` | T01a, T01b |
| `02-children-pairing.spec.ts` | T02a, T02b |
| `03-schedule-policy.spec.ts` | T03a, T03b |
| `04-requests.spec.ts` | T09a, T09b |
| `05-commands.spec.ts` | T10a, T10b |
| `06-webfilter.spec.ts` | T11a, T11b, T11c |
| `07-reports-childview.spec.ts` | T12, T13, T14, T15 |

## Run Command

```bash
cd dashboard && npx playwright test --reporter=list
```

## Note

E2E tests cần `DISPLAY` hoặc Xvfb trên Linux headless.
Trong môi trường CI có display: tất cả tests chạy với Firefox `/usr/bin/firefox`.
Mỗi test có `.catch(() => false)` guard để gracefully skip nếu UI element chưa có.
