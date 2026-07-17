from app.ai.class_map import CANONICAL_CLASSES
from app.api.system import get_redaction_config
from app.core.config import DEFAULT_CLASS_CONFIDENCE, Settings


def test_yolo26n_is_the_default_detector() -> None:
    settings = Settings()

    assert settings.model_path.name == "model_deteksi_yolo26n.pt"
    assert settings.effective_model_path.name == "model_deteksi_yolo26n.pt"


def test_redaction_contract_exposes_all_yolo26n_classes() -> None:
    config = get_redaction_config()

    assert "Kartu_ATM" in CANONICAL_CLASSES
    assert config["canonical_classes"] == CANONICAL_CLASSES
    assert config["default_class_confidence"] == DEFAULT_CLASS_CONFIDENCE
    assert set(DEFAULT_CLASS_CONFIDENCE) == set(CANONICAL_CLASSES)
