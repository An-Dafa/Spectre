
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]

# Per-class confidence defaults, dikalibrasi dari kurva F1/PR per kelas
# (model.val() pada model_deteksi). Strong classes (KTP/KK/SIM/Paspor/Teks_Sensitif,
# AP>0.99) punya plateau F1 lebar -> threshold rendah-sedang tanpa buang recall.
# Wajah (AP 0.970) kelas lemah + privacy-critical -> paling rendah demi recall.
# Plat_Nomor (AP 0.968) F1 jatuh di conf<0.15 (banyak FP) -> floor dijaga.
# Untuk redaksi PII, bias ke recall tinggi (false negative = bocor data).
DEFAULT_CLASS_CONFIDENCE: Dict[str, float] = {
    "KTP": 0.35,
    "KK": 0.35,
    "SIM": 0.35,
    "Paspor": 0.35,
    "Teks_Sensitif": 0.30,
    "Wajah": 0.25,
    "Plat_Nomor": 0.35,
    "Resi": 0.30,
}


class Settings(BaseSettings):
    app_name: str = "Spectre"
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    model_path: Path = Path("./models/model_deteksi.pt")
    model_confidence: float = Field(default=0.35, ge=0.01, le=0.99)
    model_class_confidence: Dict[str, float] = Field(default_factory=lambda: dict(DEFAULT_CLASS_CONFIDENCE))
    model_device: str = "cpu"

    database_url: str = "sqlite:///./storage/spectre.db"

    government_token: str = "spectre-government-demo-token"
    approver_token: str = "spectre-approver-demo-token"
    crypto_admin_token: str = "spectre-crypto-admin-demo-token"

    runtime_policy_path: Path = Path("./storage/config/runtime_policy.json")
    cors_origins: str = "https://localhost:5173,https://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("model_path", "runtime_policy_path", mode="after")
    @classmethod
    def resolve_backend_relative_path(cls, value: Path) -> Path:
        if value.is_absolute():
            return value
        return BACKEND_ROOT / value

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def storage_root(self) -> Path:
        return BACKEND_ROOT / "storage"

    @property
    def operational_redacted_dir(self) -> Path:
        return self.storage_root / "operational_zone" / "redacted"

    @property
    def operational_metadata_dir(self) -> Path:
        return self.storage_root / "operational_zone" / "metadata"

    @property
    def vault_encrypted_original_dir(self) -> Path:
        return self.storage_root / "sovereign_vault" / "encrypted_original"

    @property
    def vault_keys_dir(self) -> Path:
        return self.storage_root / "sovereign_vault" / "keys_simulated"

    @property
    def runtime_config_dir(self) -> Path:
        return self.storage_root / "config"

    @property
    def audit_dir(self) -> Path:
        return self.storage_root / "audit"

    @property
    def effective_model_path(self) -> Path:
        if self.model_path.exists():
            return self.model_path
        fallback = BACKEND_ROOT / "models" / "model_deteksi.pt"
        return fallback if fallback.exists() else self.model_path

    @property
    def model_exists(self) -> bool:
        return self.effective_model_path.exists()


def ensure_storage_directories(settings: Settings) -> None:
    directories = [
        BACKEND_ROOT / "models",
        settings.operational_redacted_dir,
        settings.operational_metadata_dir,
        settings.vault_encrypted_original_dir,
        settings.vault_keys_dir,
        settings.runtime_config_dir,
        settings.audit_dir,
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    ensure_storage_directories(settings)
    return settings
