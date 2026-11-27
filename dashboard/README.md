# OpenGuard Kids — Dashboard

## Giới thiệu

Dashboard React (TypeScript + Vite) dành cho phụ huynh quản lý thời gian sử dụng máy tính của trẻ.

## Cài đặt

```bash
cd dashboard
npm install
```

## Chạy development

```bash
npm run dev
# Truy cập: http://localhost:5173
# Demo mode: không cần backend — dùng DemoOgkClient tích hợp sẵn
```

## Biến môi trường

| Variable | Mô tả | Mặc định |
|----------|--------|----------|
| `VITE_API_MODE` | `demo` (không cần server) hoặc `api` (kết nối thật) | `demo` |

## Chạy Unit Tests (Vitest)

```bash
npm test
# Dự kiến: 9+ tests PASS
```

## Build Production

```bash
npm run build
# Output: dist/ (~282 kB JS, ~87 kB gzip)
```

## Chạy E2E Tests (Playwright)

```bash
# Từ thư mục gốc dự án
cd dashboard && npx playwright test
# Hoặc với HTML report:
npx playwright test --reporter=html
```

## Cấu trúc thư mục

```
dashboard/src/
├── api/client.ts          # HttpOgkClient + DemoOgkClient
├── components/            # StatusBadges, shared UI
├── data/
│   ├── demoFixtures.ts    # Demo state (cô lập, không lẫn production)
│   └── domainCatalog.ts   # 200+ domain entries, NT6 protected list
├── pages/                 # 8 trang chính (Login, Overview, Apps, ...)
├── styles/app.css         # Sage green design system
├── types/ogk.ts           # TypeScript types từ contracts/
└── utils/validation.ts    # Schedule/domain validation
```

## Các trang chính

| Trang | Chức năng |
|-------|-----------|
| Login | Auth với ≥10 ký tự, Demo/API toggle |
| Overview | Metric cards, weekly bar chart |
| Children & Devices | Child profiles, enrollment code 8-char/10-min |
| Apps & Schedule | Ma trận 7×48, quota, app rules, policy version |
| Requests | Duyệt/từ chối yêu cầu (atomic transition) |
| Commands | LOCK_SESSION, exemption (5-state, không "success" trước ACK) |
| Reports | Daily/weekly chart, audit log, child-view |
| Web Filter | 6 category rules, SafeSearch, NT6 protected allowlist |
| Profiles | 3 age-band templates, NT1 transparency |
