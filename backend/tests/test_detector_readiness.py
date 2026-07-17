import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from app.ai.detector import YoloDetector


class FakeModel:
    def __init__(self, fail_warmup: bool = False) -> None:
        self.fail_warmup = fail_warmup

    def predict(self, image, **kwargs):
        assert image.shape == (320, 320, 3)
        assert kwargs["imgsz"] == 320
        if self.fail_warmup:
            raise RuntimeError("warmup failed")
        return []


def load_with_fake_model(fail_warmup: bool) -> YoloDetector:
    with TemporaryDirectory() as directory:
        model_path = Path(directory) / "models" / "model.pt"
        model_path.parent.mkdir()
        model_path.write_bytes(b"fake")
        previous = sys.modules.get("ultralytics")
        previous_config_dir = os.environ.get("YOLO_CONFIG_DIR")
        sys.modules["ultralytics"] = SimpleNamespace(YOLO=lambda _: FakeModel(fail_warmup))
        try:
            detector = YoloDetector(model_path)
            detector.load()
            return detector
        finally:
            if previous is None:
                sys.modules.pop("ultralytics", None)
            else:
                sys.modules["ultralytics"] = previous
            if previous_config_dir is None:
                os.environ.pop("YOLO_CONFIG_DIR", None)
            else:
                os.environ["YOLO_CONFIG_DIR"] = previous_config_dir


def test_ready_only_after_successful_warmup() -> None:
    detector = load_with_fake_model(False)
    assert detector.loaded
    assert not detector.loading
    assert detector.load_error is None


def test_warmup_failure_keeps_detector_unavailable() -> None:
    detector = load_with_fake_model(True)
    assert not detector.loaded
    assert detector.model is None
    assert detector.load_error == "warmup failed"


if __name__ == "__main__":
    test_ready_only_after_successful_warmup()
    test_warmup_failure_keeps_detector_unavailable()
