import re
from pathlib import Path


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def prevent_path_traversal(base_dir: Path, filename: str) -> Path:
    if not filename or filename in {".", ".."}:
        raise ValueError("Invalid filename")
    safe_name = Path(filename).name
    target = (base_dir / safe_name).resolve()
    base = base_dir.resolve()
    if base not in target.parents and target != base:
        raise ValueError("Path traversal attempt rejected")
    return target


def slugify_filename(value: str) -> str:
    value = Path(value or "upload").name
    stem = Path(value).stem or "upload"
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", stem).strip(".-_") or "upload"
    return safe[:80]
