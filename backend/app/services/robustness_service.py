from typing import Any

import cv2
import numpy as np


def _rotate(image: np.ndarray, angle: int) -> np.ndarray:
    if angle == 0:
        return image
    if angle == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    if angle == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    if angle == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return image


def _map_box(box: dict[str, float], angle: int, width: int, height: int) -> dict[str, float]:
    x1, y1, x2, y2 = box["x1"], box["y1"], box["x2"], box["y2"]
    if angle == 0:
        return box
    if angle == 180:
        return {"x1": width - x2, "y1": height - y2, "x2": width - x1, "y2": height - y1}
    if angle == 90:
        return {"x1": y1, "y1": height - x2, "x2": y2, "y2": height - x1}
    if angle == 270:
        return {"x1": width - y2, "y1": x1, "x2": width - y1, "y2": x2}
    return box


def _iou(a: dict[str, float], b: dict[str, float]) -> float:
    x1, y1 = max(a["x1"], b["x1"]), max(a["y1"], b["y1"])
    x2, y2 = min(a["x2"], b["x2"]), min(a["y2"], b["y2"])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = max(0, a["x2"] - a["x1"]) * max(0, a["y2"] - a["y1"])
    area_b = max(0, b["x2"] - b["x1"]) * max(0, b["y2"] - b["y1"])
    denom = area_a + area_b - inter
    return inter / denom if denom else 0.0


def _nms(detections: list[dict[str, Any]], threshold: float) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for det in sorted(detections, key=lambda item: item.get("confidence", 0), reverse=True):
        duplicate = any(det["class_name"] == kept_det["class_name"] and _iou(det["box"], kept_det["box"]) >= threshold for kept_det in kept)
        if not duplicate:
            kept.append(det)
    return kept


def robust_predict_with_tta(detector, image: np.ndarray, confidence_threshold: float | dict[str, float], tta_angles: str = "0,180", iou_threshold: float = 0.55) -> dict[str, Any]:
    height, width = image.shape[:2]
    angles = []
    for item in tta_angles.split(","):
        try:
            angle = int(item.strip())
        except ValueError:
            continue
        if angle in {0, 90, 180, 270} and angle not in angles:
            angles.append(angle)
    if not angles:
        angles = [0, 180]
    all_detections: list[dict[str, Any]] = []
    total_latency = 0.0
    device = detector.device
    for angle in angles:
        prediction = detector.predict(_rotate(image, angle), confidence_threshold)
        total_latency += float(prediction.get("latency_ms", 0))
        device = str(prediction.get("device", device))
        for detection in prediction.get("detections", []):
            all_detections.append({**detection, "box": _map_box(detection["box"], angle, width, height), "tta_angle": angle})
    merged = _nms(all_detections, iou_threshold)
    return {
        "device": device,
        "latency_ms": round(total_latency, 2),
        "detection_count": len(merged),
        "detections": merged,
        "robustness": {
            "document_tta_enabled": True,
            "tta_angles": angles,
            "nms_iou_threshold": iou_threshold,
            "note": "Document TTA helps upside-down documents without retraining.",
        },
    }
