import base64
import json
import os
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import SovereignVaultRecord, VaultKey, utc_now
from app.db.repositories import SovereignVaultRepository, VaultKeyRepository
from app.services.audit_service import create_audit_log
from app.utils.hash_utils import sha256_bytes
from app.utils.time_utils import now_wib_iso, to_wib_iso

settings = get_settings()
ALGORITHM = "AES-256-GCM + RSA-OAEP-SHA256"


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.b64decode(value.encode("ascii"))


def _fingerprint(public_pem: bytes) -> str:
    return sha256_bytes(public_pem)[:32]


@lru_cache(maxsize=16)
def _load_public_key(path: str):
    return serialization.load_pem_public_key(Path(path).read_bytes())


@lru_cache(maxsize=16)
def _load_private_key(path: str):
    return serialization.load_pem_private_key(Path(path).read_bytes(), password=None)


def ensure_active_vault_key(db: Session) -> VaultKey:
    repo = VaultKeyRepository(db)
    active = repo.get_active()
    if active:
        return active
    key = rotate_vault_key(db, actor="system", audit_event="vault_key_initialized")
    return key


def get_active_vault_key(db: Session) -> VaultKey:
    key = VaultKeyRepository(db).get_active()
    if not key:
        key = ensure_active_vault_key(db)
    return key


def rotate_vault_key(db: Session, actor: str = "crypto-admin", audit_event: str = "vault_key_rotated") -> VaultKey:
    repo = VaultKeyRepository(db)
    for key in db.query(VaultKey).filter(VaultKey.is_active.is_(True)).all():
        key.is_active = False
        key.retired_at = utc_now()

    version = repo.get_latest_version() + 1
    key_id = f"spectre-vault-key-v{version}-{uuid.uuid4().hex[:8]}"
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    private_pem = private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    public_pem = public_key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    private_path = settings.vault_keys_dir / f"{key_id}.private.pem"
    public_path = settings.vault_keys_dir / f"{key_id}.public.pem"
    private_path.write_bytes(private_pem)
    public_path.write_bytes(public_pem)
    key = VaultKey(
        key_id=key_id,
        key_version=version,
        public_key_path=str(public_path),
        private_key_path=str(private_path),
        public_key_fingerprint=_fingerprint(public_pem),
        is_active=True,
    )
    repo.add(key)
    create_audit_log(db, None, "Sovereign Vault", audit_event, actor, f"Vault key version {version} active", {"key_id": key_id, "key_version": version})
    return key


def serialize_key(key: VaultKey) -> dict[str, Any]:
    return {
        "key_id": key.key_id,
        "key_version": key.key_version,
        "public_key_fingerprint": key.public_key_fingerprint,
        "created_at": to_wib_iso(key.created_at),
    }


def encrypt_original_for_vault(db: Session, record_id: str, upload_session_id: str, original_filename: str, original_bytes: bytes) -> tuple[SovereignVaultRecord, dict[str, Any]]:
    key = get_active_vault_key(db)
    dek = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)
    ciphertext = AESGCM(dek).encrypt(nonce, original_bytes, record_id.encode("utf-8"))
    public_key = _load_public_key(key.public_key_path)
    wrapped_dek = public_key.encrypt(dek, padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    bundle = {
        "record_id": record_id,
        "upload_session_id": upload_session_id,
        "original_filename": original_filename,
        "encryption_algorithm": ALGORITHM,
        "key_id": key.key_id,
        "key_version": key.key_version,
        "nonce_b64": _b64(nonce),
        "wrapped_dek_b64": _b64(wrapped_dek),
        "ciphertext_b64": _b64(ciphertext),
        "original_sha256": sha256_bytes(original_bytes),
        "ciphertext_sha256": sha256_bytes(ciphertext),
        "created_at": now_wib_iso(),
    }
    path = settings.vault_encrypted_original_dir / f"{record_id}.json"
    path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    record = SovereignVaultRecord(
        record_id=record_id,
        upload_session_id=upload_session_id,
        original_filename=original_filename,
        encrypted_bundle_path=str(path),
        encryption_algorithm=ALGORITHM,
        key_id=key.key_id,
        key_version=key.key_version,
        nonce_b64=bundle["nonce_b64"],
        wrapped_dek_b64=bundle["wrapped_dek_b64"],
        original_sha256=bundle["original_sha256"],
        ciphertext_sha256=bundle["ciphertext_sha256"],
        plaintext_stored=False,
    )
    SovereignVaultRepository(db).add(record)
    return record, bundle


def decrypt_original_from_vault(record: SovereignVaultRecord, db: Session) -> bytes:
    key = VaultKeyRepository(db).get_by_version(record.key_version)
    if not key:
        raise ValueError("Vault key version not found")
    bundle = json.loads(Path(record.encrypted_bundle_path).read_text(encoding="utf-8"))
    private_key = _load_private_key(key.private_key_path)
    dek = private_key.decrypt(_unb64(bundle["wrapped_dek_b64"]), padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    plaintext = AESGCM(dek).decrypt(_unb64(bundle["nonce_b64"]), _unb64(bundle["ciphertext_b64"]), record.record_id.encode("utf-8"))
    return plaintext
