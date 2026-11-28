from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from server.app.db.base import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="parent")
    child_id: Mapped[str | None] = mapped_column(ForeignKey("children.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    __table_args__ = (
        CheckConstraint("role IN ('parent','child-view','admin')", name="ck_users_role"),
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    csrf_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    revoked_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    __table_args__ = (
        Index("ix_auth_sessions_user", "user_id"),
        Index("ix_auth_sessions_expiry", "expires_at"),
    )


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), primary_key=False, nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None]
    updated_at: Mapped[datetime] = mapped_column(nullable=False)
    __table_args__ = (
        UniqueConstraint("email", "ip_address", name="uq_login_attempt_email_ip"),
    )


class Child(Base):
    __tablename__ = "children"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    age_band: Mapped[str | None] = mapped_column(String(32))
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)


class Device(Base):
    __tablename__ = "devices"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    child_id: Mapped[str] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), nullable=False)
    windows_sid: Mapped[str | None] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    token_hash: Mapped[str | None] = mapped_column(String(255))
    last_seen_at: Mapped[datetime | None]
    applied_policy_version: Mapped[int | None] = mapped_column(Integer)
    revoked_at: Mapped[datetime | None]
    __table_args__ = (Index("ix_devices_child_id", "child_id"),)


class DeviceAuthCredential(Base):
    __tablename__ = "device_auth_credentials"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), unique=True, nullable=False)
    access_expires_at: Mapped[datetime] = mapped_column(nullable=False)
    refresh_expires_at: Mapped[datetime] = mapped_column(nullable=False)
    revoked_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    __table_args__ = (Index("ix_device_auth_credentials_access_expiry", "access_expires_at"),)


class DeviceRefreshToken(Base):
    __tablename__ = "device_refresh_tokens"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    credential_id: Mapped[str] = mapped_column(
        ForeignKey("device_auth_credentials.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    consumed_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    __table_args__ = (
        Index("ix_device_refresh_tokens_credential", "credential_id"),
        Index("ix_device_refresh_tokens_expiry", "expires_at"),
    )


class EnrollmentCode(Base):
    __tablename__ = "enrollment_codes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    code_prefix: Mapped[str | None] = mapped_column(String(4))
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    consumed_at: Mapped[datetime | None]
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    child_id: Mapped[str | None] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"))
    __table_args__ = (Index("ix_enrollment_codes_prefix", "code_prefix"),)


class EnrollmentAttempt(Base):
    __tablename__ = "enrollment_attempts"
    ip_address: Mapped[str] = mapped_column(String(45), primary_key=True)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    window_started_at: Mapped[datetime] = mapped_column(nullable=False)
    locked_until: Mapped[datetime | None]


class Policy(Base):
    __tablename__ = "policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    document_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    __table_args__ = (UniqueConstraint("device_id", "version", name="uq_policies_device_version"),)


class AppCatalog(Base):
    __tablename__ = "app_catalog"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_exe_name: Mapped[str | None] = mapped_column(String(255))
    normalized_path: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(64))


class UsageInterval(Base):
    __tablename__ = "usage_intervals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(36), nullable=False)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    start_utc: Mapped[datetime] = mapped_column(nullable=False)
    end_utc: Mapped[datetime] = mapped_column(nullable=False)
    active_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    app_id: Mapped[str | None] = mapped_column(ForeignKey("app_catalog.id", ondelete="SET NULL"))
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    boot_id: Mapped[str] = mapped_column(String(36), nullable=False)
    __table_args__ = (
        UniqueConstraint("device_id", "event_id", name="uq_usage_device_event"),
        CheckConstraint("end_utc > start_utc", name="ck_usage_end_after_start"),
        CheckConstraint("active_seconds >= 0", name="ck_usage_active_nonnegative"),
        Index("ix_usage_device_time", "device_id", "start_utc", "end_utc"),
    )


class DeviceEvent(Base):
    __tablename__ = "device_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(36), nullable=False)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(64))
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    __table_args__ = (
        UniqueConstraint("device_id", "event_id", name="uq_events_device_event"),
        Index("ix_events_device_time", "device_id", "observed_at"),
    )


class Request(Base):
    __tablename__ = "requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    request_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    decided_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    decided_at: Mapped[datetime | None]
    __table_args__ = (
        CheckConstraint("status IN ('pending','approved','rejected','expired')", name="ck_requests_status"),
        Index("ix_requests_device_status_time", "device_id", "status", "created_at"),
    )


class Grant(Base):
    __tablename__ = "grants"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_id: Mapped[str | None] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), unique=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    scope_json: Mapped[str] = mapped_column(Text, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(nullable=False)
    valid_until: Mapped[datetime] = mapped_column(nullable=False)
    amount_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    local_date: Mapped[str] = mapped_column(String(10), nullable=False)


class Command(Base):
    __tablename__ = "commands"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    issued_at: Mapped[datetime] = mapped_column(nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    delivered_at: Mapped[datetime | None]
    resolved_at: Mapped[datetime | None]
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    dedup_key: Mapped[str] = mapped_column(String(36), nullable=False)
    result_json: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        UniqueConstraint("device_id", "dedup_key", name="uq_commands_device_dedup"),
        CheckConstraint("status IN ('queued','delivered','executed','failed','expired')", name="ck_commands_status"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    device_id: Mapped[str | None] = mapped_column(ForeignKey("devices.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False)
    before_json: Mapped[str | None] = mapped_column(Text)
    after_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    __table_args__ = (
        Index("ix_audit_actor_time", "actor_user_id", "created_at"),
        Index("ix_audit_device_time", "device_id", "created_at"),
    )


class TransparencyRecord(Base):
    __tablename__ = "transparency_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    child_id: Mapped[str] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), nullable=False)
    explanation_version: Mapped[str] = mapped_column(String(36), nullable=False)
    acknowledged_at: Mapped[datetime] = mapped_column(nullable=False)
