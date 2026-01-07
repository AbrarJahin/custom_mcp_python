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
    """Read a text file under FILES_BASE_DIR."""
    base = Path(settings.files_base_dir)
    fp = _safe_join(base, path)

    if not fp.exists() or not fp.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    max_chars = max(100, min(int(max_chars), 200_000))
    data = fp.read_text(encoding="utf-8", errors="replace")
    if len(data) > max_chars:
        data = data[:max_chars]

    return {"path": str(fp), "text": data, "chars": len(data)}


def read_pdf_text(path: str, max_pages: int = 10, max_chars: int = 80_000) -> dict:
    """Extract basic text from a PDF under FILES_BASE_DIR."""
    base = Path(settings.files_base_dir)
    fp = _safe_join(base, path)

    if not fp.exists() or not fp.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    max_pages = max(1, min(int(max_pages), 50))
    max_chars = max(500, min(int(max_chars), 300_000))

    reader = PdfReader(str(fp))
    pages = reader.pages[:max_pages]

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
