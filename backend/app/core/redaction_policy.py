from dataclasses import dataclass

from fastapi import HTTPException, status

from app.ai.class_map import CANONICAL_CLASSES, normalize_class_name, parse_class_csv

ALLOWED_REDACTION_MODES = ["black_box", "blur", "pixelate"]


@dataclass(frozen=True)
class RedactionRule:
    profile: str
    mode: str
    label_enabled: bool
    label_text: str
    active_classes: tuple[str, ...]


_REDACTION_PROFILES = {
    "admin": RedactionRule(
        profile="admin",
        mode="black_box",
        label_enabled=True,
        label_text="REDACTED",
        active_classes=tuple(CANONICAL_CLASSES),
    ),
    "government": RedactionRule(
        profile="government",
        mode="black_box",
        label_enabled=True,
        label_text="REDACTED",
        active_classes=tuple(CANONICAL_CLASSES),
    ),
    "live_webcam": RedactionRule(
        profile="live_webcam",
        mode="blur",
        label_enabled=False,
        label_text="",
        active_classes=("Wajah", "KTP", "KK", "SIM", "Kartu_ATM", "Resi"),
    ),
}


def is_allowed_redaction_mode(mode: str) -> bool:
    return mode in ALLOWED_REDACTION_MODES


def validate_redaction_mode(mode: str) -> str:
    normalized = mode.strip().lower().replace("-", "_")
    if not is_allowed_redaction_mode(normalized):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown redaction mode: {mode}",
        )
    return normalized


def get_redaction_rule(profile: str) -> RedactionRule:
    normalized = profile.strip().lower().replace("-", "_")
    if normalized not in _REDACTION_PROFILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown redaction profile: {profile}",
        )
    return _REDACTION_PROFILES[normalized]


def build_active_classes(
    default_classes: list[str] | tuple[str, ...],
    active_classes_override: str | list[str] | None = None,
    disabled_classes: str | list[str] | None = None,
) -> list[str]:
    if isinstance(active_classes_override, str):
        active_classes = parse_class_csv(active_classes_override)
    elif active_classes_override:
        active_classes = [normalize_class_name(item) for item in active_classes_override]
    else:
        active_classes = [normalize_class_name(item) for item in default_classes]

    if isinstance(disabled_classes, str):
        disabled = set(parse_class_csv(disabled_classes))
    elif disabled_classes:
        disabled = {normalize_class_name(item) for item in disabled_classes}
    else:
        disabled = set()

    return [class_name for class_name in active_classes if class_name not in disabled]


def serialize_redaction_rule(rule: RedactionRule) -> dict[str, object]:
    return {
        "profile": rule.profile,
        "mode": rule.mode,
        "label_enabled": rule.label_enabled,
        "label_text": rule.label_text,
        "active_classes": list(rule.active_classes),
    }


def serialize_redaction_profiles() -> dict[str, dict[str, object]]:
    return {name: serialize_redaction_rule(rule) for name, rule in _REDACTION_PROFILES.items()}
