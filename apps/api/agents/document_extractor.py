"""
Document extractor — Claude Vision extraction of math problems from uploaded files.

Accepts image files (JPEG, PNG, GIF, WebP) and PDFs (converted to images via PyMuPDF).
Returns a list of structured problem dicts: {number, statement_latex, points}.

Files are kept in DATA_DIR/session_uploads/<session_id>/ during the session and
deleted by ws_router._end_session when the session ends.
"""
from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_EXTRACTOR_SYSTEM = """\
You are a math problem extractor. Given one or more images of a problem set, exam, or
textbook page, extract every math problem as structured JSON.

Return ONLY valid JSON with this exact schema — no markdown, no explanation:
{
  "problems": [
    {
      "number": 1,
      "statement_latex": "The full problem statement using $...$ for inline math and $$...$$ for display math.",
      "points": null
    }
  ]
}

Rules:
- number: problem number as labeled, or sequential starting at 1 if not labeled (integer).
- statement_latex: full problem text with LaTeX math notation; preserve all formulas accurately.
- points: integer point value if explicitly shown (e.g., "(5 pts)"), otherwise null.
- Include ALL problems visible across all images.
- Ignore page headers, course names, student name fields, and purely decorative text.
- If the image shows a single problem, return it as problems[0] with number=1.
"""

_EXTRACTOR_PROMPT = (
    "Extract every math problem from the image(s) above. "
    "Return structured JSON per the system instructions."
)

# Maximum images per Vision call (Anthropic supports up to 20; we cap lower for cost)
_MAX_IMAGES = 5
# Maximum file size per image (bytes) — 5 MB after base64 overhead is fine
_MAX_FILE_BYTES = 8 * 1024 * 1024  # 8 MB raw
# Max PDF pages to convert
_MAX_PDF_PAGES = 3


async def extract_problems(file_paths: list[Path | str]) -> list[dict]:
    """
    Extract math problems from a list of local image / PDF files using Claude Vision.

    Args:
        file_paths: Local file paths (absolute or relative).

    Returns:
        List of {"number": int, "statement_latex": str, "points": int | None}.
        Returns [] if ANTHROPIC_API_KEY is absent or no usable images found.
    """
    from config import ANTHROPIC_API_KEY
    if not ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set — document extraction skipped")
        return []

    images = _load_images(file_paths)
    if not images:
        logger.info("No valid images to extract from")
        return []

    from llm_anthropic_client import call_with_images
    try:
        raw = await call_with_images(
            text_prompt=_EXTRACTOR_PROMPT,
            images=images[:_MAX_IMAGES],
            system=_EXTRACTOR_SYSTEM,
            max_tokens=2048,
        )
        return _parse_response(raw)
    except Exception as exc:
        logger.error("Document extraction failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_images(file_paths: list[Path | str]) -> list[dict]:
    """Convert a list of file paths into Anthropic image content dicts."""
    result: list[dict] = []
    for fp in file_paths:
        path = Path(fp)
        if not path.exists():
            logger.warning("Upload file not found: %s", path)
            continue
        suffix = path.suffix.lower()
        if suffix in (".jpg", ".jpeg"):
            img = _load_raw(path, "image/jpeg")
            if img:
                result.append(img)
        elif suffix == ".png":
            img = _load_raw(path, "image/png")
            if img:
                result.append(img)
        elif suffix == ".gif":
            img = _load_raw(path, "image/gif")
            if img:
                result.append(img)
        elif suffix == ".webp":
            img = _load_raw(path, "image/webp")
            if img:
                result.append(img)
        elif suffix == ".pdf":
            result.extend(_pdf_to_images(path))
        else:
            logger.debug("Unsupported upload type ignored: %s", suffix)
        if len(result) >= _MAX_IMAGES:
            break
    return result


def _load_raw(path: Path, media_type: str) -> Optional[dict]:
    """Read a raw image file and return an Anthropic image dict, or None if too large."""
    try:
        raw = path.read_bytes()
        if len(raw) > _MAX_FILE_BYTES:
            logger.warning("Image file too large (%d bytes), skipping: %s", len(raw), path)
            return None
        return {"data": base64.b64encode(raw).decode(), "media_type": media_type}
    except Exception as exc:
        logger.error("Could not read image file %s: %s", path, exc)
        return None


def _pdf_to_images(pdf_path: Path) -> list[dict]:
    """
    Convert the first N pages of a PDF to PNG images using PyMuPDF.
    Returns [] and logs a warning if PyMuPDF is not installed.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning(
            "PyMuPDF not installed — PDF extraction disabled. "
            "Install with: pip install pymupdf"
        )
        return []

    images: list[dict] = []
    try:
        doc = fitz.open(str(pdf_path))
        for page_num in range(min(len(doc), _MAX_PDF_PAGES)):
            page = doc[page_num]
            # 2× zoom for readable resolution; PNG for lossless
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            png_bytes = pix.tobytes("png")
            if len(png_bytes) <= _MAX_FILE_BYTES:
                images.append({
                    "data": base64.b64encode(png_bytes).decode(),
                    "media_type": "image/png",
                })
        doc.close()
    except Exception as exc:
        logger.error("PDF → image conversion failed for %s: %s", pdf_path, exc)
    return images


def _parse_response(raw: str) -> list[dict]:
    """Parse the JSON response from Claude and return validated problem dicts."""
    try:
        # Claude sometimes wraps in markdown fences despite instructions
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
        data = json.loads(text)
        problems_raw = data.get("problems", [])
        if not isinstance(problems_raw, list):
            return []
        result = []
        for i, p in enumerate(problems_raw):
            if not isinstance(p, dict):
                continue
            stmt = str(p.get("statement_latex", "")).strip()
            if not stmt:
                continue
            pts = p.get("points")
            result.append({
                "number": int(p.get("number", i + 1)),
                "statement_latex": stmt,
                "points": int(pts) if isinstance(pts, (int, float)) else None,
            })
        return result
    except Exception as exc:
        logger.error("Failed to parse document extractor response: %s | raw=%s", exc, raw[:200])
        return []
