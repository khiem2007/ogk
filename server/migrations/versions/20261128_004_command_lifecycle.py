"""Add command lifecycle timestamps.

Revision ID: 20261128_004
Revises: 20261126_003
Create Date: 2026-11-28
"""

from alembic import op

revision = "20261128_004"
down_revision = "20261126_003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {row[1] for row in bind.exec_driver_sql("PRAGMA table_info(commands)").fetchall()}
    if "issued_at" not in columns:
        op.execute("ALTER TABLE commands ADD COLUMN issued_at DATETIME")
        op.execute("UPDATE commands SET issued_at = expires_at WHERE issued_at IS NULL")
    if "delivered_at" not in columns:
        op.execute("ALTER TABLE commands ADD COLUMN delivered_at DATETIME")
    if "resolved_at" not in columns:
        op.execute("ALTER TABLE commands ADD COLUMN resolved_at DATETIME")


def downgrade() -> None:
    pass
