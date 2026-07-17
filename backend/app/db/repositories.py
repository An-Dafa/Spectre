from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.db.models import (
    AuditLog,
    GovernmentAccessRequest,
    OperationalMetadata,
    SovereignVaultRecord,
    VaultKey,
)


class BaseRepository:
    model: type

    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, instance: Any) -> Any:
        self.db.add(instance)
        self.db.flush()
        self.db.refresh(instance)
        return instance


class OperationalMetadataRepository(BaseRepository):
    model = OperationalMetadata

    def get_by_record_id(self, record_id: str) -> OperationalMetadata | None:
        return self.db.scalar(select(OperationalMetadata).where(OperationalMetadata.record_id == record_id))

    def list_recent(self, limit: int = 50) -> Sequence[OperationalMetadata]:
        statement = select(OperationalMetadata).order_by(OperationalMetadata.created_at.desc()).limit(limit)
        return self.db.scalars(statement).all()


class SovereignVaultRepository(BaseRepository):
    model = SovereignVaultRecord

    def get_by_record_id(self, record_id: str) -> SovereignVaultRecord | None:
        return self.db.scalar(select(SovereignVaultRecord).where(SovereignVaultRecord.record_id == record_id))


class VaultKeyRepository(BaseRepository):
    model = VaultKey

    def get_active(self) -> VaultKey | None:
        return self.db.scalar(select(VaultKey).where(VaultKey.is_active.is_(True)))

    def get_by_version(self, key_version: int) -> VaultKey | None:
        return self.db.scalar(select(VaultKey).where(VaultKey.key_version == key_version))

    def get_latest_version(self) -> int:
        keys = self.db.scalars(select(VaultKey).order_by(VaultKey.key_version.desc()).limit(1)).all()
        return keys[0].key_version if keys else 0


class GovernmentAccessRequestRepository(BaseRepository):
    model = GovernmentAccessRequest

    def get_by_request_id(self, request_id: str) -> GovernmentAccessRequest | None:
        return self.db.scalar(
            select(GovernmentAccessRequest).where(GovernmentAccessRequest.request_id == request_id)
        )


class AuditLogRepository(BaseRepository):
    model = AuditLog

    def list_logs(
        self,
        limit: int = 50,
        record_id: str | None = None,
        zone: str | None = None,
        event_type: str | None = None,
    ) -> Sequence[AuditLog]:
        statement: Select[tuple[AuditLog]] = select(AuditLog)
        if record_id:
            statement = statement.where(AuditLog.record_id == record_id)
        if zone:
            statement = statement.where(AuditLog.zone == zone)
        if event_type:
            statement = statement.where(AuditLog.event_type == event_type)
        statement = statement.order_by(AuditLog.created_at.desc()).limit(limit)
        return self.db.scalars(statement).all()
