from typing import Any

import cv2
import numpy as np

from app.ai.class_map import normalize_class_name
from app.utils.image_utils import clamp_box_to_image


def _apply_padding(box: dict[str, float], width: int, height: int, padding_ratio: float) -> dict[str, int]:
    box_width = float(box["x2"]) - float(box["x1"])
    box_height = float(box["y2"]) - float(box["y1"])
    pad_x = box_width * padding_ratio
    pad_y = box_height * padding_ratio
    return clamp_box_to_image(
        float(box["x1"]) - pad_x,
        float(box["y1"]) - pad_y,
        float(box["x2"]) + pad_x,
        float(box["y2"]) + pad_y,
        width,
        height,
    )


def _blur_roi(roi: np.ndarray) -> np.ndarray:
    if roi.size == 0:
        return roi
    small = cv2.resize(roi, (max(1, roi.shape[1] // 8), max(1, roi.shape[0] // 8)), interpolation=cv2.INTER_LINEAR)
    enlarged = cv2.resize(small, (roi.shape[1], roi.shape[0]), interpolation=cv2.INTER_NEAREST)
    return cv2.blur(enlarged, (9, 9))


def _pixelate_roi(roi: np.ndarray) -> np.ndarray:
    if roi.size == 0:
        return roi
    small = cv2.resize(roi, (max(1, roi.shape[1] // 14), max(1, roi.shape[0] // 14)), interpolation=cv2.INTER_LINEAR)
    return cv2.resize(small, (roi.shape[1], roi.shape[0]), interpolation=cv2.INTER_NEAREST)


def redact_image(
    image: np.ndarray,
    detections: list[dict[str, Any]],
    mode: str,
    active_classes: list[str],
    label_enabled: bool = True,
    label_text: str = "REDACTED",
    box_padding_ratio: float = 0.04,
) -> dict[str, Any]:
    redacted = image.copy()
    height, width = redacted.shape[:2]
    active = set(active_classes)
    redacted_detections: list[dict[str, Any]] = []
    skipped_detections: list[dict[str, Any]] = []

    for detection in detections:
        try:
            class_name = normalize_class_name(str(detection.get("class_name", "")))
        except Exception:
            class_name = str(detection.get("class_name", "Unknown"))
        detection = {**detection, "class_name": class_name}
        if class_name not in active:
            skipped_detections.append(detection)
            continue

        padded = _apply_padding(detection["box"], width, height, box_padding_ratio)
        x1, y1, x2, y2 = padded["x1"], padded["y1"], padded["x2"], padded["y2"]
        roi = redacted[y1:y2, x1:x2]
        if mode == "black_box":
            redacted[y1:y2, x1:x2] = (0, 0, 0)
            if label_enabled and label_text:
                cv2.putText(redacted, label_text, (x1 + 6, min(y2 - 8, y1 + 24)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        elif mode == "blur":
            redacted[y1:y2, x1:x2] = _blur_roi(roi)
        elif mode == "pixelate":
            redacted[y1:y2, x1:x2] = _pixelate_roi(roi)
        redacted_detections.append({**detection, "redacted_box": padded})

    return {
        "image": redacted,
        "redacted_count": len(redacted_detections),
        "redacted_detections": redacted_detections,
        "skipped_detections": skipped_detections,
    }
