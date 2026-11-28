"""A09 report and retention indexes.

Revision ID: 20261128_005
Revises: 20261128_004
Create Date: 2026-11-28
"""

from alembic import op

revision = "20261128_005"
down_revision = "20261128_004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_requests_device_created", "requests", ["device_id", "created_at"])
    op.create_index("ix_grants_device_validity", "grants", ["device_id", "valid_from", "valid_until"])
    op.create_index("ix_commands_device_issued", "commands", ["device_id", "issued_at"])


def downgrade() -> None:
    op.drop_index("ix_commands_device_issued", table_name="commands")
    op.drop_index("ix_grants_device_validity", table_name="grants")
    op.drop_index("ix_requests_device_created", table_name="requests")
