from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.repositories import SovereignVaultRepository
from app.services.government_access_service import (
    approve_access_request,
    create_access_request,
    get_access_request,
    secure_original_download,
    serialize_access_request,
    validate_approver_token,
    validate_government_token,
)
from app.utils.time_utils import to_wib_iso

router = APIRouter(tags=["government-access"])


@router.get("/vault/records/{record_id}")
def vault_record(record_id: str, db: Annotated[Session, Depends(get_db)]) -> dict[str, object]:
    record = SovereignVaultRepository(db).get_by_record_id(record_id)
    if not record:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Vault record not found")
    return {
        "record_id": record.record_id,
        "original_filename": record.original_filename,
        "encryption_algorithm": record.encryption_algorithm,
        "key_id": record.key_id,
        "key_version": record.key_version,
        "original_sha256": record.original_sha256,
        "ciphertext_sha256": record.ciphertext_sha256,
        "plaintext_returned": False,
        "access_level": "metadata_only",
        "retention_status": "encrypted_bundle_available",
        "created_at": to_wib_iso(record.created_at),
    }


@router.post("/government/access-requests")
def government_create_access_request(
    db: Annotated[Session, Depends(get_db)],
    record_id: str,
    requester: str,
    requester_role: str,
    reason: str,
    x_government_token: Annotated[str | None, Header()] = None,
) -> dict[str, object]:
    validate_government_token(x_government_token)
    request = create_access_request(db, record_id, requester, requester_role, reason)
    db.commit()
    return {"request_id": request.request_id, "record_id": request.record_id, "status": request.status}


@router.post("/government/access-requests/{request_id}/approve")
def government_approve_access_request(
    request_id: str,
    db: Annotated[Session, Depends(get_db)],
    approved_by: str,
    x_approver_token: Annotated[str | None, Header()] = None,
) -> dict[str, object]:
    validate_approver_token(x_approver_token)
    request, token = approve_access_request(db, request_id, approved_by)
    db.commit()
    return {
        "request_id": request.request_id,
        "status": request.status,
        "one_time_access_token": token,
        "expires_at": to_wib_iso(request.access_token_expires_at),
    }


@router.get("/government/access-requests/{request_id}")
def government_get_access_request(
    request_id: str,
    db: Annotated[Session, Depends(get_db)],
    x_government_token: Annotated[str | None, Header()] = None,
) -> dict[str, object]:
    validate_government_token(x_government_token)
    return serialize_access_request(get_access_request(db, request_id))


@router.get("/government/access-requests/{request_id}/secure-original")
def government_secure_original(
    request_id: str,
    access_token: str,
    db: Annotated[Session, Depends(get_db)],
    x_government_token: Annotated[str | None, Header()] = None,
) -> Response:
    validate_government_token(x_government_token)
    data, filename = secure_original_download(db, request_id, access_token)
    db.commit()
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{Path(filename).name}"'},
    )
