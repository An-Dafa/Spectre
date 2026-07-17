import json
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import AuditLog
from app.db.repositories import AuditLogRepository
from app.utils.time_utils import to_wib_iso


def _json_default(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return to_wib_iso(value)
    return str(value)


def create_audit_log(
    db: Session,
    record_id: str | None,
    zone: str,
    event_type: str,
    actor: str,
    action: str,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    details_json = json.dumps(details or {}, default=_json_default, ensure_ascii=False)
    entry = AuditLog(
        record_id=record_id,
        zone=zone,
        event_type=event_type,
        actor=actor,
        action=action,
        details_json=details_json,
    )
    return AuditLogRepository(db).add(entry)


def parse_audit_details(details_json: str) -> dict[str, Any]:
    try:
        parsed = json.loads(details_json or "{}")
    except json.JSONDecodeError:
        return {"raw": details_json}
    return parsed if isinstance(parsed, dict) else {"value": parsed}


def serialize_audit_log(entry: AuditLog) -> dict[str, Any]:
    return {
        "id": entry.id,
        "record_id": entry.record_id,
        "zone": entry.zone,
        "event_type": entry.event_type,
        "actor": entry.actor,
        "action": entry.action,
        "details": parse_audit_details(entry.details_json),
        "created_at": to_wib_iso(entry.created_at),
    }


def list_audit_logs(
    db: Session,
    limit: int = 50,
    record_id: str | None = None,
    zone: str | None = None,
    event_type: str | None = None,
) -> list[dict[str, Any]]:
    entries = AuditLogRepository(db).list_logs(
        limit=limit,
        record_id=record_id,
        zone=zone,
        event_type=event_type,
    )
    return [serialize_audit_log(entry) for entry in entries]
