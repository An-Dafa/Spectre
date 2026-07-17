import base64
import re
import time
from functools import lru_cache
from typing import Any

import cv2
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field

from app.utils.image_utils import cv2_image_to_bytes, get_image_shape, read_image_bytes_to_cv2, validate_image_filename

router = APIRouter(tags=["screen-shield"])

TEXT_PATTERNS = {
    "nik": re.compile(r"\b\d{16}\b"),
    "bank_account": re.compile(r"\b\d{10,15}\b"),
    "phone": re.compile(r"(?:\+62|62|0)8\d{8,11}\b"),
    "salary": re.compile(r"\b(?:Rp\s*)?\d{1,3}(?:[.,]\d{3}){2,}\b", re.IGNORECASE),
}


class ScreenRedactionRequest(BaseModel):
    text: str
    active_rules: list[str] | None = Field(default=None)


@router.post("/screen/redact")
def redact_screen_text(request: ScreenRedactionRequest) -> dict[str, Any]:
    started = time.perf_counter()
    rules = request.active_rules or list(TEXT_PATTERNS)
    unknown = [rule for rule in rules if rule not in TEXT_PATTERNS]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown screen redaction rule(s): {', '.join(unknown)}",
        )

    redacted = request.text
    detections: list[dict[str, Any]] = []
    for rule in rules:
        pattern = TEXT_PATTERNS[rule]
        detections.extend({"class_name": rule, "start": match.start(), "end": match.end()} for match in pattern.finditer(redacted))
        redacted = pattern.sub("[REDACTED]", redacted)

    return {
        "profile": "screen_shield",
        "active_rules": rules,
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "detection_count": len(detections),
        "redacted_count": len(detections),
        "detections": detections,
        "redacted_text": redacted,
        "storage_policy": {
            "operational_zone_persisted": False,
            "sovereign_vault_persisted": False,
            "audit_log_per_frame": False,
            "note": "Screen-share text is processed ephemerally before the destination receives it.",
        },
    }


@router.post("/screen/ocr-redact")
async def redact_screen_image(
    file: UploadFile = File(...),
    active_rules: str | None = Query(default=None, description="Comma-separated rules: nik,bank_account,phone,salary"),
    return_image: bool = Query(default=True),
) -> dict[str, Any]:
    started = time.perf_counter()
    validate_image_filename(file.filename or "screen.png")
    image_bytes = await file.read()
    image = read_image_bytes_to_cv2(image_bytes)
    rules = [item.strip() for item in active_rules.split(",") if item.strip()] if active_rules else list(TEXT_PATTERNS)
    unknown = [rule for rule in rules if rule not in TEXT_PATTERNS]
    if unknown:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown screen redaction rule(s): {', '.join(unknown)}")

    ocr_items = _read_text_regions(image)
    detections: list[dict[str, Any]] = []
    redacted = image.copy()
    for item in ocr_items:
        matched_rules = _matching_rules(item["text"], rules)
        if not matched_rules:
            continue
        x1, y1, x2, y2 = item["box"].values()
        cv2.rectangle(redacted, (x1, y1), (x2, y2), (0, 0, 0), thickness=-1)
        detections.append(
            {
                "confidence": item["confidence"],
                "box": item["box"],
                "matched_rules": matched_rules,
            }
        )

    response = {
        "profile": "screen_shield_ocr",
        "active_rules": rules,
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "image_shape": get_image_shape(image),
        "ocr_count": len(ocr_items),
        "detection_count": len(detections),
        "redacted_count": len(detections),
        "detections": detections,
        "storage_policy": {
            "operational_zone_persisted": False,
            "sovereign_vault_persisted": False,
            "audit_log_per_frame": False,
            "note": "Screen-share images are OCR-redacted ephemerally and are not stored.",
        },
    }
    if return_image:
        response["mime_type"] = "image/jpeg"
        response["redacted_image_base64"] = base64.b64encode(cv2_image_to_bytes(redacted, ".jpg")).decode("ascii")
    return response


def _matching_rules(text: str, rules: list[str]) -> list[str]:
    return [rule for rule in rules if TEXT_PATTERNS[rule].search(text)]


def _read_text_regions(image) -> list[dict[str, Any]]:
    try:
        import easyocr
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="EasyOCR is not installed or unavailable") from exc

    try:
        results = _ocr_reader().readtext(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"OCR engine unavailable: {exc}") from exc

    items: list[dict[str, Any]] = []
    for box_points, text, confidence in results:
        xs = [int(point[0]) for point in box_points]
        ys = [int(point[1]) for point in box_points]
        items.append(
            {
                "text": str(text),
                "confidence": float(confidence),
                "box": {"x1": max(0, min(xs)), "y1": max(0, min(ys)), "x2": max(xs), "y2": max(ys)},
            }
        )
    return items


@lru_cache(maxsize=1)
def _ocr_reader():
    import easyocr

    return easyocr.Reader(["id", "en"], gpu=False, verbose=False)
