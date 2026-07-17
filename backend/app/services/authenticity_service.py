"""KTP authenticity heuristics — detect paper/printout copies without retraining the YOLO model.

This is post-processing only. It runs on the KTP crop already located by the detector
and combines several signals into a single ``fake_likelihood`` score:

  * moire     — FFT halftone/moire energy, high on photographed printouts/photocopies
  * sharpness — Laplacian variance, used as a quality gate (too blurry => inconclusive)
  * glare     — specular highlight presence, a weak "genuine PVC" indicator
  * nik       — OCR the crop, validate the 16-digit NIK structure (province/date/sequence)

None of these are a guarantee. The result is a likelihood indicator, not a verdict of law.
"""

from __future__ import annotations

import re
import threading
from typing import Any

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Scoring weights / thresholds (tunable — no model retraining involved).
# ---------------------------------------------------------------------------
_W_MOIRE = 0.45
_W_NIK = 0.35
_W_GLARE = 0.20

_VERDICT_GENUINE_MAX = 0.35
_VERDICT_FAKE_MIN = 0.60

# A crop smaller than this (in pixels, either side) is treated as inconclusive.
_MIN_CROP_SIDE = 48
# Below this Laplacian variance the crop is too blurry to judge reliably.
_MIN_SHARPNESS = 12.0

# Indonesian BPS province codes (first two NIK digits). Codes outside this set
# are flagged lightly rather than hard-failed, since new provinces appear over time.
_VALID_PROVINCE_CODES = {
    11, 12, 13, 14, 15, 16, 17, 18, 19, 21,
    31, 32, 33, 34, 35, 36,
    51, 52, 53,
    61, 62, 63, 64, 65,
    71, 72, 73, 74, 75, 76,
    81, 82,
    91, 92, 93, 94, 95, 96, 97,
}

_NIK_PATTERN = re.compile(r"(?<!\d)(\d{16})(?!\d)")

# ---------------------------------------------------------------------------
# Lazy easyocr reader — loaded once, in the background, degrades gracefully.
# ---------------------------------------------------------------------------
_reader: Any | None = None
_reader_lock = threading.Lock()
_reader_failed = False
_reader_error: str | None = None


def _get_reader() -> Any | None:
    global _reader, _reader_failed, _reader_error
    if _reader is not None or _reader_failed:
        return _reader
    with _reader_lock:
        if _reader is not None or _reader_failed:
            return _reader
        try:
            import easyocr  # heavy import — only pulled when first needed

            _reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        except Exception as exc:  # pragma: no cover - depends on local runtime
            _reader_failed = True
            _reader_error = str(exc)
            _reader = None
        return _reader


def load_in_background() -> None:
    """Warm up the OCR reader off the request path (call once at startup)."""
    if _reader is not None or _reader_failed:
        return
    threading.Thread(target=_get_reader, name="spectre-ocr-loader", daemon=True).start()


def ocr_status() -> dict[str, Any]:
    return {
        "ocr_loaded": _reader is not None,
        "ocr_failed": _reader_failed,
        "ocr_error": _reader_error,
    }


# ---------------------------------------------------------------------------
# Visual signals (fast, no OCR — safe to run per live frame).
# ---------------------------------------------------------------------------
def _moire_score(gray: np.ndarray) -> float:
    """High when the crop shows halftone/moire periodic energy (photographed printout)."""
    work = cv2.resize(gray, (256, 256), interpolation=cv2.INTER_AREA).astype(np.float32)
    work = work - work.mean()
    window = np.outer(np.hanning(256), np.hanning(256))
    spectrum = np.fft.fftshift(np.fft.fft2(work * window))
    magnitude = np.log1p(np.abs(spectrum))

    cy, cx = 128, 128
    yy, xx = np.ogrid[:256, :256]
    radius = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    # Mid-to-high frequency annulus is where screen/halftone peaks live.
    band = (radius > 28) & (radius < 110)
    band_vals = magnitude[band]
    if band_vals.size == 0:
        return 0.0
    band_mean = float(band_vals.mean())
    band_peak = float(band_vals.max())
    # "Peakiness" of the band relative to its own mean — periodic screening spikes.
    peakiness = (band_peak - band_mean) / (band_mean + 1e-6)
    return float(np.clip((peakiness - 0.35) / 1.0, 0.0, 1.0))


def _sharpness_value(gray: np.ndarray) -> float:
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _glare_genuine_score(bgr: np.ndarray) -> float:
    """Localised specular highlights (hologram/laminate) — a weak genuine-PVC indicator."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    value = hsv[:, :, 2]
    saturation = hsv[:, :, 1]
    # Specular = very bright AND low saturation, in tight clusters.
    specular = ((value > 240) & (saturation < 40)).astype(np.uint8)
    frac = float(specular.mean())
    if frac <= 0.0:
        return 0.0
    # A small, concentrated specular fraction is the genuine signature; a huge
    # blown-out area (frac very high) is just overexposure, not a hologram.
    return float(np.clip((min(frac, 0.05) / 0.05) * (1.0 - min(frac, 1.0)), 0.0, 1.0))


# ---------------------------------------------------------------------------
# NIK OCR + structural validation.
# ---------------------------------------------------------------------------
def _extract_nik(bgr: np.ndarray) -> str | None:
    reader = _get_reader()
    if reader is None:
        return None
    try:
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        # Upscale small crops so the digit row is legible to the OCR model.
        if max(gray.shape) < 700:
            scale = 700 / max(gray.shape)
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        results = reader.readtext(gray, allowlist="0123456789", detail=0, paragraph=False)
    except Exception:
        return None
    for text in results:
        digits = re.sub(r"\D", "", str(text))
        match = _NIK_PATTERN.search(digits)
        if match:
            return match.group(1)
    # Fall back to scanning the concatenation of all OCR fragments.
    joined = re.sub(r"\D", "", "".join(str(t) for t in results))
    match = _NIK_PATTERN.search(joined)
    return match.group(1) if match else None


def _validate_nik(nik: str) -> dict[str, Any]:
    issues: list[str] = []
    if len(nik) != 16 or not nik.isdigit():
        return {"valid": False, "issues": ["nik_not_16_digits"], "invalid_score": 1.0}

    province = int(nik[0:2])
    regency = int(nik[2:4])
    district = int(nik[4:6])
    day = int(nik[6:8])
    month = int(nik[8:10])
    sequence = int(nik[12:16])

    if province not in _VALID_PROVINCE_CODES:
        issues.append("province_code_unknown")
    if regency == 0:
        issues.append("regency_code_zero")
    if district == 0:
        issues.append("district_code_zero")
    # Women's birth day is stored as day + 40.
    birth_day = day - 40 if day > 40 else day
    if not (1 <= birth_day <= 31):
        issues.append("birth_day_invalid")
    if not (1 <= month <= 12):
        issues.append("birth_month_invalid")
    if sequence == 0:
        issues.append("sequence_zero")

    # Weight the structural problems: date issues are the strongest signal.
    weights = {
        "province_code_unknown": 0.25,
        "regency_code_zero": 0.3,
        "district_code_zero": 0.3,
        "birth_day_invalid": 0.6,
        "birth_month_invalid": 0.6,
        "sequence_zero": 0.4,
    }
    invalid_score = float(min(1.0, sum(weights.get(i, 0.3) for i in issues)))
    return {"valid": len(issues) == 0, "issues": issues, "invalid_score": invalid_score}


# ---------------------------------------------------------------------------
# Public entry point.
# ---------------------------------------------------------------------------
def _verdict_for(score: float) -> str:
    if score < _VERDICT_GENUINE_MAX:
        return "genuine"
    if score < _VERDICT_FAKE_MIN:
        return "suspicious"
    return "likely_fake"


def analyze_ktp_authenticity(
    image_bgr: np.ndarray,
    box: dict[str, Any],
    run_ocr: bool = True,
) -> dict[str, Any]:
    """Analyse a single KTP detection. ``box`` is a dict with x1/y1/x2/y2 keys.

    Returns a dict with ``fake_likelihood`` (0..1), ``verdict``, and the per-signal
    breakdown. ``run_ocr=False`` skips the (slow) NIK OCR — use that per live frame.
    """
    height, width = image_bgr.shape[:2]
    x1 = max(0, int(box.get("x1", 0)))
    y1 = max(0, int(box.get("y1", 0)))
    x2 = min(width, int(box.get("x2", 0)))
    y2 = min(height, int(box.get("y2", 0)))
    crop = image_bgr[y1:y2, x1:x2]

    if crop.size == 0 or min(crop.shape[:2]) < _MIN_CROP_SIDE:
        return {
            "verdict": "inconclusive",
            "fake_likelihood": 0.0,
            "reason": "crop_too_small",
            "signals": {},
            "nik": None,
        }

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    sharpness = _sharpness_value(gray)
    if sharpness < _MIN_SHARPNESS:
        return {
            "verdict": "inconclusive",
            "fake_likelihood": 0.0,
            "reason": "crop_too_blurry",
            "signals": {"sharpness": round(sharpness, 2)},
            "nik": None,
        }

    moire = _moire_score(gray)
    glare_genuine = _glare_genuine_score(crop)

    nik_info: dict[str, Any] | None = None
    nik_invalid_score = 0.0
    nik_value: str | None = None
    if run_ocr:
        nik_value = _extract_nik(crop)
        if nik_value:
            nik_info = _validate_nik(nik_value)
            nik_invalid_score = float(nik_info["invalid_score"])
        else:
            # OCR ran but found no 16-digit NIK — mild suspicion, not proof.
            nik_info = {"valid": False, "issues": ["nik_not_found"], "invalid_score": 0.2}
            nik_invalid_score = 0.2

    # Weighted blend. When OCR is skipped, renormalise over the visual signals only.
    if run_ocr:
        fake_likelihood = (
            _W_MOIRE * moire
            + _W_NIK * nik_invalid_score
            + _W_GLARE * (1.0 - glare_genuine)
        )
    else:
        denom = _W_MOIRE + _W_GLARE
        fake_likelihood = (
            _W_MOIRE * moire + _W_GLARE * (1.0 - glare_genuine)
        ) / denom

    fake_likelihood = float(np.clip(fake_likelihood, 0.0, 1.0))

    return {
        "verdict": _verdict_for(fake_likelihood),
        "fake_likelihood": round(fake_likelihood, 3),
        "reason": "ok",
        "signals": {
            "moire": round(moire, 3),
            "sharpness": round(sharpness, 2),
            "glare_genuine": round(glare_genuine, 3),
            "nik_invalid": round(nik_invalid_score, 3),
        },
        "nik": (
            {
                "value_masked": (nik_value[:6] + "******" + nik_value[-4:]) if nik_value else None,
                "found": nik_value is not None,
                "valid": nik_info.get("valid") if nik_info else None,
                "issues": nik_info.get("issues", []) if nik_info else [],
            }
            if run_ocr
            else None
        ),
        "note": (
            "Heuristic indicator only (FFT moire + sharpness + glare + NIK structure). "
            "Not a legal verdict; tune weights as needed without retraining the model."
        ),
    }


def analyze_detections(
    image_bgr: np.ndarray,
    detections: list[dict[str, Any]],
    run_ocr: bool = True,
    target_classes: tuple[str, ...] = ("KTP",),
) -> list[dict[str, Any]]:
    """Run authenticity analysis on every detection whose class is in ``target_classes``."""
    results: list[dict[str, Any]] = []
    for detection in detections:
        if detection.get("class_name") not in target_classes:
            continue
        analysis = analyze_ktp_authenticity(image_bgr, detection.get("box", {}), run_ocr=run_ocr)
        results.append(
            {
                "class_name": detection.get("class_name"),
                "confidence": detection.get("confidence"),
                "box": detection.get("box"),
                **analysis,
            }
        )
    return results
