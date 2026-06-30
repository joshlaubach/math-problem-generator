"""
Document extractor — Claude Vision extraction of math problems from uploaded files.

Accepts image files (JPEG, PNG, GIF, WebP) and PDFs (text extracted via pdfplumber).
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
    pdf_text = _load_pdf_texts(file_paths)

    if not images and not pdf_text:
        logger.info("No valid content to extract from")
        return []

    prompt = _EXTRACTOR_PROMPT
    if pdf_text:
        prompt = (
            "The following text was extracted from a PDF document:\n\n"
            + pdf_text
            + "\n\n"
            + _EXTRACTOR_PROMPT
        )

    from llm_anthropic_client import call_with_images
    try:
        raw = await call_with_images(
            text_prompt=prompt,
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
            pass  # PDFs handled separately via _load_pdf_texts (text extraction)
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


def _load_pdf_texts(file_paths: list[Path | str]) -> str:
    """
    Extract text from any PDF files in file_paths using pdfplumber (MIT license).
    Returns a single string of all extracted text, or "" if no PDFs or pdfplumber not installed.
    """
    try:
        import pdfplumber
    except ImportError:
        logger.warning(
            "pdfplumber not installed — PDF text extraction disabled. "
            "Install with: pip install pdfplumber"
        )
        return ""

    texts: list[str] = []
    for fp in file_paths:
        path = Path(fp)
        if path.suffix.lower() != ".pdf":
            continue
        try:
            with pdfplumber.open(str(path)) as pdf:
                page_texts = [
                    p.extract_text() or ""
                    for p in pdf.pages[:_MAX_PDF_PAGES]
                ]
            extracted = "\n".join(t for t in page_texts if t.strip())
            if extracted.strip():
                texts.append(extracted)
        except Exception as exc:
            logger.error("PDF text extraction failed for %s: %s", path, exc)
    return "\n\n".join(texts)


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
