"""Export all-day iCalendar schedules from docs/PHAN_CONG.md (Python stdlib)."""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/calendar'
PLAN_URL = 'https://github.com/khiem2007/ogk/blob/main/docs/PHAN_CONG.md'
START, END = date(2026, 10, 26), date(2026, 11, 29)


def escape(value):
    return value.replace('\\', '\\\\').replace('\r\n', '\n').replace('\n', '\\n').replace(';', '\\;').replace(',', '\\,')


def fold(line):
    """Fold at <=75 UTF-8 octets without splitting a Unicode code point."""
    parts, current = [], ''
    for char in line:
        if len((current + char).encode('utf-8')) > 75:
            prefix = current.rstrip(' \t')
            carry = current[len(prefix):]
            parts.append(prefix)
            current = ' ' + carry
        current += char
    parts.append(current)
    return '\r\n'.join(parts)


def tasks():
    found = []
    for line in (ROOT / 'docs/PHAN_CONG.md').read_text(encoding='utf-8').splitlines():
        if not re.match(r'\| [ABC]\d\d \|', line):
            continue
        code, week, begin, due, hours, dependency, work, knowledge, acceptance = [v.strip() for v in line.strip('|').split('|')]
        begin, due = (datetime.strptime(v, '%d/%m/%Y').date() for v in (begin, due))
        if not START <= begin <= due <= END:
            raise ValueError(f'{code}: date outside project period')
        owner = {'A': 'TV1', 'B': 'TV2', 'C': 'TV3'}[code[0]]
        found.append(dict(
            code=code, owner=owner, begin=begin, due=due,
            title=f'[OGK][{owner}][{code}] {work.split(";")[0]}',
            description=f'Phụ trách: {owner}\nTuần: {week}\nƯớc lượng: {hours} giờ trong khoảng triển khai này (không phải làm cả ngày).\nHạn hoàn thành: {due:%d/%m/%Y}, hết ngày UTC+7.\nPhụ thuộc: {dependency}\nĐầu ra: {work}\nKiến thức cần học: {knowledge}\nNghiệm thu: {acceptance}\nReview/test và cập nhật PROGRESS trước khi đóng task.\nChi tiết: {PLAN_URL}',
        ))
    if len(found) != 32 or len({v['code'] for v in found}) != 32:
        raise ValueError('Expected exactly 32 unique tasks')
    return found


def milestones():
    specs = [
        ('KICKOFF', START, 'Khởi động dự án 5 tuần', 'Cả nhóm điền tên TV1–TV3, chốt phạm vi MVP và contract. Quỹ 136 giờ/người trong 5 tuần, trung bình 27,2 giờ/tuần. Dùng lịch task để tự phân bổ giờ làm; các sự kiện đều là cả ngày.'),
        ('M1', date(2026, 11, 1), 'Mốc tuần 1: đặc tả, spike và nền tảng', 'TV1: A01/A02; A03 đang làm. TV2: B01/B02. TV3: C01/C02. Nghiệm thu SRS/ERD/contracts và spike SID/session/IPC/DNS; core/UI shell. Ghi rõ spike chưa chứng minh được.'),
        ('M2', date(2026, 11, 8), 'Mốc tuần 2: pairing, policy và counter', 'TV1: A03–A05 xong, A06 đang làm. TV2: B03/B04 xong, B05 đang làm. TV3: C03 xong, C04 đang làm. Nghiệm thu ghép thiết bị và policy thật, simulator/counter pass; bắt đầu service integration.'),
        ('M3', date(2026, 11, 15), 'Mốc tuần 3: agent thật, offline và commands', 'TV1: A06–A08. TV2: B05–B07. TV3: C04/C05. Nghiệm thu service/helper/Tray thật, offline 10 phút/reconnect, grant/command qua API-agent. UI duyệt/điều khiển hoàn thành 18/11.'),
        ('M4', date(2026, 11, 22), 'Mốc tuần 4: E2E chính, báo cáo và DNS proxy', 'TV1: A09/A10. TV2: B08; B09 chuẩn bị adapter/rollback theo contract. TV3: C06/C07. Nghiệm thu luồng UI–API–agent và báo cáo thật; DNS proxy unit/integration pass. Tích hợp adapter DNS/UI hoàn thành 25/11.'),
        ('RC', date(2026, 11, 28), 'Chốt bản nghiệm thu và kiểm thử VM sạch', 'TV1: A11/A12. TV2: B09/B10. TV3: C08/C09; chốt evidence C10. Nghiệm thu HTTPS, cài/gỡ và DNS restore, E2E, đo mục tiêu lab 70s/10s/3s. Chỉ sửa lỗi ảnh hưởng bàn giao; không thêm tính năng.'),
        ('M5', END, 'DEADLINE: demo và bàn giao OpenGuard Kids', 'Hạn cuối dự án: hết ngày 29/11/2026 (UTC+7). Cả nhóm chạy demo 8–10 phút, nộp source/build, hướng dẫn cài/gỡ, test report/evidence và video. TV3 hoàn tất C10. Ghi đúng phần chưa làm/chưa chạy. Extension chuyển sau deadline.'),
    ]
    return [dict(code=code, owner='NHOM', begin=day, due=day,
                 title=f'[OGK][NHÓM] {title}', description=description + '\n' + PLAN_URL)
            for code, day, title, description in specs]


def export(filename, title, events):
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//OpenGuard Kids//Five Week Project Plan//VI',
             'CALSCALE:GREGORIAN', 'METHOD:PUBLISH', 'X-WR-CALNAME:' + escape(title), 'X-WR-TIMEZONE:Asia/Bangkok']
    for item in sorted(events, key=lambda v: (v['begin'], v['code'])):
        lines.extend([
            'BEGIN:VEVENT', f"UID:ogk-20261026-{item['code'].lower()}@calendar.ogk.local",
            'DTSTAMP:' + stamp, 'SEQUENCE:0',
            'DTSTART;VALUE=DATE:' + item['begin'].strftime('%Y%m%d'),
            'DTEND;VALUE=DATE:' + (item['due'] + timedelta(days=1)).strftime('%Y%m%d'),
            'SUMMARY:' + escape(item['title']), 'DESCRIPTION:' + escape(item['description']),
            'URL:' + PLAN_URL, 'STATUS:CONFIRMED', 'TRANSP:TRANSPARENT',
            'CATEGORIES:' + item['owner'], 'END:VEVENT',
        ])
    lines.append('END:VCALENDAR')
    target = OUT / filename
    target.write_bytes(('\r\n'.join(fold(line) for line in lines) + '\r\n').encode('utf-8'))
    print(f'{target.relative_to(ROOT)}: {len(events)} events')


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    work, shared = tasks(), milestones()
    export('OGK-5-tuan-toan-nhom.ics', 'OGK | Toàn nhóm | 26-10 đến 29-11-2026', work + shared)
    for owner in ('TV1', 'TV2', 'TV3'):
        export(f'OGK-5-tuan-{owner}.ics', f'OGK | {owner} | 5 tuần',
               [item for item in work if item['owner'] == owner] + shared)
