# Windows spikes B01

Phụ trách: **TV2**. Các script cần **Windows VM + CPython**. Cài dependency:

```powershell
py -3 -m pip install -r requirements-windows-spikes.txt
```

Tất cả script mặc định là dry-run/read-only. Có thể ghi rõ `--dry-run`. Chỉ hai thao tác làm thay đổi trạng thái máy là ngắt phiên và khôi phục DNS; cả hai đều cần `--execute` cùng token xác nhận.

## Session, SID và fallback disconnect

```powershell
py -3 agent/spikes/spike_session_sid.py --dry-run --parent-user Parent --child-user Child
py -3 agent/spikes/spike_session_sid.py --dry-run --session-id 2
```

Kết quả gồm `SessionId`, WinStation, trạng thái WTS, tài khoản, SID, loại Admin/Standard, vai trò và active console. Thử fallback từ tiến trình thật sự chạy trong Session 0:

```powershell
py -3 agent/spikes/spike_session_sid.py --session-id 2 --execute --confirm-disconnect DISCONNECT-2
```

Script cấm target Session 0 và cấm nhánh thực thi nếu tiến trình gọi không ở Session 0. `DISCONNECTED` không được báo thành `LOCKED`.

## Foreground process và idle

Chạy trong phiên đăng nhập của trẻ, không chạy từ Session 0:

```powershell
py -3 agent/spikes/spike_foreground_idle.py --dry-run --samples 5 --interval 1
```

Mỗi mẫu ghi HWND, PID, process name/path, session của helper/process và idle time lấy từ `GetLastInputInfo`. Không đọc hoặc xuất tiêu đề cửa sổ theo nguyên tắc tối thiểu dữ liệu. Script chỉ đọc dữ liệu; `--execute` là cờ tương thích và không mở thêm thao tác ghi.

## Named Pipe, DACL và replay

Dry-run dựng DACL LocalSystem + tài khoản trẻ, kiểm payload tối đa 4096 byte, UUID trùng và timestamp lệch quá 30 giây:

```powershell
py -3 agent/spikes/spike_ipc_pipe.py --dry-run --child-account .\Child
```

Thử live: server chạy trong terminal elevated/System; client chạy trong phiên trẻ:

```powershell
py -3 agent/spikes/spike_ipc_pipe.py --execute --role server --child-account .\Child
py -3 agent/spikes/spike_ipc_pipe.py --execute --role client
```

Phải thử thêm một tài khoản không có trong DACL và lưu bằng chứng `Access denied`. Replay cache hiện chỉ sống trong tiến trình vì đây là spike, chưa phải IPC production của B05.

## DNS backup/restore

Đọc các adapter đang `Up`, tách IPv4/IPv6, nguồn DNS DHCP/Static và ghi backup JSON:

```powershell
py -3 agent/spikes/spike_dns_backup.py --dry-run --output runtime/dns-backups/before.json
```

Xem kế hoạch khôi phục mà chưa đổi hệ thống:

```powershell
py -3 agent/spikes/spike_dns_backup.py --dry-run --restore runtime/dns-backups/before.json
```

Chỉ sau khi kiểm tra backup, chạy terminal Administrator:

```powershell
py -3 agent/spikes/spike_dns_backup.py --restore runtime/dns-backups/before.json --execute --confirm-restore RESTORE-DNS
```

Restore đối chiếu InterfaceIndex và GUID, đặt lại DHCP hoặc danh sách DNS tĩnh cho từng family, rồi chạy `ipconfig /flushdns`. Đây là spike chuẩn bị cho B09; chưa có preflight proxy/rollback giao dịch.

## Bằng chứng cần lưu từ VM

- Bảng phiên trước/sau lock, unlock và disconnect; chỉ rõ parent/child/Session 0.
- Foreground và idle ở đúng phiên trẻ.
- DACL được phép/từ chối theo SID; payload quá cỡ, UUID replay và timestamp cũ đều bị từ chối.
- JSON DNS trước/sau cho adapter DHCP và Static, cả IPv4/IPv6; kết quả restore và flush DNS.

Không đưa username thật, token hoặc dữ liệu nhạy cảm vào Git. Lưu bằng chứng đã che thông tin trong `docs/evidence/`.
