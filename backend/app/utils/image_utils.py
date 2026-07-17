import math
from pathlib import Path

import cv2
import numpy as np
from fastapi import HTTPException, status

from app.utils.file_utils import slugify_filename

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_DOCUMENT_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | {".pdf"}
MAX_PDF_BYTES = 20 * 1024 * 1024
MAX_PDF_RENDER_PIXELS = 20_000_000
PDF_RENDER_DPI = 150


def validate_image_filename(filename: str | None) -> None:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image extension. Allowed: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}",
        )


def validate_document_filename(filename: str | None) -> None:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document extension. Allowed: {', '.join(sorted(ALLOWED_DOCUMENT_EXTENSIONS))}",
        )


def read_image_bytes_to_cv2(image_bytes: bytes) -> np.ndarray:
    if not image_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty image file")
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or unsupported image bytes")
    return image


def read_document_bytes_to_cv2(document_bytes: bytes, filename: str | None) -> np.ndarray:
    validate_document_filename(filename)
    if Path(filename or "").suffix.lower() != ".pdf":
        return read_image_bytes_to_cv2(document_bytes)
    if not document_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty PDF file")
    if len(document_bytes) > MAX_PDF_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="PDF exceeds the 20 MB limit")

    import pymupdf

    try:
        document = pymupdf.open(stream=document_bytes, filetype="pdf")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or corrupted PDF") from exc

    with document:
        if document.needs_pass:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password-protected PDFs are not supported")
        if document.page_count != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MVP PDF upload currently supports exactly one page",
            )

        page = document[0]
        scale = PDF_RENDER_DPI / 72
        width = math.ceil(page.rect.width * scale)
        height = math.ceil(page.rect.height * scale)
        if width <= 0 or height <= 0 or width * height > MAX_PDF_RENDER_PIXELS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PDF page dimensions are too large")

        pixmap = page.get_pixmap(dpi=PDF_RENDER_DPI, colorspace=pymupdf.csRGB, alpha=False)
        rgb = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width, 3)
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def get_image_shape(image: np.ndarray) -> dict[str, int]:
    height, width = image.shape[:2]
    channels = image.shape[2] if len(image.shape) > 2 else 1
    return {"width": int(width), "height": int(height), "channels": int(channels)}


def cv2_image_to_bytes(image: np.ndarray, extension: str = ".jpg") -> bytes:
    if not extension.startswith("."):
        extension = f".{extension}"
    success, encoded = cv2.imencode(extension, image)
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to encode image")
    return encoded.tobytes()


def clamp_box_to_image(x1: float, y1: float, x2: float, y2: float, image_width: int, image_height: int) -> dict[str, int]:
    left = max(0, min(int(round(x1)), image_width - 1))
    top = max(0, min(int(round(y1)), image_height - 1))
    right = max(0, min(int(round(x2)), image_width))
    bottom = max(0, min(int(round(y2)), image_height))
    if right <= left:
        right = min(image_width, left + 1)
    if bottom <= top:
        bottom = min(image_height, top + 1)
    return {"x1": left, "y1": top, "x2": right, "y2": bottom}


def safe_filename(original_filename: str | None) -> str:
    suffix = Path(original_filename or "upload.jpg").suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        suffix = ".jpg"
    return f"{slugify_filename(original_filename or 'upload')}{suffix}"
