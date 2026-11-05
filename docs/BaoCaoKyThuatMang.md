# Khung Báo cáo kỹ thuật hệ thống và mạng

Đầu ra cuối: `docs/BaoCaoKyThuatMang.pdf`. Bản Markdown này là khung thu thập bằng chứng, chưa phải báo cáo đã hoàn tất.

## M1. Sơ đồ luồng gói tin

- Vẽ browser → Windows stub resolver → OGK DNS proxy `127.0.0.1:53` → chuẩn hóa/tra rule → upstream hoặc block response.
- Tách UDP/TCP, cache hit/miss, timeout và IPv4/IPv6.
- Chèn ảnh Wireshark/tcpdump đã che dữ liệu; ghi filter, môi trường, expected/actual.

## M2. So sánh phương án chặn

So sánh hosts, DNS proxy cục bộ, HTTP(S) proxy và WFP theo: độ chính xác, chặn HTTPS, chi phí hiện thực, khả năng bị vượt, ảnh hưởng hiệu năng. Kết luận vì sao DNS proxy là phương án chính và không tuyên bố thấy URL/path HTTPS.

## M3. Phân tích đường vòng

Tối thiểu 7 ca: DNS thủ công, DoH, DoT, VPN/proxy, truy cập IP, Safe Mode, USB boot, Windows account khác, kill process. Mỗi ca phải có môi trường, bước thử, actual, đối phó hoặc lý do chấp nhận rủi ro.

## M4. Đo hiệu năng

| Phép đo | Baseline | Có agent | Số mẫu | Chỉ số |
|---|---:|---:|---:|---|
| CPU idle/peak | TBD | TBD | ≥30 | mean/p95 |
| RAM idle/peak | TBD | TBD | ≥30 | mean/p95 |
| DNS latency | TBD | TBD | ≥30 mỗi cấu hình | p50/p95 |
| Dashboard → policy applied | N/A | TBD | ≥30 | p50/p95/max |

Ghi công cụ đo, warm-up, cache state, upstream, Windows build và commit.

## M5. Khả năng chịu lỗi

Ba ca bắt buộc: mất mạng, server dừng, agent bị kết thúc. Với mỗi ca ghi expected, actual, dữ liệu có mất/nhân đôi không, trạng thái UI và recovery time.

## M6. Đồng bộ thời gian

Mô tả wall-clock UTC cho lịch, monotonic cho duration, đối chiếu thời gian server ở heartbeat 60 giây, ngưỡng `clock_suspect`, high-water local date và giới hạn qua reboot. Thử lùi đồng hồ 3 giờ: quota không tăng và có event.
