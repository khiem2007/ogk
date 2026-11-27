"""Add enrollment and device token lifecycle state.

Revision ID: 20261126_003
Revises: 20261126_002
Create Date: 2026-11-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20261126_003"
down_revision = "20261126_002"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    if "code_prefix" not in _columns("enrollment_codes"):
        with op.batch_alter_table("enrollment_codes") as batch:
            batch.add_column(sa.Column("code_prefix", sa.String(4), nullable=True))
            batch.add_column(sa.Column("child_id", sa.String(36), nullable=True))
            batch.create_foreign_key(
                "fk_enrollment_codes_child_id_children",
                "children",
                ["child_id"],
                ["id"],
                ondelete="CASCADE",
            )
    elif "child_id" not in _columns("enrollment_codes"):
        with op.batch_alter_table("enrollment_codes") as batch:
            batch.add_column(sa.Column("child_id", sa.String(36), nullable=True))
            batch.create_foreign_key(
                "fk_enrollment_codes_child_id_children",
                "children",
                ["child_id"],
                ["id"],
                ondelete="CASCADE",
            )

    if "ix_enrollment_codes_prefix" not in {
        index["name"] for index in sa.inspect(op.get_bind()).get_indexes("enrollment_codes")
    }:
        op.create_index("ix_enrollment_codes_prefix", "enrollment_codes", ["code_prefix"])

    tables = _tables()
    if "device_auth_credentials" not in tables:
        op.create_table(
            "device_auth_credentials",
            sa.Column("id", sa.String(36), primary_key=True, nullable=False),
            sa.Column(
                "device_id",
                sa.String(36),
                sa.ForeignKey("devices.id", ondelete="CASCADE"),
                nullable=False,
                unique=True,
            ),
            sa.Column("access_expires_at", sa.DateTime(), nullable=False),
            sa.Column("refresh_expires_at", sa.DateTime(), nullable=False),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index(
            "ix_device_auth_credentials_access_expiry",
            "device_auth_credentials",
            ["access_expires_at"],
        )

    tables = _tables()
    if "device_refresh_tokens" not in tables:
        op.create_table(
            "device_refresh_tokens",
            sa.Column("id", sa.String(36), primary_key=True, nullable=False),
            sa.Column(
                "credential_id",
                sa.String(36),
                sa.ForeignKey("device_auth_credentials.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("consumed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index(
            "ix_device_refresh_tokens_credential",
            "device_refresh_tokens",
            ["credential_id"],
        )
        op.create_index(
            "ix_device_refresh_tokens_expiry",
            "device_refresh_tokens",
            ["expires_at"],
        )

    if "enrollment_attempts" not in _tables():
        op.create_table(
            "enrollment_attempts",
            sa.Column("ip_address", sa.String(45), primary_key=True, nullable=False),
            sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("window_started_at", sa.DateTime(), nullable=False),
            sa.Column("locked_until", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    tables = _tables()
    if "enrollment_attempts" in tables:
        op.drop_table("enrollment_attempts")
    if "device_refresh_tokens" in tables:
        op.drop_index("ix_device_refresh_tokens_expiry", table_name="device_refresh_tokens")
        op.drop_index("ix_device_refresh_tokens_credential", table_name="device_refresh_tokens")
        op.drop_table("device_refresh_tokens")
    if "device_auth_credentials" in tables:
        op.drop_index("ix_device_auth_credentials_access_expiry", table_name="device_auth_credentials")
        op.drop_table("device_auth_credentials")
    if "ix_enrollment_codes_prefix" in {
        index["name"] for index in sa.inspect(op.get_bind()).get_indexes("enrollment_codes")
    }:
        op.drop_index("ix_enrollment_codes_prefix", table_name="enrollment_codes")
    columns = _columns("enrollment_codes")
    if "child_id" in columns or "code_prefix" in columns:
        with op.batch_alter_table("enrollment_codes") as batch:
            if "child_id" in columns:
                batch.drop_column("child_id")
            if "code_prefix" in columns:
                batch.drop_column("code_prefix")
