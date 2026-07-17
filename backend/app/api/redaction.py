import json
import time
import uuid
from typing import Annotated, Any

import cv2
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.ai.runtime import detector
from app.core.config import get_settings
from app.core.redaction_policy import build_active_classes, get_redaction_rule, validate_redaction_mode
from app.core.runtime_policy import load_runtime_policy, resolve_class_confidence
from app.db.database import get_db
from app.db.models import OperationalMetadata
from app.db.repositories import OperationalMetadataRepository
from app.services.audit_service import create_audit_log
from app.services.authenticity_service import analyze_detections
from app.services.false_positive_guardrail import apply_false_positive_guardrail, validate_guardrail_mode
from app.services.redaction_service import redact_image
from app.services.robustness_service import robust_predict_with_tta
from app.services.storage_service import save_operational_metadata, save_redacted_image_to_operational_zone
from app.services.vault_service import encrypt_original_for_vault
from app.utils.image_utils import get_image_shape, read_document_bytes_to_cv2

router = APIRouter(tags=["redaction"])
settings = get_settings()
SUPPORTED_PERFORMANCE_MODES = {"fast", "balanced", "robust"}
SLOW_PROCESSING_THRESHOLD_MS = 5000.0


def resolve_performance_settings(
    performance_mode: str,
    document_tta: bool,
    tta_angles: str | None,
    guardrail_enabled: bool,
    guardrail_mode: str | None,
) -> dict[str, Any]:
    mode = (performance_mode or "fast").strip().lower()
    if mode not in SUPPORTED_PERFORMANCE_MODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid performance_mode. Supported values: fast, balanced, robust.",
        )

    if mode == "fast":
        return {
            "performance_mode": "fast",
            "document_tta": False,
            "tta_angles": "0",
            "guardrail_enabled": guardrail_enabled,
            "guardrail_mode": guardrail_mode or "privacy_first",
            "ocr_enabled": False,
            "max_inference_size": 640,
            "note": "Fast Demo uses one inference pass, no OCR, and lightweight post-processing.",
        }

    if mode == "balanced":
        return {
            "performance_mode": "balanced",
            "document_tta": True,
            "tta_angles": "0,180",
            "guardrail_enabled": guardrail_enabled,
            "guardrail_mode": guardrail_mode or "precision_demo",
            "ocr_enabled": False,
            "max_inference_size": 960,
            "note": "Balanced uses 0/180 document TTA without OCR by default.",
        }

    return {
        "performance_mode": "robust",
        "document_tta": True,
        "tta_angles": tta_angles or "0,90,180,270",
        "guardrail_enabled": guardrail_enabled,
        "guardrail_mode": guardrail_mode or "precision_demo",
        "ocr_enabled": True,
        "max_inference_size": 1280,
        "note": "Robust Verification enables heavier rotation checks and OCR-capable guardrail validation.",
    }


def _prepare_inference_image(image, max_inference_size: int):
    height, width = image.shape[:2]
    longest = max(height, width)
    if max_inference_size <= 0 or longest <= max_inference_size:
        return image, 1.0
    scale = max_inference_size / float(longest)
    target_width = max(1, int(round(width * scale)))
    target_height = max(1, int(round(height * scale)))
    resized = cv2.resize(image, (target_width, target_height), interpolation=cv2.INTER_AREA)
    return resized, scale


def _scale_prediction_boxes(prediction: dict[str, Any], scale: float) -> dict[str, Any]:
    if scale >= 0.999:
        return {**prediction, "inference_scale": 1.0}
    factor = 1.0 / scale
    detections: list[dict[str, Any]] = []
    for detection in prediction.get("detections", []):
        box = detection.get("box") or {}
        detections.append(
            {
                **detection,
                "box": {
                    "x1": float(box.get("x1", 0.0)) * factor,
                    "y1": float(box.get("y1", 0.0)) * factor,
                    "x2": float(box.get("x2", 0.0)) * factor,
                    "y2": float(box.get("y2", 0.0)) * factor,
                },
            }
        )
    return {
        **prediction,
        "detections": detections,
        "detection_count": len(detections),
        "inference_scale": round(scale, 4),
    }


def _build_timing(timings: dict[str, float], total_ms: float) -> dict[str, float]:
    storage_ms = (
        timings.get("redacted_image_storage_ms", 0.0)
        + timings.get("metadata_storage_ms", 0.0)
        + timings.get("operational_db_stage_ms", 0.0)
        + timings.get("db_commit_ms", 0.0)
    )
    return {
        "total_ms": round(total_ms, 2),
        "inference_ms": round(timings.get("inference_ms", timings.get("inference_wall_ms", 0.0)), 2),
        "guardrail_ms": round(timings.get("guardrail_ms", 0.0), 2),
        "redaction_ms": round(timings.get("redaction_ms", 0.0), 2),
        "storage_ms": round(storage_ms, 2),
        "vault_ms": round(timings.get("vault_ms", timings.get("vault_encrypt_ms", 0.0)), 2),
        "decode_ms": round(timings.get("decode_ms", 0.0), 2),
        "policy_ms": round(timings.get("policy_ms", 0.0), 2),
        "authenticity_ms": round(timings.get("authenticity_ms", 0.0), 2),
        "audit_ms": round(timings.get("audit_stage_ms", 0.0), 2),
    }


@router.post("/redact")
async def redact_upload(
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(...)],
    confidence_threshold: float = Query(default=settings.model_confidence, ge=0.01, le=0.99),
    profile: str = "government",
    redaction_mode: str | None = None,
    active_classes: str | None = None,
    disabled_classes: str | None = None,
    use_runtime_policy: bool = False,
    document_tta: bool = True,
    tta_angles: str | None = None,
    guardrail_enabled: bool = True,
    guardrail_mode: str | None = None,
    authenticity_ocr: bool = False,
    performance_mode: str = Query(default="fast", description="Redaction performance preset: fast, balanced, robust."),
) -> dict[str, Any]:
    request_started = time.perf_counter()
    timings: dict[str, float] = {}

    def mark_timing(name: str, started: float) -> None:
        timings[name] = round((time.perf_counter() - started) * 1000, 2)

    if not detector.loaded:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Model not loaded: {detector.load_error or 'missing model'}")

    performance_settings = resolve_performance_settings(performance_mode, document_tta, tta_angles, guardrail_enabled, guardrail_mode)

    stage_started = time.perf_counter()
    filename = file.filename or "upload.jpg"
    original_bytes = await file.read()
    image = read_document_bytes_to_cv2(original_bytes, filename)
    mark_timing("decode_ms", stage_started)
    dynamic_injection = None

    stage_started = time.perf_counter()
    if use_runtime_policy:
        policy = load_runtime_policy()
        confidence_threshold = float(policy["confidence_threshold"])
        class_confidence = resolve_class_confidence(policy, confidence_threshold)
        profile = str(policy["profile"])
        redaction_mode = str(policy["redaction_mode"])
        active_classes = ",".join(policy["active_classes"])
        disabled_classes = ",".join(policy["disabled_classes"])
        label_text = str(policy.get("label_text") or "REDACTED")
        dynamic_injection = {"enabled": True, "policy": policy}
    else:
        # Tanpa runtime policy: pakai default per-kelas dari config, dengan
        # confidence_threshold skalar query param sebagai fallback per kelas.
        class_confidence = resolve_class_confidence({}, confidence_threshold)
        label_text = "REDACTED"

    rule = get_redaction_rule(profile)
    mode = validate_redaction_mode(redaction_mode or rule.mode)
    active = build_active_classes(rule.active_classes, active_classes, disabled_classes)
    try:
        normalized_guardrail_mode = validate_guardrail_mode(str(performance_settings["guardrail_mode"]))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not performance_settings["guardrail_enabled"]:
        normalized_guardrail_mode = "off"
    mark_timing("policy_ms", stage_started)

    stage_started = time.perf_counter()
    inference_image, inference_scale = _prepare_inference_image(image, int(performance_settings["max_inference_size"]))
    prediction = (
        robust_predict_with_tta(detector, inference_image, class_confidence, tta_angles=str(performance_settings["tta_angles"]))
        if performance_settings["document_tta"] and profile == "government"
        else detector.predict(inference_image, class_confidence)
    )
    prediction = _scale_prediction_boxes(prediction, inference_scale)
    mark_timing("inference_ms", stage_started)

    stage_started = time.perf_counter()
    guardrail = apply_false_positive_guardrail(
        image=image,
        detections=prediction["detections"],
        guardrail_mode=normalized_guardrail_mode,
        profile=profile,
        active_classes=active,
        ocr_enabled=bool(performance_settings["ocr_enabled"]),
    )
    mark_timing("guardrail_ms", stage_started)

    stage_started = time.perf_counter()
    ktp_authenticity = analyze_detections(
        image,
        prediction["detections"],
        run_ocr=bool(performance_settings["ocr_enabled"]) and authenticity_ocr,
    )
    mark_timing("authenticity_ms", stage_started)

    stage_started = time.perf_counter()
    redaction = redact_image(image, guardrail["validated_detections"], mode=mode, active_classes=active, label_enabled=rule.label_enabled, label_text=label_text)
    mark_timing("redaction_ms", stage_started)

    record_id = f"rec_{uuid.uuid4().hex}"
    upload_session_id = f"upl_{uuid.uuid4().hex}"

    stage_started = time.perf_counter()
    redacted_file = save_redacted_image_to_operational_zone(redaction["image"], filename, record_id)
    detected_classes = sorted({item["class_name"] for item in prediction["detections"]})
    mark_timing("redacted_image_storage_ms", stage_started)

    stage_started = time.perf_counter()
    OperationalMetadataRepository(db).add(OperationalMetadata(
        record_id=record_id,
        upload_session_id=upload_session_id,
        original_filename=filename,
        redacted_filename=redacted_file["filename"],
        redacted_path=redacted_file["path"],
        redaction_profile=profile,
        redaction_mode=mode,
        active_classes_json=json.dumps(active),
        confidence_threshold=confidence_threshold,
        detection_count=prediction["detection_count"],
        redacted_count=redaction["redacted_count"],
        latency_ms=prediction["latency_ms"],
        detected_classes_json=json.dumps(detected_classes),
        stores_private_original_in_operational_zone=False,
    ))
    mark_timing("operational_db_stage_ms", stage_started)

    stage_started = time.perf_counter()
    vault_record, vault_bundle = encrypt_original_for_vault(db, record_id, upload_session_id, filename, original_bytes)
    mark_timing("vault_ms", stage_started)

    stage_started = time.perf_counter()
    create_audit_log(db, record_id, "Operational Zone", "redacted_output_created", "system", "Redacted output created", {"redacted_file": redacted_file})
    create_audit_log(db, record_id, "Sovereign Vault", "encrypted_original_stored", "system", "Encrypted original stored", {"key_version": vault_record.key_version})
    if guardrail["rejected_detections"]:
        create_audit_log(
            db,
            record_id,
            "AI Guardrail",
            "false_positive_guardrail_applied",
            "system",
            "Rejected suspicious hand-drawn or non-authentic detections before redaction.",
            {
                "guardrail_mode": normalized_guardrail_mode,
                "rejected_count": len(guardrail["rejected_detections"]),
                "validation_summary": guardrail["validation_summary"],
            },
        )
    if dynamic_injection:
        create_audit_log(db, record_id, "Dynamic Injection", "runtime_policy_applied", "system", "Runtime policy applied to redaction", dynamic_injection)
    flagged_ktp = [item for item in ktp_authenticity if item["verdict"] in ("suspicious", "likely_fake")]
    if flagged_ktp:
        create_audit_log(
            db,
            record_id,
            "Operational Zone",
            "ktp_authenticity_flagged",
            "system",
            f"{len(flagged_ktp)} KTP detection(s) flagged by authenticity heuristics",
            {"flagged": [{"verdict": i["verdict"], "fake_likelihood": i["fake_likelihood"], "signals": i["signals"]} for i in flagged_ktp]},
        )
    mark_timing("audit_stage_ms", stage_started)

    stage_started = time.perf_counter()
    db.commit()
    mark_timing("db_commit_ms", stage_started)

    total_latency_ms = round((time.perf_counter() - request_started) * 1000, 2)
    timing = _build_timing(timings, total_latency_ms)

    if performance_settings["performance_mode"] == "robust" or total_latency_ms >= SLOW_PROCESSING_THRESHOLD_MS:
        stage_started = time.perf_counter()
        create_audit_log(
            db,
            record_id,
            "AI Pipeline",
            "performance_mode_applied",
            "system",
            "Applied redaction performance mode.",
            {
                "performance_mode": performance_settings["performance_mode"],
                "document_tta": performance_settings["document_tta"],
                "tta_angles": performance_settings["tta_angles"],
                "ocr_enabled": performance_settings["ocr_enabled"],
                "total_ms": total_latency_ms,
            },
        )
        db.commit()
        mark_timing("performance_audit_ms", stage_started)
        total_latency_ms = round((time.perf_counter() - request_started) * 1000, 2)
        timing = _build_timing(timings, total_latency_ms)

    performance_payload = {
        "mode": performance_settings["performance_mode"],
        "document_tta": performance_settings["document_tta"],
        "tta_angles": performance_settings["tta_angles"],
        "guardrail_enabled": normalized_guardrail_mode != "off",
        "guardrail_mode": normalized_guardrail_mode,
        "ocr_enabled": performance_settings["ocr_enabled"],
        "max_inference_size": performance_settings["max_inference_size"],
        "inference_scale": prediction.get("inference_scale", 1.0),
        "detector_latency_ms": prediction["latency_ms"],
        "timing": timing,
        "note": "Performance mode changes preprocessing/post-processing only. The YOLO model is not retrained.",
    }

    stage_started = time.perf_counter()
    metadata_file = save_operational_metadata({
        "record_id": record_id,
        "upload_session_id": upload_session_id,
        "original_filename": filename,
        "redacted_file": redacted_file,
        "redaction_profile": profile,
        "redaction_mode": mode,
        "active_classes": active,
        "confidence_threshold": confidence_threshold,
        "class_confidence_threshold": class_confidence,
        "detection_count": prediction["detection_count"],
        "redacted_count": redaction["redacted_count"],
        "latency_ms": prediction["latency_ms"],
        "detected_classes": detected_classes,
        "performance_mode": performance_settings["performance_mode"],
        "effective_tta_angles": performance_settings["tta_angles"],
        "ocr_enabled": performance_settings["ocr_enabled"],
        "timing": timing,
        "performance": performance_payload,
        "false_positive_guardrail": {
            "enabled": normalized_guardrail_mode != "off",
            "mode": normalized_guardrail_mode,
            "validation_summary": guardrail["validation_summary"],
            "rejected_count": len(guardrail["rejected_detections"]),
        },
        "stores_private_original_in_operational_zone": False,
    })
    mark_timing("metadata_storage_ms", stage_started)
    total_latency_ms = round((time.perf_counter() - request_started) * 1000, 2)
    timing = _build_timing(timings, total_latency_ms)
    performance_payload["timing"] = timing

    return {
        "record_id": record_id,
        "upload_session_id": upload_session_id,
        "filename": filename,
        "image_shape": get_image_shape(image),
        "redaction_policy": {
            "profile": profile,
            "mode": mode,
            "active_classes": active,
            "label_enabled": rule.label_enabled,
            "label_text": label_text,
            "performance_mode": performance_settings["performance_mode"],
            "document_tta": performance_settings["document_tta"],
            "tta_angles": performance_settings["tta_angles"],
            "guardrail_enabled": normalized_guardrail_mode != "off",
            "guardrail_mode": normalized_guardrail_mode,
            "ocr_enabled": performance_settings["ocr_enabled"],
            "max_inference_size": performance_settings["max_inference_size"],
            "note": "Performance mode changes preprocessing/post-processing only. The YOLO model is not retrained.",
        },
        "dynamic_injection": dynamic_injection,
        "robustness": prediction.get("robustness"),
        "confidence_threshold": confidence_threshold,
        "class_confidence_threshold": class_confidence,
        "device": prediction["device"],
        "latency_ms": prediction["latency_ms"],
        "total_latency_ms": total_latency_ms,
        "timing": timing,
        "performance": performance_payload,
        "detection_count": prediction["detection_count"],
        "redacted_count": redaction["redacted_count"],
        "detected_classes": detected_classes,
        "detections": guardrail["detections"],
        "redacted_detections": redaction["redacted_detections"],
        "skipped_detections": redaction["skipped_detections"] + guardrail["rejected_detections"],
        "rejected_detections": guardrail["rejected_detections"],
        "validation_summary": guardrail["validation_summary"],
        "ktp_authenticity": ktp_authenticity,
        "operational_zone": {"redacted_file": redacted_file, "metadata_file": metadata_file, "stores_private_original": False},
        "sovereign_vault": {
            "encrypted": True,
            "key_id": vault_record.key_id,
            "key_version": vault_record.key_version,
            "encrypted_bundle_path": vault_record.encrypted_bundle_path,
            "original_sha256": vault_bundle["original_sha256"],
            "plaintext_stored": False,
        },
    }
