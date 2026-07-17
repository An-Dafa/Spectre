from __future__ import annotations

import re
import time
import uuid
from typing import Any


TRACK_RULES = {
    "enterprise_kyc": ["id_card", "face", "nik"],
    "liveshield": ["id_card", "shipping_label", "qr_code", "face"],
    "screen_shield": ["nik", "bank_account", "phone", "salary"],
}

TRACK_STORAGE = {
    "enterprise_kyc": {
        "operational_zone_persisted": True,
        "sovereign_vault_persisted": True,
        "audit_log_persisted": True,
    },
    "liveshield": {
        "operational_zone_persisted": False,
        "sovereign_vault_persisted": False,
        "audit_log_persisted": False,
    },
    "screen_shield": {
        "operational_zone_persisted": False,
        "sovereign_vault_persisted": False,
        "audit_log_persisted": False,
    },
}

TEXT_PATTERNS = {
    "nik": re.compile(r"\b\d{16}\b"),
    "bank_account": re.compile(r"\b\d{10,15}\b"),
    "phone": re.compile(r"(?:\+62|62|0)8\d{8,11}\b"),
    "salary": re.compile(r"\b(?:Rp\s*)?\d{1,3}(?:[.,]\d{3}){2,}\b", re.IGNORECASE),
}


def supported_flow() -> dict[str, Any]:
    return {
        "app": "Spectre",
        "role": "visual privacy middleware",
        "journey": ["source_unsafe", "spectre_edge_engine", "destination_safe"],
        "tracks": {
            "enterprise_kyc": "Static document KYC redaction before company storage.",
            "liveshield": "Ephemeral webcam/frame redaction before public broadcast.",
            "screen_shield": "Ephemeral screen-share text redaction before meeting transport.",
        },
    }


def process_visual(track: str, enabled_rules: list[str] | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    rules = _rules_for(track, enabled_rules)
    detections = [_mock_detection(rule, index) for index, rule in enumerate(rules)]
    record_id = f"rec_{uuid.uuid4().hex}" if track == "enterprise_kyc" else None

    return {
        "track": track,
        "source": {"zone": "source_unsafe", "raw_data_received": True},
        "middleware": {
            "zone": "spectre_edge_engine",
            "rules": rules,
            "detections": detections,
            "redaction": {"mode": "blur" if track != "enterprise_kyc" else "black_box", "redacted_count": len(detections)},
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        },
        "destination": {
            "zone": "destination_safe",
            "receives_raw_data": False,
            "receives_redacted_data": True,
            "record_id": record_id,
            "storage_policy": TRACK_STORAGE[track],
        },
        "audit": _audit(track, record_id, len(detections)),
    }


def process_screen_text(text: str, enabled_rules: list[str] | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    rules = _rules_for("screen_shield", enabled_rules)
    redacted = text
    detections: list[dict[str, Any]] = []

    for rule in rules:
        pattern = TEXT_PATTERNS[rule]
        for match in pattern.finditer(redacted):
            detections.append({"class_name": rule, "start": match.start(), "end": match.end()})
        redacted = pattern.sub("[REDACTED]", redacted)

    return {
        "track": "screen_shield",
        "source": {"zone": "source_unsafe", "raw_text_received": True},
        "middleware": {
            "zone": "spectre_edge_engine",
            "rules": rules,
            "detections": detections,
            "redaction": {"mode": "text_blackout", "redacted_count": len(detections)},
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        },
        "destination": {
            "zone": "destination_safe",
            "receives_raw_data": False,
            "redacted_text": redacted,
            "storage_policy": TRACK_STORAGE["screen_shield"],
        },
        "audit": _audit("screen_shield", None, len(detections)),
    }


def _rules_for(track: str, enabled_rules: list[str] | None) -> list[str]:
    if track not in TRACK_RULES:
        raise ValueError(f"unsupported track: {track}")
    allowed = TRACK_RULES[track]
    if not enabled_rules:
        return allowed
    rules = [rule for rule in enabled_rules if rule in allowed]
    if not rules:
        raise ValueError(f"no valid rules for track: {track}")
    return rules


def _mock_detection(rule: str, index: int) -> dict[str, Any]:
    offset = 24 * index
    return {
        "class_name": rule,
        "confidence": 0.91,
        "box": {"x1": 40 + offset, "y1": 52 + offset, "x2": 180 + offset, "y2": 132 + offset},
    }


def _audit(track: str, record_id: str | None, detection_count: int) -> dict[str, Any]:
    return {
        "event": f"{track}_middleware_pass",
        "record_id": record_id,
        "detection_count": detection_count,
        "raw_data_left_source": False,
    }
