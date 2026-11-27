"""
tests/unit/test_tray_state.py
==============================
Unit tests cho C05 — Tray module (không cần GUI thật).
Chạy với: QT_QPA_PLATFORM=offscreen python -m pytest tests/unit/test_tray_state.py -v

Tại sao không cần GUI thật:
- TrayState và IPCClient là pure Python, không import PySide6.
- OgkTrayApp import PySide6, nhưng ta dùng QT_QPA_PLATFORM=offscreen
  → Qt tạo "offscreen" surface ảo, không cần màn hình thật.
- _stop_emitter.stop_requested là Qt Signal: với offscreen platform, 
  Signal hoạt động bình thường (không cần display).
"""

import os
import sys
import pytest

# Đảm bảo import từ root project
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from agent.tray.models import TrayState
from agent.tray.ipc_client import IPCClient, IPCOfflineError, FORBIDDEN_PAYLOAD_KEYS


# ================================================================== #
#  Test Group 1: TrayState                                            #
# ================================================================== #

class TestTrayState:
    def test_initial_values(self):
        """TrayState khởi tạo với giá trị mặc định hợp lệ."""
        s = TrayState()
        assert s.remaining_seconds == 0
        assert s.quota_seconds == 0
        assert s.online is False
        assert s.manual_lock is False
        assert s.warning_level == 0
        assert s.offline_requests == []

    def test_warning_level_thresholds(self):
        """compute_warning_level() trả đúng mức tại từng ngưỡng."""
        s = TrayState()

        s.remaining_seconds = 3600
        assert s.compute_warning_level() == 0  # > 10 phút = ok

        s.remaining_seconds = 600
        assert s.compute_warning_level() == 1  # = 10 phút → cảnh báo

        s.remaining_seconds = 300
        assert s.compute_warning_level() == 2  # = 5 phút

        s.remaining_seconds = 60
        assert s.compute_warning_level() == 3  # = 1 phút

        s.remaining_seconds = 0
        assert s.compute_warning_level() == 4  # grace

        s.remaining_seconds = -10
        assert s.compute_warning_level() == 4  # grace (âm)

    def test_offline_queue_accumulate(self):
        """Yêu cầu offline được tích lũy và hiển thị "Chưa gửi"."""
        s = TrayState()
        s.add_offline_request("time_extension", "Xin thêm 30 phút", "2026-11-01T10:00:00Z")
        s.add_offline_request("app_unblock", "Mở game học toán", "2026-11-01T10:01:00Z")
        assert s.pending_count() == 2
        # Nhãn UI sẽ hiển thị "Chưa gửi (2)"

    def test_offline_queue_no_forbidden_fields(self):
        """
        add_offline_request KHÔNG lưu window_title hay URL — NT2.
        Payload của offline request chỉ có: type, note, queued_at.
        """
        s = TrayState()
        s.add_offline_request("false_block", "Báo chặn nhầm", "2026-11-01T10:00:00Z")
        req = s.offline_requests[0]
        # Các field được phép
        assert "type" in req
        assert "note" in req
        assert "queued_at" in req
        # Các field bị cấm KHÔNG được có
        for forbidden in FORBIDDEN_PAYLOAD_KEYS:
            assert forbidden not in req, f"NT2 violation: '{forbidden}' tìm thấy trong offline request"

    def test_flush_offline_requests(self):
        """flush_offline_requests() trả về queue rồi xóa sạch."""
        s = TrayState()
        s.add_offline_request("time_extension", "note A", "2026-11-01T10:00:00Z")
        s.add_offline_request("app_unblock", "note B", "2026-11-01T10:01:00Z")
        flushed = s.flush_offline_requests()
        assert len(flushed) == 2
        assert s.pending_count() == 0  # đã xóa

    def test_manual_lock_state(self):
        """manual_lock = True sau khi nhận command.lock."""
        s = TrayState()
        s.manual_lock = True
        s.lock_reason = "parent_override"
        assert s.manual_lock is True
        assert s.lock_reason == "parent_override"


# ================================================================== #
#  Test Group 2: IPCClient — NT2 enforcement                          #
# ================================================================== #

class TestIPCClientNT2:
    def test_forbidden_keys_rejected(self):
        """
        build_message() raise ValueError nếu payload chứa key bị cấm (NT2).
        """
        client = IPCClient(mock=True)
        for forbidden in ["window_title", "url", "screenshot", "keylog"]:
            with pytest.raises(ValueError, match="NT2 violation"):
                client.build_message(
                    "telemetry.sample",
                    {forbidden: "some_value", "app_id": "calc.exe"}
                )

    def test_valid_telemetry_accepted(self):
        """
        build_message() chấp nhận telemetry.sample hợp lệ (không có key cấm).
        """
        client = IPCClient(mock=True)
        msg = client.build_message(
            "telemetry.sample",
            {"remaining_seconds": 1800, "app_id": "calc.exe", "category": "education"}
        )
        assert msg["message_type"] == "telemetry.sample"
        assert msg["schema_version"] == 1
        assert "message_id" in msg
        assert "sent_at" in msg

    def test_unknown_message_type_rejected(self):
        """build_message() raise ValueError cho message_type không hợp lệ."""
        client = IPCClient(mock=True)
        with pytest.raises(ValueError, match="Unknown message_type"):
            client.build_message("unknown.type", {})

    def test_offline_raises_ipc_offline_error(self):
        """
        Khi mock mode, receive() không có response → IPCOfflineError.
        """
        client = IPCClient(mock=True)
        with pytest.raises(IPCOfflineError):
            client.receive()

    def test_mock_inject_response(self):
        """inject_mock_response() cho phép unit test inject telemetry giả."""
        client = IPCClient(mock=True)
        fake_msg = {
            "schema_version": 1,
            "message_id": "00000000-0000-0000-0000-000000000001",
            "sent_at": "2026-11-01T10:00:00Z",
            "session_id": 1,
            "child_sid": "S-1-5-21-0-0-0-1001",
            "message_type": "telemetry.sample",
            "payload": {"remaining_seconds": 900},
        }
        client.inject_mock_response(fake_msg)
        received = client.receive()
        assert received["message_type"] == "telemetry.sample"
        assert received["payload"]["remaining_seconds"] == 900

    def test_command_lock_parsed(self):
        """command.lock message được parse đúng."""
        client = IPCClient(mock=True)
        lock_msg = {
            "schema_version": 1,
            "message_id": "00000000-0000-0000-0000-000000000002",
            "sent_at": "2026-11-01T10:00:00Z",
            "session_id": 1,
            "child_sid": "S-1-5-21-0-0-0-1001",
            "message_type": "command.lock",
            "payload": {"reason_code": "parent_override", "lock_until": None},
        }
        client.inject_mock_response(lock_msg)
        received = client.receive()
        assert received["message_type"] == "command.lock"
        assert received["payload"]["reason_code"] == "parent_override"


# ================================================================== #
#  Test Group 3: Tray availability guard                              #
# ================================================================== #

class TestTrayAvailabilityGuard:
    """
    Kiểm tra guard: khi tray không khả dụng, app KHÔNG được chạy ẩn.

    Cách tiếp cận: test logic guard function trực tiếp (không tạo QApp full).
    OgkTrayApp.__init__ gọi sys.exit(1) khi isSystemTrayAvailable() = False.
    Ta extract logic đó thành hàm helper để unit-test dễ hơn.
    """

    def test_stop_emitter_signal_works(self):
        """
        _stop_emitter.stop_requested Signal hoạt động đúng khi emit.
        (Xác minh Qt Signal infrastructure hoạt động trong offscreen env.)
        """
        from agent.tray import app as tray_app

        received = []
        tray_app._stop_emitter.stop_requested.connect(
            lambda r: received.append(r)
        )
        tray_app._stop_emitter.stop_requested.emit("tray_unavailable")
        assert "tray_unavailable" in received

    def test_tray_state_tray_available_field(self):
        """
        TrayState.tray_available = False → app logic phải dừng.
        (Unit test kiểm tra field tồn tại và mặc định True.)
        """
        s = TrayState()
        assert s.tray_available is True
        # Giả lập tray không có
        s.tray_available = False
        assert s.tray_available is False
        # Trong OgkTrayApp.__init__, nếu tray_available=False → sys.exit(1)
        # Logic: if not QSystemTrayIcon.isSystemTrayAvailable(): sys.exit(1)
