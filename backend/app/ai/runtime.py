from app.ai.detector import YoloDetector
from app.core.config import get_settings

settings = get_settings()
detector = YoloDetector(settings.effective_model_path, settings.model_device)
