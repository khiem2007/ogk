"""
agent/tray/ipc_client.py
========================
IPCClient — giao tiếp giữa Tray và agent core qua Unix socket (Linux)
hoặc Named Pipe stub (Windows).

Giải thích luồng hoạt động:
1. Tray app gọi `client.send(message_type, payload)` → đóng gói thành
   JSON theo ipc_message.schema.json → gửi qua socket.
2. Tray app gọi `client.receive()` → nhận JSON từ socket → validate schema
   → trả về dict.
3. Nếu socket chưa sẵn sàng (agent core chưa chạy) → raise IPCOfflineError
   → Tray chuyển sang chế độ offline, queue requests.

NT2 enforcement tại đây:
- `FORBIDDEN_PAYLOAD_KEYS` = {"window_title", "url", "screenshot", "keylog"}
- Nếu payload chứa bất kỳ key nào trong danh sách → raise ValueError ngay
  trước khi gửi, KHÔNG BAO GIỜ truyền ra ngoài tiến trình.

Vì cross-platform test (Linux không có Windows Named Pipe), module dùng
Unix socket trên Linux và mock/stub trên Windows (hoặc khi MOCK_IPC=1).
"""

from __future__ import annotations
import json
import os
import socket
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

# Keys bị cấm trong payload (NT2 — không thu thập nội dung)
FORBIDDEN_PAYLOAD_KEYS = {"window_title", "url", "screenshot", "keylog"}

VALID_MESSAGE_TYPES = {
    "telemetry.sample",
    "request.submit",
    "status.get",
    "notification.ack",
    "command.lock",
    "command.result",
}


class IPCOfflineError(Exception):
    """Agent core chưa sẵn sàng hoặc socket ngắt kết nối."""


class IPCClient:
    """
    Client IPC nhẹ, chỉ dùng stdlib (không cần PySide6).
    Dễ unit-test độc lập với GUI.
    """

    def __init__(
        self,
        socket_path: str = "/tmp/ogk_ipc.sock",
        session_id: int = 1,
        child_sid: str = "S-1-5-21-0-0-0-1001",
        mock: bool = False,
    ):
        self.socket_path = socket_path
        self.session_id = session_id
        self.child_sid = child_sid
        self._mock = mock or os.environ.get("OGK_MOCK_IPC", "0") == "1"
        self._mock_responses: list[Dict[str, Any]] = []  # cho unit tests

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def build_message(
        self,
        message_type: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Đóng gói message theo ipc_message.schema.json.
        Validate NT2 và message_type trước khi trả về.
        """
        if message_type not in VALID_MESSAGE_TYPES:
            raise ValueError(f"Unknown message_type: {message_type}")

        # NT2: reject payload có key nhạy cảm
        bad = FORBIDDEN_PAYLOAD_KEYS & set(payload.keys())
        if bad:
            raise ValueError(f"NT2 violation — forbidden payload keys: {bad}")

        return {
            "schema_version": 1,
            "message_id": str(uuid.uuid4()),
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "session_id": self.session_id,
            "child_sid": self.child_sid,
            "message_type": message_type,
            "payload": payload,
        }

    def send(self, message_type: str, payload: Dict[str, Any]) -> None:
        """Gửi message lên agent core."""
        msg = self.build_message(message_type, payload)
        if self._mock:
            return  # mock mode: bỏ qua gửi thật
        self._send_raw(json.dumps(msg).encode())

    def receive(self) -> Dict[str, Any]:
        """Nhận 1 message từ agent core."""
        if self._mock:
            if self._mock_responses:
                return self._mock_responses.pop(0)
            raise IPCOfflineError("No mock response queued")
        return self._recv_raw()

    def inject_mock_response(self, msg: Dict[str, Any]) -> None:
        """Dùng trong unit tests để inject response giả."""
        self._mock_responses.append(msg)

    # ------------------------------------------------------------------ #
    #  Internal socket I/O                                                 #
    # ------------------------------------------------------------------ #

    def _send_raw(self, data: bytes) -> None:
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.connect(self.socket_path)
                s.sendall(data)
        except (FileNotFoundError, ConnectionRefusedError) as e:
            raise IPCOfflineError(str(e)) from e

    def _recv_raw(self) -> Dict[str, Any]:
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.connect(self.socket_path)
                chunks = []
                while True:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    chunks.append(chunk)
            return json.loads(b"".join(chunks))
        except (FileNotFoundError, ConnectionRefusedError) as e:
            raise IPCOfflineError(str(e)) from e
