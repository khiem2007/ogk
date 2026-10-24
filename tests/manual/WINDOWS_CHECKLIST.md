# Checklist Windows — tất cả chưa chạy

Ghi mỗi ca: commit, Windows build, account/SID, adapter, steps, expected, actual,
pass/fail/blocked, link evidence. Chỉ dùng VM lab và app thử nghiệm không chứa dữ liệu cần lưu.

- [ ] Service Session 0, helper trong SID/session trẻ; foreground/idle đúng phiên.
- [ ] IPC từ SID khác, stale timestamp, oversized/invalid payload bị từ chối.
- [ ] Foreground đổi app; idle/lock/sleep không bị cộng nhầm; restart khôi phục quota.
- [ ] Kill Tray: degraded, helper restart có backoff; báo thời gian ước lượng và thiếu app telemetry.
- [ ] Khóa qua helper; fallback disconnect được ghi đúng trạng thái; manual lock còn sau unlock.
- [ ] Không chặn process hệ thống hoặc phiên phụ huynh.
- [ ] Mất mạng 10 phút: policy vẫn áp dụng; reconnect dedup event/grant/command.
- [ ] Lệnh hết hạn và replay/crash quanh ACK không tạo tác động muộn hoặc kéo dài miễn hạn.
- [ ] DNS UDP/TCP, domain boundary, IPv4/IPv6, cache và upstream timeout.
- [ ] Port 53 bận/proxy lỗi: không đổi adapter; rollback hoạt động.
- [ ] Cài/gỡ khôi phục chính xác DHCP/static DNS ban đầu; không tự forward loopback.
- [ ] VM sạch: install → enroll → restart → demo → uninstall; đo 70s/10s/3s mục tiêu lab.

Các ca T01–T18 đầy đủ xem PROJECT_BRIEF mục 10. Mock không thay bằng chứng Windows.
