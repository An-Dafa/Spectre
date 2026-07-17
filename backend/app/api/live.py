import asyncio
import base64
import json
from typing import Annotated, Any

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.responses import StreamingResponse

from app.ai.runtime import detector
from app.core.redaction_policy import build_active_classes, get_redaction_rule, validate_redaction_mode
from app.services.live_turbo_service import get_session, get_session_status, start_session, stop_session
from app.services.redaction_service import redact_image
from app.utils.image_utils import cv2_image_to_bytes, get_image_shape, read_image_bytes_to_cv2, validate_image_filename

router = APIRouter(tags=["live-stream"])
MAX_LIVE_FRAME_BYTES = 2_000_000
DEFAULT_LIVE_CLASSES = "Wajah,KTP,KK,SIM,Resi"


def _ensure_model_loaded() -> None:
    if not detector.loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Model not loaded: {detector.load_error or 'model is still loading or missing'}",
        )


def _live_settings(payload: dict[str, Any]) -> tuple[float, str, list[str]]:
    confidence = float(payload.get("confidence_threshold", 0.25))
    if not 0.01 <= confidence <= 0.99:
        raise ValueError("confidence_threshold must be between 0.01 and 0.99")
    rule = get_redaction_rule("live_webcam")
    mode = validate_redaction_mode(str(payload.get("redaction_mode", "blur")))
    active = build_active_classes(
        rule.active_classes,
        payload.get("active_classes", DEFAULT_LIVE_CLASSES),
        payload.get("disabled_classes"),
    )
    return confidence, mode, active


@router.websocket("/live/ws")
async def live_websocket(websocket: WebSocket) -> None:
    """Binary JPEG in, compact detection JSON out. Frames are never persisted."""
    await websocket.accept()
    if not detector.loaded:
        await websocket.send_json({"type": "error", "message": f"Model not loaded: {detector.load_error or 'model is still loading or missing'}"})
        await websocket.close(code=1013)
        return

    confidence, mode, active = _live_settings({})
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break

            if message.get("text") is not None:
                try:
                    payload = json.loads(message["text"])
                    confidence, mode, active = _live_settings(payload)
                except (HTTPException, TypeError, ValueError, json.JSONDecodeError) as exc:
                    detail = exc.detail if isinstance(exc, HTTPException) else str(exc)
                    await websocket.send_json({"type": "error", "message": detail})
                continue

            frame_bytes = message.get("bytes")
            if not frame_bytes:
                continue
            if len(frame_bytes) > MAX_LIVE_FRAME_BYTES:
                await websocket.send_json({"type": "error", "message": "Live frame exceeds 2 MB limit"})
                continue

            try:
                image = read_image_bytes_to_cv2(frame_bytes)
                prediction = await asyncio.to_thread(detector.predict, image, confidence, max(image.shape[:2]))
            except Exception as exc:
                await websocket.send_json({"type": "error", "message": str(exc)})
                continue

            detections = [
                detection
                for detection in prediction["detections"]
                if detection.get("class_name") in active
            ]
            await websocket.send_json({
                "type": "detections",
                "profile": "live_webcam",
                "redaction_mode": mode,
                "active_classes": active,
                "confidence_threshold": confidence,
                "device": prediction["device"],
                "inference_size": prediction["inference_size"],
                "latency_ms": prediction["latency_ms"],
                "image_shape": get_image_shape(image),
                "raw_detection_count": prediction["detection_count"],
                "detection_count": len(detections),
                "redacted_count": len(detections),
                "detections": detections,
                "storage_policy": {
                    "operational_zone_persisted": False,
                    "sovereign_vault_persisted": False,
                    "audit_log_per_frame": False,
                    "note": "Live frame processed ephemerally over WebSocket and not stored.",
                },
            })
    except WebSocketDisconnect:
        pass


@router.post("/live/redact-frame")
async def live_redact_frame(
    file: Annotated[UploadFile, File(...)],
    confidence_threshold: float = Query(default=0.25, ge=0.01, le=0.99),
    redaction_mode: str = Query(default="blur"),
    active_classes: str | None = Query(default=DEFAULT_LIVE_CLASSES),
    disabled_classes: str | None = Query(default=None),
    return_image: bool = Query(default=True),
) -> dict[str, Any]:
    """Process one webcam frame ephemerally. No Operational Zone or Vault persistence."""
    _ensure_model_loaded()
    validate_image_filename(file.filename or "frame.jpg")
    frame_bytes = await file.read()
    image = read_image_bytes_to_cv2(frame_bytes)
    rule = get_redaction_rule("live_webcam")
    mode = validate_redaction_mode(redaction_mode)
    active = build_active_classes(rule.active_classes, active_classes, disabled_classes)

    prediction = await asyncio.to_thread(detector.predict, image, confidence_threshold, max(image.shape[:2]))
    if return_image:
        redaction = redact_image(
            image,
            prediction["detections"],
            mode=mode,
            active_classes=active,
            label_enabled=False,
            label_text="",
            box_padding_ratio=0.04,
        )
    else:
        redacted_detections = [
            detection
            for detection in prediction["detections"]
            if detection.get("class_name") in active
        ]
        redaction = {
            "redacted_count": len(redacted_detections),
            "redacted_detections": redacted_detections,
            "skipped_detections": [
                detection
                for detection in prediction["detections"]
                if detection.get("class_name") not in active
            ],
        }

    response = {
        "profile": "live_webcam",
        "redaction_mode": mode,
        "active_classes": active,
        "confidence_threshold": confidence_threshold,
        "device": prediction["device"],
        "inference_size": prediction["inference_size"],
        "latency_ms": prediction["latency_ms"],
        "image_shape": get_image_shape(image),
        "raw_detection_count": prediction["detection_count"],
        "detection_count": prediction["detection_count"],
        "redacted_count": redaction["redacted_count"],
        "detections": prediction["detections"],
        "redacted_detections": redaction["redacted_detections"],
        "skipped_detections": redaction["skipped_detections"],
        "storage_policy": {
            "operational_zone_persisted": False,
            "sovereign_vault_persisted": False,
            "audit_log_per_frame": False,
            "note": "Live frame processed ephemerally and not stored.",
        },
    }
    if return_image:
        output_bytes = cv2_image_to_bytes(redaction["image"], ".jpg")
        response.update({
            "mime_type": "image/jpeg",
            "frame_image_base64": base64.b64encode(output_bytes).decode("ascii"),
        })
    return response


@router.post("/live/turbo/start")
def live_turbo_start(
    session_id: str = Query(default="default"),
    camera_index: int = Query(default=0, ge=0),
    confidence_threshold: float = Query(default=0.25, ge=0.01, le=0.99),
    redaction_mode: str = Query(default="blur"),
    active_classes: str | None = Query(default=DEFAULT_LIVE_CLASSES),
    disabled_classes: str | None = Query(default=None),
    target_width: int = Query(default=320, ge=240, le=1280),
    infer_interval_ms: int = Query(default=180, ge=50, le=2000),
    jpeg_quality: int = Query(default=75, ge=35, le=95),
    box_hold_ms: int = Query(default=700, ge=100, le=5000),
) -> dict[str, Any]:
    _ensure_model_loaded()
    try:
        session = start_session(
            session_id=session_id,
            detector=detector,
            camera_index=camera_index,
            confidence_threshold=confidence_threshold,
            redaction_mode=redaction_mode,
            active_classes=active_classes,
            disabled_classes=disabled_classes,
            target_width=target_width,
            infer_interval_ms=infer_interval_ms,
            jpeg_quality=jpeg_quality,
            box_hold_ms=box_hold_ms,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"status": "started", **session.get_status(), "mjpeg_url": f"/api/live/turbo/mjpeg?session_id={session_id}"}


@router.post("/live/turbo/stop")
def live_turbo_stop(session_id: str = Query(default="default")) -> dict[str, Any]:
    return {"status": "stopped", **stop_session(session_id)}


@router.get("/live/turbo/status")
def live_turbo_status(session_id: str = Query(default="default")) -> dict[str, Any]:
    return get_session_status(session_id)


@router.get("/live/turbo/mjpeg")
def live_turbo_mjpeg(session_id: str = Query(default="default")) -> StreamingResponse:
    session = get_session(session_id)
    if not session or not session.running:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Live turbo session is not running")
    return StreamingResponse(
        session.mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"},
    )
