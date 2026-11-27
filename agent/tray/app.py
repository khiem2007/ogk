"""
agent/tray/app.py
=================
OgkTrayApp — ứng dụng PySide6 chạy trong session của trẻ.

## Giải thích kiến trúc tổng thể

```
┌──────────────────────────────────────────┐
│  OgkTrayApp (QApplication)               │
│  ├── QSystemTrayIcon (icon + menu)       │
│  │    ├── QMenu: remaining / status      │
│  │    └── Actions: Xin thêm giờ / Thoát │
│  ├── QTimer (1s) → cập nhật countdown   │
│  ├── BlockingDialog (khi hết giờ / lock) │
│  └── RequestDialog (form xin thêm giờ)  │
└──────────────────────────────────────────┘
         ↕ IPC (Unix socket / mock)
┌──────────────────────────────────────────┐
│  agent core (tiến trình riêng, hệ thống) │
└──────────────────────────────────────────┘
```

## Quy tắc bắt buộc (từ ARCHITECTURE.md)
- Nếu `QSystemTrayIcon.isSystemTrayAvailable()` = False → agent PHẢI dừng,
  KHÔNG được chạy ẩn.
- Khởi động luôn hiển thị notification: "OpenGuard Kids đang chạy công khai"
- NT2: không log / hiển thị window_title, URL, screenshot.
- NT1: tab "Phần mềm này làm gì?" dùng ngôn ngữ cấp 1 (grade-1 Vietnamese).
"""

from __future__ import annotations
import sys
from datetime import datetime, timezone
from typing import Optional

from PySide6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QDialog,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QTabWidget, QWidget, QMessageBox,
)
from PySide6.QtGui import QIcon, QPixmap, QColor
from PySide6.QtCore import Qt, QTimer, Signal, QObject

from agent.tray.models import TrayState
from agent.tray.ipc_client import IPCClient, IPCOfflineError


# ------------------------------------------------------------------ #
#  Helpers                                                             #
# ------------------------------------------------------------------ #

def _fmt_seconds(secs: int) -> str:
    """Chuyển giây → "HH:MM:SS" (hoặc "00:00" nếu âm)."""
    if secs <= 0:
        return "00:00:00"
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _make_icon(color: str = "#4CAF50") -> QIcon:
    """
    Tạo icon tray đơn giản bằng QPixmap (hình tròn màu).
    Màu xanh = bình thường, vàng = cảnh báo, đỏ = khóa.
    Không cần file PNG bên ngoài — phù hợp môi trường headless/CI.
    """
    px = QPixmap(32, 32)
    px.fill(QColor(color))
    return QIcon(px)


# ------------------------------------------------------------------ #
#  Stop signal emitter (dùng trong unit tests)                         #
# ------------------------------------------------------------------ #

class _StopSignalEmitter(QObject):
    stop_requested = Signal(str)  # reason string


_stop_emitter = _StopSignalEmitter()


# ------------------------------------------------------------------ #
#  RequestDialog — form xin thêm giờ / mở app / báo chặn nhầm        #
# ------------------------------------------------------------------ #

class RequestDialog(QDialog):
    """
    Cửa sổ popup để trẻ gửi yêu cầu lên phụ huynh.

    Có 3 loại yêu cầu:
    - time_extension: Xin thêm giờ
    - app_unblock: Xin mở ứng dụng
    - false_block: Báo chặn nhầm

    NT2: form CHỈ cho nhập ghi chú tự do (note), KHÔNG có trường URL/app path.
    """

    def __init__(self, state: TrayState, ipc: IPCClient, parent=None):
        super().__init__(parent)
        self.state = state
        self.ipc = ipc
        self.setWindowTitle("Gửi yêu cầu cho bố/mẹ")
        self.setMinimumWidth(360)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Nút chọn loại yêu cầu
        self._req_type = "time_extension"
        btn_row = QHBoxLayout()
        for label, rtype in [
            ("⏱ Xin thêm giờ", "time_extension"),
            ("📱 Xin mở app", "app_unblock"),
            ("🚫 Báo chặn nhầm", "false_block"),
        ]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, t=rtype: self._select_type(t))
            btn_row.addWidget(btn)
            if rtype == "time_extension":
                btn.setChecked(True)
        layout.addLayout(btn_row)

        # Ghi chú (note)
        layout.addWidget(QLabel("Ghi chú cho bố/mẹ:"))
        self._note = QTextEdit()
        self._note.setMaximumHeight(80)
        self._note.setPlaceholderText("Ví dụ: Con cần thêm 30 phút để làm bài tập nhóm")
        layout.addWidget(self._note)

        # Trạng thái offline queue
        self._status_lbl = QLabel("")
        layout.addWidget(self._status_lbl)

        # Nút gửi
        send_btn = QPushButton("Gửi yêu cầu")
        send_btn.clicked.connect(self._submit)
        layout.addWidget(send_btn)

    def _select_type(self, req_type: str):
        self._req_type = req_type

    def _submit(self):
        note = self._note.toPlainText().strip()
        queued_at = datetime.now(timezone.utc).isoformat()

        payload = {
            "request_type": self._req_type,
            "note": note,
        }

        try:
            self.ipc.send("request.submit", payload)
            self._status_lbl.setText("✅ Đã gửi. Chờ bố/mẹ duyệt.")
        except IPCOfflineError:
            # Offline → enqueue
            self.state.add_offline_request(self._req_type, note, queued_at)
            n = self.state.pending_count()
            self._status_lbl.setText(
                f"📶 Chưa gửi ({n}) — sẽ gửi khi kết nối lại"
            )


# ------------------------------------------------------------------ #
#  BlockingDialog — hiển thị khi hết giờ hoặc bị khóa                 #
# ------------------------------------------------------------------ #

class BlockingDialog(QDialog):
    """
    Dialog toàn màn hình (không có nút đóng) hiển thị khi:
    - Hết quota (remaining_seconds ≤ 0 sau grace 60s)
    - Lệnh LOCK_SESSION từ phụ huynh (manual_lock = True)

    NT1: Dùng ngôn ngữ đơn giản cấp 1 cho trẻ.
    Không có cách đóng từ phía trẻ — chỉ phụ huynh mở khóa qua dashboard.
    """

    def __init__(self, reason: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("OpenGuard Kids")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        # Không cho đóng bằng X
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        self.setMinimumSize(400, 300)
        self._build_ui(reason)

    def _build_ui(self, reason: str):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel("🔒")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 64px;")
        layout.addWidget(icon_lbl)

        msg = QLabel("Hôm nay em đã dùng máy tính đủ rồi.\n\nBố/mẹ sẽ mở khóa cho em.")
        if reason:
            msg.setText(f"Bố/mẹ đã đặt: {reason}\n\nHãy hỏi bố/mẹ để mở khóa nhé.")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setWordWrap(True)
        msg.setStyleSheet("font-size: 18px;")
        layout.addWidget(msg)


# ------------------------------------------------------------------ #
#  InfoTabsDialog — "Phần mềm này làm gì?" + "Hôm nay em dùng gì"   #
# ------------------------------------------------------------------ #

class InfoTabsDialog(QDialog):
    """
    NT1: Giải thích minh bạch bằng ngôn ngữ cấp 1 cho trẻ.
    Tab 1: Phần mềm này làm gì?
    Tab 2: Hôm nay em đã dùng gì (child-view usage)
    """

    def __init__(self, state: TrayState, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OpenGuard Kids — Thông tin")
        self.setMinimumSize(480, 360)
        tabs = QTabWidget()

        # Tab 1 — NT1 transparency
        tab1 = QWidget()
        t1_layout = QVBoxLayout(tab1)
        txt = QLabel(
            "<h3>Phần mềm này làm gì?</h3>"
            "<p>Phần mềm <b>OpenGuard Kids</b> giúp bố/mẹ cài thời gian dùng máy tính cho em.</p>"
            "<ul>"
            "<li>Phần mềm đếm thời gian em dùng máy.</li>"
            "<li>Khi hết giờ, máy tính sẽ tự khóa lại.</li>"
            "<li>Em có thể xin bố/mẹ thêm giờ bằng nút <b>Xin thêm giờ</b>.</li>"
            "<li>Phần mềm <b>không xem</b> màn hình, không đọc tin nhắn của em.</li>"
            "</ul>"
            "<p><small>Nếu có câu hỏi, hãy hỏi bố/mẹ hoặc thầy/cô nhé.</small></p>"
        )
        txt.setWordWrap(True)
        txt.setTextFormat(Qt.TextFormat.RichText)
        t1_layout.addWidget(txt)
        tabs.addTab(tab1, "📖 Phần mềm này làm gì?")

        # Tab 2 — usage summary
        tab2 = QWidget()
        t2_layout = QVBoxLayout(tab2)
        used = state.quota_seconds - state.remaining_seconds
        used_str = _fmt_seconds(max(0, used))
        quota_str = _fmt_seconds(state.quota_seconds)
        summary = QLabel(
            f"<h3>Hôm nay em đã dùng:</h3>"
            f"<p>🕐 <b>{used_str}</b> / {quota_str} (hạn mức)</p>"
            f"<p>{'🟢 Còn thời gian.' if state.remaining_seconds > 0 else '🔴 Đã hết giờ hôm nay.'}</p>"
        )
        summary.setTextFormat(Qt.TextFormat.RichText)
        t2_layout.addWidget(summary)
        tabs.addTab(tab2, "📊 Hôm nay em dùng gì")

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(tabs)
        close_btn = QPushButton("Đóng")
        close_btn.clicked.connect(self.accept)
        main_layout.addWidget(close_btn)


# ------------------------------------------------------------------ #
#  OgkTrayApp — entry point                                            #
# ------------------------------------------------------------------ #

class OgkTrayApp(QApplication):
    """
    Ứng dụng tray chính.

    Vòng đời:
    1. __init__: Kiểm tra tray available → nếu không → emit stop + exit(1)
    2. setup_tray(): Tạo QSystemTrayIcon, QMenu, kết nối signals
    3. QTimer 1s: tick() → giảm remaining_seconds, cập nhật menu, kiểm cảnh báo
    4. Khi manual_lock hoặc remaining ≤ 0 sau grace → show BlockingDialog
    """

    def __init__(self, state: Optional[TrayState] = None, ipc: Optional[IPCClient] = None):
        super().__init__(sys.argv)
        self.state = state or TrayState()
        self.ipc = ipc or IPCClient(mock=True)
        self._blocking_dialog: Optional[BlockingDialog] = None
        self._warned: set[int] = set()  # warning levels đã hiển thị
        self._grace_secs: int = 0  # đếm ngược grace period

        # Kiểm tra tray availability — PHẢI làm trước mọi thứ
        if not QSystemTrayIcon.isSystemTrayAvailable():
            _stop_emitter.stop_requested.emit("tray_unavailable")
            sys.exit(1)

        self.setup_tray()
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)  # mỗi giây

    def setup_tray(self):
        """Khởi tạo icon và context menu."""
        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(_make_icon("#4CAF50"))
        self._tray.setToolTip("OpenGuard Kids")
        self._tray.activated.connect(self._on_tray_activated)

        menu = QMenu()

        # Dòng hiển thị thời gian còn lại
        self._time_action = menu.addAction("⏱ Đang tải...")
        self._time_action.setEnabled(False)

        # Dòng trạng thái kết nối
        self._conn_action = menu.addAction("🔴 Offline")
        self._conn_action.setEnabled(False)

        menu.addSeparator()
        menu.addAction("📩 Xin thêm giờ / Yêu cầu", self._show_request_dialog)
        menu.addAction("❓ Phần mềm này làm gì?", self._show_info_dialog)
        menu.addSeparator()
        menu.addAction("Thoát (cần mật khẩu phụ huynh)", self._quit_with_auth)

        self._tray.setContextMenu(menu)
        self._tray.show()

        # NT2 / NT1: thông báo khởi động công khai
        self._tray.showMessage(
            "OpenGuard Kids đang chạy",
            "Phần mềm quản lý thời gian đang hoạt động công khai.",
            QSystemTrayIcon.MessageIcon.Information,
            3000,
        )

    def _tick(self):
        """Gọi mỗi giây bởi QTimer."""
        # Giảm remaining nếu không bị lock thủ công
        if not self.state.manual_lock and self.state.remaining_seconds > 0:
            self.state.remaining_seconds -= 1

        # Cập nhật warning level
        new_level = self.state.compute_warning_level()

        # Hiển thị cảnh báo lần đầu ở mỗi threshold
        if new_level > 0 and new_level not in self._warned:
            self._warned.add(new_level)
            self._show_warning(new_level)

        # Grace period: remaining = 0 → đếm 60s rồi lock
        if self.state.remaining_seconds <= 0 and not self.state.manual_lock:
            self._grace_secs += 1
            if self._grace_secs >= 60:
                self._show_blocking("")

        self._update_menu()
        self._update_icon(new_level)

        # Cập nhật trạng thái kết nối qua IPC
        self._poll_ipc()

    def _show_warning(self, level: int):
        """Hiển thị QMessageBox cảnh báo tại ngưỡng."""
        msgs = {
            1: ("⚠️ Sắp hết giờ", "Còn khoảng 10 phút. Hãy lưu bài đang làm nhé!"),
            2: ("⚠️ Còn 5 phút", "Còn khoảng 5 phút. Mau lưu bài đi nhé!"),
            3: ("🚨 Còn 1 phút!", "Chỉ còn 1 phút nữa. Lưu bài ngay!"),
            4: ("🔒 Hết giờ", "Em đã dùng hết giờ hôm nay. Máy sẽ khóa sau 60 giây."),
        }
        title, text = msgs.get(level, ("", ""))
        if title:
            QMessageBox.warning(None, title, text)

    def _show_blocking(self, reason: str):
        """Hiển thị dialog khóa (không thể đóng)."""
        if self._blocking_dialog is None or not self._blocking_dialog.isVisible():
            self._blocking_dialog = BlockingDialog(reason)
            self._blocking_dialog.show()

    def _update_menu(self):
        """Cập nhật text trong tray menu."""
        rem = _fmt_seconds(self.state.remaining_seconds)
        lock_indicator = " 🔒" if self.state.manual_lock else ""
        pending = self.state.pending_count()
        pending_str = f" (Chưa gửi: {pending})" if pending > 0 else ""

        self._time_action.setText(f"⏱ Còn lại: {rem}{lock_indicator}{pending_str}")
        self._conn_action.setText(
            "🟢 Đang kết nối" if self.state.online else "🔴 Offline"
        )

    def _update_icon(self, level: int):
        """Đổi màu icon theo trạng thái."""
        if self.state.manual_lock:
            self._tray.setIcon(_make_icon("#f44336"))  # đỏ
        elif level >= 3:
            self._tray.setIcon(_make_icon("#FF9800"))  # cam
        elif level >= 1:
            self._tray.setIcon(_make_icon("#FFC107"))  # vàng
        else:
            self._tray.setIcon(_make_icon("#4CAF50"))  # xanh

    def _poll_ipc(self):
        """Thử nhận telemetry từ agent core."""
        try:
            msg = self.ipc.receive()
            if msg.get("message_type") == "telemetry.sample":
                p = msg.get("payload", {})
                self.state.remaining_seconds = p.get(
                    "remaining_seconds", self.state.remaining_seconds
                )
                self.state.online = True
                # Flush offline queue
                pending = self.state.flush_offline_requests()
                for req in pending:
                    try:
                        self.ipc.send("request.submit", {
                            "request_type": req["type"],
                            "note": req["note"],
                        })
                    except IPCOfflineError:
                        self.state.add_offline_request(
                            req["type"], req["note"], req["queued_at"]
                        )
            elif msg.get("message_type") == "command.lock":
                p = msg.get("payload", {})
                self.state.manual_lock = True
                self.state.lock_reason = p.get("reason_code", "")
                self._show_blocking(self.state.lock_reason)
        except IPCOfflineError:
            self.state.online = False

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_info_dialog()

    def _show_request_dialog(self):
        dlg = RequestDialog(self.state, self.ipc, None)
        dlg.exec()

    def _show_info_dialog(self):
        dlg = InfoTabsDialog(self.state, None)
        dlg.exec()

    def _quit_with_auth(self):
        # TODO: gọi IPC yêu cầu parent PIN trước khi thoát
        QMessageBox.information(
            None,
            "Thoát",
            "Vui lòng nhập mật khẩu phụ huynh để thoát. (Tính năng sẽ được TV2 tích hợp.)",
        )


# ------------------------------------------------------------------ #
#  Entry point                                                         #
# ------------------------------------------------------------------ #

def main():
    """
    Khởi chạy ứng dụng tray.
    Môi trường headless: QT_QPA_PLATFORM=offscreen
    """
    app = OgkTrayApp()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
