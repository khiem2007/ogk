"""Add auth roles, sessions and login lockout.

Revision ID: 20261126_002
Revises: 20261123_001
Create Date: 2026-11-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20261126_002"
down_revision = "20261123_001"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    return {column["name"] for column in sa.inspect(bind).get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()

    users_columns = _columns("users")
    with op.batch_alter_table("users") as batch:
        if "role" not in users_columns:
            batch.add_column(sa.Column("role", sa.String(32), nullable=False, server_default="parent"))
        if "child_id" not in users_columns:
            batch.add_column(sa.Column("child_id", sa.String(36), nullable=True))

    table_names = set(sa.inspect(bind).get_table_names())
    if "auth_sessions" not in table_names:
        op.create_table(
            "auth_sessions",
            sa.Column("id", sa.String(36), primary_key=True, nullable=False),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("csrf_token_hash", sa.String(64), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_auth_sessions_user", "auth_sessions", ["user_id"])
        op.create_index("ix_auth_sessions_expiry", "auth_sessions", ["expires_at"])

    table_names = set(sa.inspect(bind).get_table_names())
    if "login_attempts" not in table_names:
        op.create_table(
            "login_attempts",
            sa.Column("id", sa.String(36), primary_key=True, nullable=False),
            sa.Column("email", sa.String(255), nullable=False),
            sa.Column("ip_address", sa.String(45), nullable=False),
            sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("locked_until", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("email", "ip_address", name="uq_login_attempt_email_ip"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    table_names = set(sa.inspect(bind).get_table_names())
    if "login_attempts" in table_names:
        op.drop_table("login_attempts")
    if "auth_sessions" in table_names:
        op.drop_index("ix_auth_sessions_expiry", table_name="auth_sessions")
        op.drop_index("ix_auth_sessions_user", table_name="auth_sessions")
        op.drop_table("auth_sessions")
