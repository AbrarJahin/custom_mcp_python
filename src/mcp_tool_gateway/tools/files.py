from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from ..config import settings


def _safe_join(base: Path, user_path: str) -> Path:
    """Prevent path traversal; keep reads inside FILES_BASE_DIR."""
    base = base.resolve()
    p = (base / user_path).resolve()
    if base != p and base not in p.parents:
        raise ValueError("Path escapes base directory")
    return p


def read_text(path: str, max_chars: int = 50_000) -> dict:
    base = Path(settings.files_base_dir)
    fp = _safe_join(base, path)

    if not fp.exists() or not fp.is_file():
        raise FileNotFoundError(str(fp))

    text = fp.read_text(encoding="utf-8", errors="replace")
    if len(text) > max_chars:
        text = text[:max_chars]

    return {"path": str(fp), "text": text, "chars": len(text)}


def read_pdf_text(path: str, max_pages: int = 10, max_chars: int = 80_000) -> dict:
    base = Path(settings.files_base_dir)
    fp = _safe_join(base, path)

    if not fp.exists() or not fp.is_file():
        raise FileNotFoundError(str(fp))

    reader = PdfReader(str(fp))
    pages = reader.pages[: max(1, int(max_pages))]

    chunks: list[str] = []
    for pg in pages:
        try:
            chunks.append(pg.extract_text() or "")
        except Exception:
            chunks.append("")
    text = "\n\n".join(chunks)
    if len(text) > max_chars:
        text = text[:max_chars]

    return {"path": str(fp), "pages_read": len(pages), "text": text}
