import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.repositories import OperationalMetadataRepository, SovereignVaultRepository
from app.services.storage_service import get_redacted_file_path
from app.utils.time_utils import to_wib_iso

router = APIRouter(tags=["storage"])


def _json_list(value: str) -> list[Any]:
    try:
        data = json.loads(value or "[]")
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


@router.get("/files/redacted/{filename}")
def redacted_file(filename: str) -> FileResponse:
    try:
        path = get_redacted_file_path(filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not path.exists():
        raise HTTPException(status_code=404, detail="Redacted file not found")
    return FileResponse(path)


@router.get("/storage/records")
def storage_records(db: Annotated[Session, Depends(get_db)], limit: int = Query(default=50, ge=1, le=200)) -> dict[str, object]:
    records = []
    for op in OperationalMetadataRepository(db).list_recent(limit):
        vault = SovereignVaultRepository(db).get_by_record_id(op.record_id)
        records.append({
            "record_id": op.record_id,
            "upload_session_id": op.upload_session_id,
            "original_filename": op.original_filename,
            "redacted_filename": op.redacted_filename,
            "redacted_url": f"/api/files/redacted/{op.redacted_filename}",
            "redaction_profile": op.redaction_profile,
            "redaction_mode": op.redaction_mode,
            "active_classes": _json_list(op.active_classes_json),
            "confidence_threshold": op.confidence_threshold,
            "detection_count": op.detection_count,
            "redacted_count": op.redacted_count,
            "latency_ms": op.latency_ms,
            "detected_classes": _json_list(op.detected_classes_json),
            "stores_private_original_in_operational_zone": op.stores_private_original_in_operational_zone,
            "vault_encrypted": bool(vault),
            "vault_key_id": vault.key_id if vault else None,
            "vault_key_version": vault.key_version if vault else None,
            "created_at": to_wib_iso(op.created_at),
        })
    return {"records": records, "count": len(records)}
