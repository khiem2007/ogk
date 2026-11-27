# Checklist Windows — tất cả chưa chạy

Ghi mỗi ca: commit, Windows build, account/SID, adapter, steps, expected, actual,
pass/fail/blocked, link evidence. Chỉ dùng VM lab và app thử nghiệm không chứa dữ liệu cần lưu.

- [ ] Service Session 0, helper trong SID/session trẻ; foreground/idle đúng phiên.
- [ ] Telemetry không chứa window title/URL/nội dung; Tray luôn hiện, không icon thì agent dừng.
- [ ] IPC từ SID khác, stale timestamp, oversized/invalid payload bị từ chối.
- [ ] Foreground đổi app; idle/lock/sleep không bị cộng nhầm; restart khôi phục quota.
- [ ] Kill Tray: degraded, helper restart có backoff; báo thời gian ước lượng và thiếu app telemetry.
- [ ] Khóa qua helper; fallback disconnect được ghi đúng trạng thái; manual lock còn sau unlock.
- [ ] Không chặn process hệ thống hoặc phiên phụ huynh.
- [ ] App test đổi tên vẫn nhận diện bằng SHA-256; block hiện lý do và người đặt luật.
- [ ] Mất mạng 10 phút: policy vẫn áp dụng; reconnect dedup event/grant/command.
- [ ] Lệnh hết hạn và replay/crash quanh ACK không tạo tác động muộn hoặc kéo dài miễn hạn.
- [ ] DNS UDP/TCP, domain boundary, IPv4/IPv6, cache và upstream timeout.
- [ ] SafeSearch pass bằng `nslookup` và browser; protected allowlist trường học/111/cứu hộ không bị block.
- [ ] Port 53 bận/proxy lỗi: không đổi adapter; rollback hoạt động.
- [ ] Cài/gỡ khôi phục chính xác DHCP/static DNS ban đầu; không tự forward loopback.
- [ ] VM sạch: install → enroll → restart → demo → uninstall; policy ≤60s, command <5s, khóa lịch ≤5s, usage ±30s/giờ.
- [ ] M4: CPU/RAM, DNS p50/p95 và policy latency, mỗi phép đo ≥30 mẫu.
- [ ] M5: mất mạng, server dừng, agent bị kill; ghi expected/actual/recovery time.
- [ ] M6: lùi giờ 3h không tăng quota, có clock event và đối chiếu server ở heartbeat.

Các ca T01–T23 đầy đủ xem PROJECT_BRIEF mục 10. Mock không thay bằng chứng Windows/network.
