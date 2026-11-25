"""Initial server database schema.

Revision ID: 20261123_001
Revises:
Create Date: 2026-11-23
"""

from alembic import op

from server.app.db.base import Base
import server.app.models.entities  # noqa: F401


revision = "20261123_001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("PRAGMA foreign_keys=ON")
    bind.exec_driver_sql("PRAGMA busy_timeout=5000")
    bind.exec_driver_sql("PRAGMA journal_mode=WAL")
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("PRAGMA foreign_keys=OFF")
    for table_name in (
        "transparency_records", "audit_logs", "commands", "grants", "requests",
        "device_events", "usage_intervals", "app_catalog", "policies",
        "enrollment_codes", "devices", "children", "users",
    ):
        if table_name in bind.dialect.get_table_names(bind):
            op.drop_table(table_name)
