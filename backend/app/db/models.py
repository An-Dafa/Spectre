from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.utils.time_utils import utc_now


class OperationalMetadata(Base):
    __tablename__ = "operational_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    record_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    upload_session_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    redacted_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    redacted_path: Mapped[str] = mapped_column(Text, nullable=False)
    redaction_profile: Mapped[str] = mapped_column(String(64), nullable=False)
    redaction_mode: Mapped[str] = mapped_column(String(64), nullable=False)
    active_classes_json: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    detection_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    redacted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    detected_classes_json: Mapped[str] = mapped_column(Text, nullable=False)
    stores_private_original_in_operational_zone: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class SovereignVaultRecord(Base):
    __tablename__ = "sovereign_vault_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    record_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    upload_session_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_bundle_path: Mapped[str] = mapped_column(Text, nullable=False)
    encryption_algorithm: Mapped[str] = mapped_column(String(128), nullable=False)
    key_id: Mapped[str] = mapped_column(String(128), nullable=False)
    key_version: Mapped[int] = mapped_column(Integer, nullable=False)
    nonce_b64: Mapped[str] = mapped_column(Text, nullable=False)
    wrapped_dek_b64: Mapped[str] = mapped_column(Text, nullable=False)
    original_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    ciphertext_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    plaintext_stored: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class VaultKey(Base):
    __tablename__ = "vault_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    key_version: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    public_key_path: Mapped[str] = mapped_column(Text, nullable=False)
    private_key_path: Mapped[str] = mapped_column(Text, nullable=False)
    public_key_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GovernmentAccessRequest(Base):
    __tablename__ = "government_access_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    request_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    record_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    requester: Mapped[str] = mapped_column(String(255), nullable=False)
    requester_role: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    access_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    access_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    access_token_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    record_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    zone: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    details_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

