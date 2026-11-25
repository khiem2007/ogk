# server/app/models

Phụ trách: **TV1**.

ORM baseline theo ERD: users, children, devices, enrollment codes, policies, app catalog, usage, events, requests, grants, commands, audit và transparency.

Đã khai báo foreign key, unique event/policy/command/grant constraint và report/audit indexes. Schema thực thi qua migration Alembic, không tạo bảng ad-hoc trong runtime.

Trạng thái: baseline model/migration A02 đã triển khai. Xem [bảng phân công](../../../docs/PHAN_CONG.md).
