"""
agent/tray/models.py
====================
TrayState — trạng thái nội bộ của Tray app.

Giải thích:
- Đây là "nguồn sự thật" (single source of truth) cho giao diện tray.
- Mỗi khi nhận được telemetry.sample từ agent core, ta cập nhật TrayState
  rồi repaint menu và badge.
- `warning_level`: 0=bình thường, 1=≤10 phút, 2=≤5 phút, 3=≤1 phút, 4=grace(60s)
- `offline_requests`: hàng đợi khi agent core không kết nối được server —
  mỗi phần tử là dict {"type": ..., "note": ..., "queued_at": ...}
  → hiển thị nhãn "Chưa gửi (N)" trên UI.
- QUAN TRỌNG: TrayState KHÔNG lưu window_title hay URL — đây là ràng buộc NT2
  (không thu thập nội dung duyệt web / tiêu đề cửa sổ).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class TrayState:
    # Thời gian còn lại (giây) trong phiên hôm nay
    remaining_seconds: int = 0

    # Hạn mức (giây) toàn ngày
    quota_seconds: int = 0

    # Kết nối server: True = online, False = offline
    online: bool = False

    # Khóa thủ công từ phụ huynh (command.lock)
    manual_lock: bool = False

    # Mức cảnh báo: 0=ok, 1=10phút, 2=5phút, 3=1phút, 4=grace60s
    warning_level: int = 0

    # Hàng đợi yêu cầu offline (chưa gửi được lên server)
    offline_requests: List[Dict[str, Any]] = field(default_factory=list)

    # Lý do khóa (từ ReasonCode) — hiển thị dialog "Phụ huynh đặt"
    lock_reason: str = ""

    # Icon tray có khả dụng không (QSystemTrayIcon.isSystemTrayAvailable())
    tray_available: bool = True

    def compute_warning_level(self) -> int:
        """
        Tính mức cảnh báo dựa trên remaining_seconds.
        Grace period (4) = 60 giây cuối sau khi quota hết.
        """
        s = self.remaining_seconds
        if s <= 0:
            return 4   # grace 60s — agent bắt đầu đếm ngược 60s rồi khóa
        elif s <= 60:
            return 3   # ≤ 1 phút
        elif s <= 300:
            return 2   # ≤ 5 phút
        elif s <= 600:
            return 1   # ≤ 10 phút
        return 0

    def add_offline_request(self, req_type: str, note: str, queued_at: str) -> None:
        """
        Thêm yêu cầu vào hàng đợi offline.
        req_type: "time_extension" | "app_unblock" | "false_block"
        """
        # NT2: không lưu window_title hay URL
        self.offline_requests.append({
            "type": req_type,
            "note": note,
            "queued_at": queued_at,
        })

    def flush_offline_requests(self) -> List[Dict[str, Any]]:
        """
        Trả về toàn bộ hàng đợi rồi xóa — gọi khi reconnect.
        """
        pending = list(self.offline_requests)
        self.offline_requests.clear()
        return pending

    def pending_count(self) -> int:
        return len(self.offline_requests)
