from __future__ import annotations

import os
from pathlib import Path

from pypdf import PdfReader

from ..config import settings


def _safe_join(base: Path, user_path: str) -> Path:
    # Prevent path traversal: resolve and ensure within base
    base = base.resolve()
    p = (base / user_path).resolve()
    if not str(p).startswith(str(base)):
        raise ValueError("Path escapes base directory")
    return p


def read_text(path: str, max_chars: int = 50_000) -> dict:
    """Read a UTF-8-ish text file under FILES_BASE_DIR."""
    base = Path(settings.files_base_dir)
    fp = _safe_join(base, path)
    data = fp.read_bytes()
    text = data.decode(errors="replace")
    if len(text) > max_chars:
        text = text[:max_chars]
    return {"path": str(fp), "text": text}


def read_pdf_text(path: str, max_pages: int = 10, max_chars: int = 80_000) -> dict:
    """Extract text from a PDF under FILES_BASE_DIR (basic extraction)."""
    base = Path(settings.files_base_dir)
    fp = _safe_join(base, path)
    reader = PdfReader(str(fp))
    pages = reader.pages[: max(1, min(int(max_pages), 50))]
    chunks: list[str] = []
    for pg in pages:
        try:
            chunks.append(pg.extract_text() or "")
        except Exception:
            chunks.append("")
    text = "\n\n".join(chunks)
    if len(text) > max_chars:
        text = text[:max_chars]
    return {
        "path": str(fp),
        "pages_read": len(pages),
        "text": text,
    }
