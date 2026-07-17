import json
from typing import Any

from fastapi import HTTPException, status

from app.ai.class_map import CANONICAL_CLASSES, normalize_class_name
from app.core.config import DEFAULT_CLASS_CONFIDENCE, get_settings
from app.core.redaction_policy import get_redaction_rule, validate_redaction_mode
from app.utils.time_utils import now_wib_iso

settings = get_settings()
ALLOWED_POLICY_KEYS = {"policy_name", "confidence_threshold", "class_confidence_threshold", "profile", "redaction_mode", "active_classes", "disabled_classes", "label_text", "injection_note", "updated_at"}


def default_runtime_policy() -> dict[str, Any]:
    return {
        "policy_name": "Default Government Policy",
        "confidence_threshold": 0.35,
        "class_confidence_threshold": dict(DEFAULT_CLASS_CONFIDENCE),
        "profile": "government",
        "redaction_mode": "black_box",
        "active_classes": CANONICAL_CLASSES,
        "disabled_classes": [],
        "label_text": "REDACTED",
        "injection_note": "Default policy",
        "updated_at": now_wib_iso(),
    }


def _validate_class_confidence(value: Any) -> dict[str, float]:
    if value is None:
        return dict(DEFAULT_CLASS_CONFIDENCE)
    if not isinstance(value, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="class_confidence_threshold must be an object")
    resolved = dict(DEFAULT_CLASS_CONFIDENCE)
    for raw_class, raw_conf in value.items():
        class_name = normalize_class_name(str(raw_class))
        try:
            conf = float(raw_conf)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"class_confidence_threshold[{class_name}] must be a number",
            ) from exc
        if conf < 0.01 or conf > 0.99:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"class_confidence_threshold[{class_name}] must be between 0.01 and 0.99",
            )
        resolved[class_name] = conf
    return resolved


def resolve_class_confidence(policy: dict[str, Any], scalar_fallback: float) -> dict[str, float]:
    """Bangun map threshold per kelas: override runtime policy > default config > skalar global."""
    overrides = policy.get("class_confidence_threshold") or {}
    return {
        class_name: float(overrides.get(class_name, DEFAULT_CLASS_CONFIDENCE.get(class_name, scalar_fallback)))
        for class_name in CANONICAL_CLASSES
    }


def _validate_policy(payload: dict[str, Any]) -> dict[str, Any]:
    unknown = set(payload) - ALLOWED_POLICY_KEYS
    if unknown:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown policy keys: {sorted(unknown)}")
    policy = {**default_runtime_policy(), **payload}
    confidence = float(policy["confidence_threshold"])
    if confidence < 0.01 or confidence > 0.99:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="confidence_threshold must be between 0.01 and 0.99")
    get_redaction_rule(str(policy["profile"]))
    policy["redaction_mode"] = validate_redaction_mode(str(policy["redaction_mode"]))
    policy["confidence_threshold"] = confidence
    policy["class_confidence_threshold"] = _validate_class_confidence(policy.get("class_confidence_threshold"))
    policy["active_classes"] = [normalize_class_name(str(item)) for item in policy.get("active_classes") or []]
    policy["disabled_classes"] = [normalize_class_name(str(item)) for item in policy.get("disabled_classes") or []]
    policy["updated_at"] = now_wib_iso()
    return policy


def load_runtime_policy() -> dict[str, Any]:
    path = settings.runtime_policy_path
    if not path.exists():
        return reset_runtime_policy()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return reset_runtime_policy()
    return _validate_policy(data)


def update_runtime_policy(payload: dict[str, Any]) -> dict[str, Any]:
    policy = _validate_policy(payload)
    settings.runtime_policy_path.parent.mkdir(parents=True, exist_ok=True)
    settings.runtime_policy_path.write_text(json.dumps(policy, indent=2, ensure_ascii=False), encoding="utf-8")
    return policy


def reset_runtime_policy() -> dict[str, Any]:
    policy = default_runtime_policy()
    settings.runtime_policy_path.parent.mkdir(parents=True, exist_ok=True)
    settings.runtime_policy_path.write_text(json.dumps(policy, indent=2, ensure_ascii=False), encoding="utf-8")
    return policy
