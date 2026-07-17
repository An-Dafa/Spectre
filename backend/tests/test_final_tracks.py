import asyncio
from io import BytesIO

from PIL import Image

from app.ai.class_map import normalize_class_name
from app.api.bridge import bridge_layout
from app.api import screen


class FakeUpload:
    filename = "screen.jpg"

    async def read(self) -> bytes:
        image = Image.new("RGB", (240, 120), "white")
        out = BytesIO()
        image.save(out, format="JPEG")
        return out.getvalue()


def test_new_live_classes_are_normalized() -> None:
    assert normalize_class_name("KK") == "KK"
    assert normalize_class_name("kartu keluarga") == "KK"
    assert normalize_class_name("Resi") == "Resi"
    assert normalize_class_name("shipping_label") == "Resi"
    assert normalize_class_name("sim") == "SIM"


def test_bridge_layout_exposes_three_tracks() -> None:
    result = bridge_layout()

    assert result["layout"] == "bridge"
    assert set(result["tracks"]) == {"enterprise_kyc", "liveshield", "screen_shield"}
    assert result["tracks"]["screen_shield"]["api"]["ocr_image"] == "/api/screen/ocr-redact"


def test_screen_ocr_redacts_matching_regions() -> None:
    original = screen._read_text_regions
    screen._read_text_regions = lambda image: [
        {"text": "NIK 3276010101010001", "confidence": 0.99, "box": {"x1": 10, "y1": 10, "x2": 180, "y2": 40}},
        {"text": "public title", "confidence": 0.90, "box": {"x1": 10, "y1": 50, "x2": 150, "y2": 80}},
    ]
    try:
        result = asyncio.run(screen.redact_screen_image(FakeUpload(), active_rules=None, return_image=False))
    finally:
        screen._read_text_regions = original

    assert result["profile"] == "screen_shield_ocr"
    assert result["redacted_count"] == 1
    assert result["storage_policy"]["operational_zone_persisted"] is False


if __name__ == "__main__":
    test_new_live_classes_are_normalized()
    test_bridge_layout_exposes_three_tracks()
    test_screen_ocr_redacts_matching_regions()
