from fastapi import APIRouter

from app.ai.class_map import CANONICAL_CLASSES, serialize_classes
from app.core.config import DEFAULT_CLASS_CONFIDENCE, get_settings
from app.core.redaction_policy import ALLOWED_REDACTION_MODES, serialize_redaction_profiles
from app.db.database import get_database_path
from app.ai.runtime import detector

router = APIRouter(tags=["system"])
settings = get_settings()


@router.get("/health")
def health() -> dict[str, object]:
    database_path = get_database_path()
    return {
        "status": "ok",
        "app": settings.app_name,
        "model_loaded": detector.loaded,
        "model_loading": detector.loading,
        "model_exists": detector.model_exists,
        "device": settings.model_device,
        "operational_zone": "ready" if settings.operational_redacted_dir.exists() else "missing",
        "sovereign_vault": "ready" if settings.vault_encrypted_original_dir.exists() else "missing",
        "database": "ready" if database_path and database_path.exists() else "pending_startup",
    }


@router.get("/model-info")
def model_info() -> dict[str, object]:
    effective_model_path = settings.effective_model_path
    is_yolo26n = effective_model_path.name == "model_deteksi_yolo26n.pt"
    return {
        "model_path": str(settings.model_path),
        "effective_model_path": str(effective_model_path),
        "model_filename": effective_model_path.name,
        "model_exists": detector.model_exists,
        "model_loaded": detector.loaded,
        "model_loading": detector.loading,
        "load_error": detector.load_error,
        "device": settings.model_device,
        "default_confidence": settings.model_confidence,
        "classes": CANONICAL_CLASSES,
        "model_loader": "ultralytics.YOLO",
        "yolo26n_ready": is_yolo26n and detector.loaded,
        "model_variant": "YOLO26n" if is_yolo26n else "legacy",
    }


@router.get("/redaction-config")
def get_redaction_config() -> dict[str, object]:
    return {
        "profiles": serialize_redaction_profiles(),
        "allowed_modes": ALLOWED_REDACTION_MODES,
        "classes": serialize_classes(),
        "canonical_classes": CANONICAL_CLASSES,
        "default_class_confidence": DEFAULT_CLASS_CONFIDENCE,
    }


@router.get("/flow")
def flow() -> dict[str, object]:
    return {
        "app": settings.app_name,
        "role": "visual privacy middleware",
        "journey": ["source_unsafe", "spectre_edge_engine", "destination_safe"],
        "tracks": {
            "enterprise_kyc": {
                "source": "third-party registration or KYC upload",
                "middleware": "local document detection, redaction, vault encryption, audit",
                "destination": "operational server receives redacted image only",
                "endpoint": "/api/redact",
            },
            "liveshield": {
                "source": "raw webcam or live frame",
                "middleware": "ephemeral frame detection and redaction",
                "destination": "public broadcast receives redacted frame only",
                "endpoints": ["/api/live/redact-frame", "/api/live/ws"],
            },
            "screen_shield": {
                "source": "screen-share text or OCR output",
                "middleware": "regex/text redaction for sensitive identifiers",
                "destination": "meeting transport receives redacted text only",
                "endpoints": ["/api/screen/redact", "/api/screen/ocr-redact"],
            },
        },
        "bridge_layout_endpoint": "/api/bridge/layout",
    }


