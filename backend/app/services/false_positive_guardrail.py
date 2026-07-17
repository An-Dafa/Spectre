from __future__ import annotations

import re
from collections import Counter
from typing import Any

import cv2
import numpy as np

from app.ai.class_map import normalize_class_name
from app.utils.image_utils import clamp_box_to_image

GUARDRAIL_MODES = {"privacy_first", "precision_demo", "off"}

OFFICIAL_DOCUMENT_CLASSES = {"KTP", "KK", "SIM", "Paspor"}
TEXT_FIELD_CLASSES = {"Teks_Sensitif", "Resi", "Kartu_ATM"}
FACE_CLASSES = {"Wajah"}

_KTP_KEYWORDS = ("NIK", "NAMA", "TEMPAT", "LAHIR", "JENIS", "KELAMIN", "ALAMAT", "AGAMA")
_KK_KEYWORDS = ("KARTU", "KELUARGA", "NIK", "NAMA", "KEPALA", "KELUARGA", "ALAMAT")
_SIM_KEYWORDS = ("SIM", "SURAT", "IZIN", "MENGEMUDI", "INDONESIA", "NAMA", "ALAMAT")
_PASPOR_KEYWORDS = ("PASSPORT", "PASPOR", "REPUBLIC", "REPUBLIK", "INDONESIA", "IMMIGRATION")
_NIK_RE = re.compile(r"(?<!\d)(?:\d[\s\-.]?){16}(?!\d)")
_PASSPORT_RE = re.compile(r"\b[A-Z][0-9]{7,8}\b")
_SIM_NUMBER_RE = re.compile(r"(?<!\d)\d{8,14}(?!\d)")


def validate_guardrail_mode(mode: str) -> str:
    normalized = mode.strip().lower().replace("-", "_")
    if normalized not in GUARDRAIL_MODES:
        raise ValueError(f"Unknown guardrail mode: {mode}")
    return normalized


def apply_false_positive_guardrail(
    image: np.ndarray,
    detections: list[dict[str, Any]],
    guardrail_mode: str,
    profile: str,
    active_classes: list[str],
    ocr_enabled: bool = True,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Post-process YOLO candidates before redaction.

    This is a heuristic guardrail only. It does not retrain, replace, or call a new
    model. In precision_demo mode, high-risk fake or hand-drawn candidates are
    removed from the detections that go into redaction.
    """
    config = config or {}
    mode = validate_guardrail_mode(guardrail_mode)
    active_set = set(active_classes)
    if mode == "off":
        return _disabled_result(detections, profile, mode)

    ocr_allowed = bool(ocr_enabled and config.get("ocr_enabled", True))
    annotated: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    validated: list[dict[str, Any]] = []
    valid_document_boxes: list[dict[str, float]] = []
    ocr_available_any = False
    ocr_attempted_any = False

    # First pass validates document boxes so face decisions can know whether a face
    # is inside a plausible official document.
    for detection in detections:
        normalized = _normalize_detection(detection)
        class_name = normalized["class_name"]
        if class_name in OFFICIAL_DOCUMENT_CLASSES:
            analysis = _validate_official_document(image, normalized, ocr_allowed)
            ocr_available_any = ocr_available_any or analysis["ocr_available"]
            ocr_attempted_any = ocr_attempted_any or analysis["ocr_attempted"]
            enriched = _enrich_detection(normalized, analysis, mode, class_name in active_set)
            if enriched["guardrail_action"] != "skip_redaction":
                valid_document_boxes.append(normalized["box"])
            annotated.append(enriched)

    # Second pass handles text and face classes plus pass-through classes.
    for detection in detections:
        normalized = _normalize_detection(detection)
        class_name = normalized["class_name"]
        if class_name in OFFICIAL_DOCUMENT_CLASSES:
            continue
        if class_name in TEXT_FIELD_CLASSES:
            analysis = _validate_sensitive_text(image, normalized, ocr_allowed)
        elif class_name in FACE_CLASSES:
            analysis = _validate_face(image, normalized, profile, mode, valid_document_boxes)
        else:
            analysis = _pass_through_validation()

        ocr_available_any = ocr_available_any or analysis.get("ocr_available", False)
        ocr_attempted_any = ocr_attempted_any or analysis.get("ocr_attempted", False)
        annotated.append(_enrich_detection(normalized, analysis, mode, class_name in active_set))

    for detection in annotated:
        if detection["guardrail_action"] == "skip_redaction":
            rejected.append(detection)
        else:
            validated.append(detection)

    status_counts = Counter(str(item.get("validation_status", "unknown")) for item in annotated)
    return {
        "validated_detections": validated,
        "rejected_detections": rejected,
        "detections": annotated,
        "validation_summary": {
            "enabled": True,
            "mode": mode,
            "profile": profile,
            "total_detections": len(detections),
            "validated_count": len(validated),
            "rejected_count": len(rejected),
            "status_counts": dict(status_counts),
            "ocr_attempted": ocr_attempted_any,
            "ocr_available": ocr_available_any,
            "note": "False positive guardrail is post-processing only. The YOLO model is not retrained.",
        },
    }


def _disabled_result(detections: list[dict[str, Any]], profile: str, mode: str) -> dict[str, Any]:
    annotated = [
        {
            **_normalize_detection(detection),
            "validation_status": "guardrail_off",
            "validation_score": None,
            "validation_reason": ["guardrail_disabled"],
            "guardrail_action": "redact",
        }
        for detection in detections
    ]
    return {
        "validated_detections": annotated,
        "rejected_detections": [],
        "detections": annotated,
        "validation_summary": {
            "enabled": False,
            "mode": mode,
            "profile": profile,
            "total_detections": len(detections),
            "validated_count": len(annotated),
            "rejected_count": 0,
            "status_counts": {"guardrail_off": len(annotated)} if annotated else {},
            "ocr_attempted": False,
            "ocr_available": False,
            "note": "False positive guardrail is disabled.",
        },
    }


def _normalize_detection(detection: dict[str, Any]) -> dict[str, Any]:
    class_name = str(detection.get("class_name", "Unknown"))
    try:
        class_name = normalize_class_name(class_name)
    except Exception:
        class_name = "Unknown"
    return {**detection, "class_name": class_name}


def _enrich_detection(
    detection: dict[str, Any],
    analysis: dict[str, Any],
    guardrail_mode: str,
    is_active: bool,
) -> dict[str, Any]:
    status = str(analysis["validation_status"])
    should_skip = (
        is_active
        and guardrail_mode == "precision_demo"
        and status.startswith("rejected_")
    )
    if should_skip:
        action = "skip_redaction"
    elif status.startswith("rejected_") or status.startswith("suspicious_"):
        action = "redact_with_warning"
    else:
        action = "redact"
    return {
        **detection,
        "validation_status": status,
        "validation_score": analysis.get("validation_score"),
        "validation_reason": analysis.get("validation_reason", []),
        "guardrail_action": action,
        "guardrail_metrics": analysis.get("metrics", {}),
    }


def _validate_official_document(image: np.ndarray, detection: dict[str, Any], ocr_allowed: bool) -> dict[str, Any]:
    crop = _crop_detection(image, detection)
    if crop.size == 0:
        return _analysis("rejected_invalid_crop", 0.0, ["empty_crop"])

    metrics = _visual_document_metrics(crop)
    ocr = _optional_ocr(crop) if ocr_allowed else {"text": "", "available": False, "attempted": False}
    class_name = detection["class_name"]
    keyword_score = _official_keyword_score(class_name, ocr["text"])
    id_pattern_score = _id_pattern_score(class_name, ocr["text"])
    official_evidence = max(keyword_score, id_pattern_score)

    if ocr["available"]:
        authenticity_score = (
            0.24 * metrics["rectangularity_score"]
            + 0.24 * metrics["printed_text_score"]
            + 0.18 * metrics["layout_score"]
            + 0.22 * keyword_score
            + 0.12 * id_pattern_score
        )
    else:
        authenticity_score = (
            0.25 * metrics["rectangularity_score"]
            + 0.50 * metrics["printed_text_score"]
            + 0.25 * metrics["layout_score"]
        )

    handdrawn_score = _handdrawn_score(metrics, official_evidence)
    reasons: list[str] = []
    if keyword_score < 0.25:
        reasons.append("low_official_keyword_score")
    if id_pattern_score < 0.25:
        reasons.append("low_id_pattern_score")
    if metrics["printed_text_score"] < 0.25:
        reasons.append("low_printed_text_score")
    if metrics["layout_score"] < 0.30:
        reasons.append("weak_layout_evidence")
    if handdrawn_score > 0.55:
        reasons.append("high_handdrawn_score")
    if not ocr["available"]:
        reasons.append("ocr_unavailable_visual_fallback")

    strong_visual_document = (
        authenticity_score >= 0.60
        and metrics["printed_text_score"] >= 0.50
        and metrics["layout_score"] >= 0.45
    )
    handdrawn_rejection = (
        official_evidence < 0.35
        and metrics["printed_text_score"] < 0.45
        and handdrawn_score >= 0.50
    )

    if official_evidence >= 0.60 or strong_visual_document:
        status = "valid_document"
        reasons = ["official_document_evidence"]
    elif handdrawn_rejection or (handdrawn_score >= 0.58 and authenticity_score < 0.42 and official_evidence < 0.35):
        status = "rejected_suspicious_handdrawn"
    elif authenticity_score >= 0.40:
        status = "uncertain_document_kept"
        reasons.append("borderline_authenticity_score")
    else:
        status = "suspicious_low_official_evidence"
        reasons.append("low_authenticity_score")

    metrics.update(
        {
            "official_keyword_score": round(keyword_score, 3),
            "id_pattern_score": round(id_pattern_score, 3),
            "handdrawn_score": round(handdrawn_score, 3),
            "ocr_available": ocr["available"],
        }
    )
    return _analysis(
        status,
        round(float(np.clip(authenticity_score, 0.0, 1.0)), 3),
        _unique_reasons(reasons),
        metrics,
        ocr_available=ocr["available"],
        ocr_attempted=ocr["attempted"],
    )


def _validate_sensitive_text(image: np.ndarray, detection: dict[str, Any], ocr_allowed: bool) -> dict[str, Any]:
    crop = _crop_detection(image, detection)
    if crop.size == 0:
        return _analysis("rejected_invalid_crop", 0.0, ["empty_crop"])

    metrics = _visual_document_metrics(crop)
    ocr = _optional_ocr(crop) if ocr_allowed else {"text": "", "available": False, "attempted": False}
    class_name = detection["class_name"]
    id_score = _id_pattern_score(class_name, ocr["text"])

    if ocr["available"] and id_score >= 0.75:
        return _analysis(
            "valid_sensitive_text",
            id_score,
            ["sensitive_pattern_detected"],
            {**metrics, "id_pattern_score": id_score, "ocr_available": True},
            ocr_available=True,
            ocr_attempted=True,
        )
    if ocr["available"]:
        return _analysis(
            "rejected_no_sensitive_pattern",
            max(0.0, min(1.0, 0.30 * metrics["printed_text_score"])),
            ["no_sensitive_number_pattern"],
            {**metrics, "id_pattern_score": id_score, "ocr_available": True},
            ocr_available=True,
            ocr_attempted=True,
        )
    confidence = float(detection.get("confidence", 0.0) or 0.0)
    return _analysis(
        "ocr_unavailable_fallback",
        round(min(1.0, confidence), 3),
        ["ocr_unavailable_keep_by_detector_confidence"],
        {**metrics, "ocr_available": False},
        ocr_available=False,
        ocr_attempted=ocr["attempted"],
    )


def _validate_face(
    image: np.ndarray,
    detection: dict[str, Any],
    profile: str,
    guardrail_mode: str,
    valid_document_boxes: list[dict[str, float]],
) -> dict[str, Any]:
    if profile == "live_webcam" or guardrail_mode == "privacy_first":
        return _analysis("privacy_first_face_kept", 1.0, ["face_privacy_first"])

    if _center_inside_any(detection.get("box", {}), valid_document_boxes):
        return _analysis("valid_face_inside_document", 0.85, ["face_inside_valid_document"])

    crop = _crop_detection(image, detection)
    metrics = _visual_document_metrics(crop) if crop.size else {}
    skin_score = _skin_color_score(crop) if crop.size else 0.0
    handdrawn = _handdrawn_score(metrics, official_evidence=0.0) if metrics else 0.0
    confidence = float(detection.get("confidence", 0.0) or 0.0)
    if handdrawn > 0.72 and skin_score < 0.08 and confidence < 0.82:
        return _analysis(
            "rejected_suspicious_face_sketch",
            round(max(0.0, 1.0 - handdrawn), 3),
            ["high_handdrawn_score", "low_skin_texture_score", "standalone_face_candidate"],
            {**metrics, "skin_texture_score": round(skin_score, 3), "handdrawn_score": round(handdrawn, 3)},
        )
    return _analysis(
        "uncertain_face_kept",
        round(max(confidence, 0.5), 3),
        ["face_uncertain_kept_to_avoid_privacy_leak"],
        {**metrics, "skin_texture_score": round(skin_score, 3), "handdrawn_score": round(handdrawn, 3)},
    )


def _pass_through_validation() -> dict[str, Any]:
    return _analysis("pass_through", 1.0, ["class_not_targeted_by_guardrail"])


def _analysis(
    status: str,
    score: float | None,
    reasons: list[str],
    metrics: dict[str, Any] | None = None,
    ocr_available: bool = False,
    ocr_attempted: bool = False,
) -> dict[str, Any]:
    return {
        "validation_status": status,
        "validation_score": score,
        "validation_reason": _unique_reasons(reasons),
        "metrics": metrics or {},
        "ocr_available": ocr_available,
        "ocr_attempted": ocr_attempted,
    }


def _crop_detection(image: np.ndarray, detection: dict[str, Any], padding_ratio: float = 0.03) -> np.ndarray:
    height, width = image.shape[:2]
    box = detection.get("box") or {}
    x1 = float(box.get("x1", 0))
    y1 = float(box.get("y1", 0))
    x2 = float(box.get("x2", 0))
    y2 = float(box.get("y2", 0))
    pad_x = max(2.0, (x2 - x1) * padding_ratio)
    pad_y = max(2.0, (y2 - y1) * padding_ratio)
    clipped = clamp_box_to_image(x1 - pad_x, y1 - pad_y, x2 + pad_x, y2 + pad_y, width, height)
    return image[clipped["y1"] : clipped["y2"], clipped["x1"] : clipped["x2"]]


def _visual_document_metrics(crop: np.ndarray) -> dict[str, Any]:
    if crop.size == 0:
        return {
            "rectangularity_score": 0.0,
            "edge_density_score": 0.0,
            "printed_text_score": 0.0,
            "text_like_component_score": 0.0,
            "layout_score": 0.0,
            "thin_stroke_score": 0.0,
            "foreground_density": 0.0,
        }
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (min(640, gray.shape[1]), min(480, gray.shape[0])), interpolation=cv2.INTER_AREA)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(blurred, 60, 160)
    edge_density = float(np.count_nonzero(edges) / max(1, edges.size))
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    rectangularity = _rectangularity_score(edges)
    text_score, component_count = _text_component_score(otsu)
    layout_score = _layout_score(otsu)
    foreground_density = float(np.count_nonzero(otsu) / max(1, otsu.size))
    dilated = cv2.dilate(otsu, np.ones((3, 3), np.uint8), iterations=1)
    thin_stroke = 1.0 - (float(np.count_nonzero(otsu)) / max(1.0, float(np.count_nonzero(dilated))))

    return {
        "rectangularity_score": round(rectangularity, 3),
        "edge_density_score": round(_score_edge_density(edge_density), 3),
        "edge_density_ratio": round(edge_density, 4),
        "printed_text_score": round(text_score, 3),
        "text_like_component_score": round(text_score, 3),
        "text_component_count": int(component_count),
        "layout_score": round(layout_score, 3),
        "thin_stroke_score": round(float(np.clip(thin_stroke, 0.0, 1.0)), 3),
        "foreground_density": round(foreground_density, 4),
    }


def _rectangularity_score(edges: np.ndarray) -> float:
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return 0.25
    contour = max(contours, key=cv2.contourArea)
    area = float(cv2.contourArea(contour))
    x, y, w, h = cv2.boundingRect(contour)
    if w <= 0 or h <= 0:
        return 0.0
    extent = area / float(w * h)
    image_area_ratio = area / float(edges.shape[0] * edges.shape[1])
    approx = cv2.approxPolyDP(contour, 0.03 * cv2.arcLength(contour, True), True)
    corner_bonus = 1.0 if 4 <= len(approx) <= 8 else 0.55
    return float(np.clip(0.55 * extent + 0.30 * min(image_area_ratio / 0.45, 1.0) + 0.15 * corner_bonus, 0.0, 1.0))


def _text_component_score(binary_inv: np.ndarray) -> tuple[float, int]:
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary_inv, 8)
    h, w = binary_inv.shape[:2]
    area = h * w
    count = 0
    for idx in range(1, num_labels):
        x, y, bw, bh, component_area = stats[idx]
        if component_area < 5 or component_area > area * 0.08:
            continue
        if bw < 2 or bh < 2 or bw > w * 0.7 or bh > h * 0.25:
            continue
        aspect = bw / max(1, bh)
        if 0.08 <= aspect <= 18:
            count += 1
    expected = max(12.0, min(80.0, area / 5000.0))
    return float(np.clip(count / expected, 0.0, 1.0)), count


def _layout_score(binary_inv: np.ndarray) -> float:
    if binary_inv.size == 0:
        return 0.0
    row_activity = (binary_inv > 0).mean(axis=1)
    col_activity = (binary_inv > 0).mean(axis=0)
    active_rows = row_activity > 0.015
    active_cols = col_activity > 0.01
    row_segments = _count_segments(active_rows)
    col_spread = float(active_cols.mean())
    line_score = min(row_segments / 6.0, 1.0)
    spread_score = float(np.clip(col_spread / 0.55, 0.0, 1.0))
    return float(np.clip(0.65 * line_score + 0.35 * spread_score, 0.0, 1.0))


def _count_segments(mask: np.ndarray) -> int:
    if mask.size == 0:
        return 0
    transitions = np.diff(np.concatenate(([False], mask.astype(bool), [False])).astype(np.int8))
    return int(np.count_nonzero(transitions == 1))


def _score_edge_density(edge_density: float) -> float:
    if edge_density <= 0:
        return 0.0
    # Printed documents generally have measurable but not overwhelming edges.
    if edge_density <= 0.16:
        return float(np.clip(edge_density / 0.08, 0.0, 1.0))
    return float(np.clip(1.0 - ((edge_density - 0.16) / 0.18), 0.0, 1.0))


def _handdrawn_score(metrics: dict[str, Any], official_evidence: float) -> float:
    if not metrics:
        return 0.0
    sparse_foreground = 1.0 - float(np.clip(float(metrics.get("foreground_density", 0.0)) / 0.12, 0.0, 1.0))
    overdrawn_edges = max(0.0, (float(metrics.get("edge_density_ratio", 0.0)) - 0.16) / 0.20)
    score = (
        0.24 * float(metrics.get("thin_stroke_score", 0.0))
        + 0.22 * (1.0 - float(metrics.get("printed_text_score", 0.0)))
        + 0.18 * (1.0 - float(metrics.get("layout_score", 0.0)))
        + 0.18 * (1.0 - official_evidence)
        + 0.10 * sparse_foreground
        + 0.08 * float(np.clip(overdrawn_edges, 0.0, 1.0))
    )
    return float(np.clip(score, 0.0, 1.0))


def _optional_ocr(crop: np.ndarray) -> dict[str, Any]:
    if crop.size == 0:
        return {"text": "", "available": False, "attempted": False}

    # pytesseract is optional and usually lightweight if already installed.
    try:
        import pytesseract  # type: ignore

        text = pytesseract.image_to_string(crop) or ""
        return {"text": text, "available": bool(text.strip()), "attempted": True}
    except Exception:
        pass

    # Reuse the existing optional easyocr warm-up if present. Import failure is fine.
    try:
        from app.services.authenticity_service import _get_reader  # type: ignore

        reader = _get_reader()
        if reader is None:
            return {"text": "", "available": False, "attempted": True}
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        if max(gray.shape) < 700:
            scale = 700 / max(gray.shape)
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        result = reader.readtext(gray, detail=0, paragraph=True)
        text = "\n".join(str(item) for item in result)
        return {"text": text, "available": bool(text.strip()), "attempted": True}
    except Exception:
        return {"text": "", "available": False, "attempted": True}


def _official_keyword_score(class_name: str, text: str) -> float:
    normalized = _normalize_text(text)
    if not normalized:
        return 0.0
    keywords = {
        "KTP": _KTP_KEYWORDS,
        "KK": _KK_KEYWORDS,
        "SIM": _SIM_KEYWORDS,
        "Paspor": _PASPOR_KEYWORDS,
    }.get(class_name, ())
    if not keywords:
        return 0.0
    hits = sum(1 for keyword in keywords if keyword in normalized)
    return float(np.clip(hits / min(4, len(keywords)), 0.0, 1.0))


def _id_pattern_score(class_name: str, text: str) -> float:
    normalized = _normalize_text(text)
    digits = re.sub(r"\D", "", normalized)
    if class_name in {"KTP", "Teks_Sensitif"}:
        return 1.0 if _NIK_RE.search(normalized) or len(digits) >= 16 else 0.0
    if class_name == "SIM":
        return 1.0 if _SIM_NUMBER_RE.search(normalized) else 0.0
    if class_name == "Paspor":
        return 1.0 if _PASSPORT_RE.search(normalized.replace(" ", "")) or "<<" in text else 0.0
    return 0.0


def _skin_color_score(crop: np.ndarray) -> float:
    if crop.size == 0:
        return 0.0
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    lower = np.array([0, 20, 60], dtype=np.uint8)
    upper = np.array([25, 180, 255], dtype=np.uint8)
    mask1 = cv2.inRange(hsv, lower, upper)
    lower2 = np.array([160, 20, 60], dtype=np.uint8)
    upper2 = np.array([179, 180, 255], dtype=np.uint8)
    mask2 = cv2.inRange(hsv, lower2, upper2)
    mask = cv2.bitwise_or(mask1, mask2)
    return float(np.count_nonzero(mask) / max(1, mask.size))


def _center_inside_any(box: dict[str, Any], boxes: list[dict[str, float]]) -> bool:
    if not box:
        return False
    cx = (float(box.get("x1", 0)) + float(box.get("x2", 0))) / 2.0
    cy = (float(box.get("y1", 0)) + float(box.get("y2", 0))) / 2.0
    for candidate in boxes:
        if candidate["x1"] <= cx <= candidate["x2"] and candidate["y1"] <= cy <= candidate["y2"]:
            return True
    return False


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.upper().replace(":", " ").replace("-", " ")).strip()


def _unique_reasons(reasons: list[str]) -> list[str]:
    unique: list[str] = []
    for reason in reasons:
        if reason and reason not in unique:
            unique.append(reason)
    return unique
