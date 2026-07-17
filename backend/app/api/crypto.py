from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.government_access_service import validate_crypto_admin_token
from app.services.vault_service import get_active_vault_key, rotate_vault_key, serialize_key

router = APIRouter(tags=["crypto"])


@router.get("/crypto/key-info")
def crypto_key_info(db: Annotated[Session, Depends(get_db)]) -> dict[str, object]:
    key = get_active_vault_key(db)
    return {
        "active_key": serialize_key(key),
        "symmetric_scheme": "AES-256-GCM",
        "asymmetric_scheme": "RSA-OAEP-SHA256",
        "dek_policy": {"scope": "per_file_upload_session", "generated_repeatedly": True, "plaintext_dek_stored": False},
        "private_key_policy": {"private_key_sent_to_user_zone": False, "rotation_strategy": "versioned key rotation"},
    }


@router.post("/crypto/rotate-vault-key")
def rotate_key(db: Annotated[Session, Depends(get_db)], x_crypto_admin_token: Annotated[str | None, Header()] = None) -> dict[str, object]:
    validate_crypto_admin_token(x_crypto_admin_token)
    key = rotate_vault_key(db)
    db.commit()
    return {"status": "rotated", "new_key": serialize_key(key), "note": "New uploads will use the latest active key."}
