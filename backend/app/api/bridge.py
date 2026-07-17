from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["bridge-layout"])


@router.get("/bridge/layout")
def bridge_layout() -> dict[str, Any]:
    return {
        "layout": "bridge",
        "columns": ["source_unsafe", "spectre_edge_engine", "destination_safe"],
        "tracks": {
            "enterprise_kyc": {
                "left": {"role": "third_party_registration", "raw_data_visible": True, "input": "document upload"},
                "middle": {"role": "spectre_edge_engine", "pipeline": ["yolo_detect", "guardrail", "redact", "vault_encrypt", "audit"]},
                "right": {"role": "company_server", "receives": "redacted document only", "original_location": "sovereign_vault"},
                "api": {"process": "/api/redact", "records": "/api/storage/records"},
            },
            "liveshield": {
                "left": {"role": "raw_camera_or_obs_source", "raw_data_visible": True, "input": "webcam frame or websocket jpeg"},
                "middle": {"role": "spectre_virtual_camera", "pipeline": ["yolo_detect", "redact_frame", "ephemeral_return"]},
                "right": {"role": "public_broadcast", "receives": "redacted frame only", "original_location": "not persisted"},
                "api": {"frame": "/api/live/redact-frame", "websocket": "/api/live/ws", "turbo": "/api/live/turbo/start"},
            },
            "screen_shield": {
                "left": {"role": "screen_share_source", "raw_data_visible": True, "input": "screen text or screenshot"},
                "middle": {"role": "spectre_screen_shield", "pipeline": ["ocr_or_text_parse", "regex_detect", "blackout", "ephemeral_return"]},
                "right": {"role": "meeting_transport", "receives": "redacted screen content only", "original_location": "not persisted"},
                "api": {"text": "/api/screen/redact", "ocr_image": "/api/screen/ocr-redact"},
            },
        },
    }
