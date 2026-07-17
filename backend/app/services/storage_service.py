import json
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.utils.file_utils import prevent_path_traversal
from app.utils.image_utils import cv2_image_to_bytes

settings = get_settings()


def save_redacted_image_to_operational_zone(image, original_filename: str, record_id: str) -> dict[str, str]:
    filename = f"{record_id}.jpg"
    path = settings.operational_redacted_dir / filename
    path.write_bytes(cv2_image_to_bytes(image, ".jpg"))
    return {"filename": filename, "path": str(path), "url": f"/api/files/redacted/{filename}"}


def save_operational_metadata(metadata: dict[str, Any]) -> dict[str, str]:
    record_id = str(metadata["record_id"])
    filename = f"{record_id}.json"
    path = settings.operational_metadata_dir / filename
    path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return {"filename": filename, "path": str(path)}


def get_redacted_file_path(filename: str) -> Path:
    return prevent_path_traversal(settings.operational_redacted_dir, filename)
