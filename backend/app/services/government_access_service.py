import secrets
from datetime import timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import GovernmentAccessRequest, utc_now
from app.db.repositories import GovernmentAccessRequestRepository, SovereignVaultRepository
from app.services.audit_service import create_audit_log
from app.services.vault_service import decrypt_original_from_vault
from app.utils.hash_utils import sha256_bytes
from app.utils.time_utils import to_wib_iso

settings = get_settings()


def validate_government_token(token: str | None) -> None:
    if token != settings.government_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid government token")


def validate_approver_token(token: str | None) -> None:
    if token != settings.approver_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid approver token")


def validate_crypto_admin_token(token: str | None) -> None:
    if token != settings.crypto_admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid crypto admin token")


def create_access_request(db: Session, record_id: str, requester: str, requester_role: str, reason: str) -> GovernmentAccessRequest:
    if not SovereignVaultRepository(db).get_by_record_id(record_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vault record not found")
    request = GovernmentAccessRequest(
        request_id=f"gar_{secrets.token_urlsafe(12)}",
        record_id=record_id,
        requester=requester,
        requester_role=requester_role,
        reason=reason,
        status="pending",
    )
    GovernmentAccessRequestRepository(db).add(request)
    create_audit_log(db, record_id, "Government Access API", "access_request_created", requester, "Government access request created", {"request_id": request.request_id, "requester_role": requester_role})
    return request


def approve_access_request(db: Session, request_id: str, approved_by: str) -> tuple[GovernmentAccessRequest, str]:
    request = GovernmentAccessRequestRepository(db).get_by_request_id(request_id)
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access request not found")
    if request.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Request is {request.status}")
    token = secrets.token_urlsafe(32)
    request.status = "approved"
    request.approved_by = approved_by
    request.approved_at = utc_now()
    request.access_token_hash = sha256_bytes(token.encode("utf-8"))
    request.access_token_expires_at = utc_now() + timedelta(minutes=15)
    create_audit_log(db, request.record_id, "Government Access API", "access_request_approved", approved_by, "Government access request approved", {"request_id": request.request_id, "expires_at": to_wib_iso(request.access_token_expires_at)})
    return request, token


def get_access_request(db: Session, request_id: str) -> GovernmentAccessRequest:
    request = GovernmentAccessRequestRepository(db).get_by_request_id(request_id)
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access request not found")
    return request


def serialize_access_request(request: GovernmentAccessRequest) -> dict[str, Any]:
    return {
        "request_id": request.request_id,
        "record_id": request.record_id,
        "requester": request.requester,
        "requester_role": request.requester_role,
        "reason": request.reason,
        "status": request.status,
        "approved_by": request.approved_by,
        "created_at": to_wib_iso(request.created_at),
        "approved_at": to_wib_iso(request.approved_at),
        "access_token_expires_at": to_wib_iso(request.access_token_expires_at),
        "access_token_used_at": to_wib_iso(request.access_token_used_at),
    }


def secure_original_download(db: Session, request_id: str, access_token: str) -> tuple[bytes, str]:
    request = get_access_request(db, request_id)
    if request.status != "approved":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Request is not approved")
    if request.access_token_used_at:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access token already used")
    if not request.access_token_expires_at or request.access_token_expires_at < utc_now():
        request.status = "expired"
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access token expired")
    if sha256_bytes(access_token.encode("utf-8")) != request.access_token_hash:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid access token")
    vault_record = SovereignVaultRepository(db).get_by_record_id(request.record_id)
    if not vault_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vault record not found")
    data = decrypt_original_from_vault(vault_record, db)
    request.access_token_used_at = utc_now()
    request.status = "used"
    create_audit_log(db, request.record_id, "Government Access API / Vault Gateway", "authorized_original_decryption", request.requester, "Authorized original decryption", {"request_id": request.request_id, "approved_by": request.approved_by})
    return data, vault_record.original_filename
