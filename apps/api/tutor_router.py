"""
Tutor utility endpoints.

GET  /tutor/taxonomy          — hierarchical course/unit/topic data for intake form
POST /tutor/session/create    — create a pending session from intake form
POST /tutor/validate          — SymPy expression validation for the scratchpad
POST /tutor/dispute           — "I think I'm right" dispute flow
POST /tutor/transcribe        — Deepgram STT (Phase 3)
POST /tutor/synthesize        — ElevenLabs TTS (Phase 3)
"""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from typing import Literal, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from auth_dependencies import require_student, get_user_repository
from users_models import User

router = APIRouter(prefix="/tutor", tags=["tutor"])

# ---------------------------------------------------------------------------
# Taxonomy — public, no auth (course/unit/topic hierarchy for intake form)
# ---------------------------------------------------------------------------

@router.get("/taxonomy")
def get_taxonomy():
    """
    Return the full course→unit→topic hierarchy from the in-memory topic registry.

    Used by the intake form dropdowns on /tutor/new.
    Response is ordered by curriculum sequence (matches taxonomy.py insertion order).
    """
    from topic_registry import COURSE_REGISTRY

    courses = []
    for course_data in COURSE_REGISTRY.values():
        units = []
        for unit_data in course_data["units"].values():
            topics = [
                {"id": tm.topic_id, "name": tm.topic_name}
                for tm in unit_data["topics"].values()
            ]
            units.append({
                "id": unit_data["unit_id"],
                "name": unit_data["unit_name"],
                "is_honors": unit_data["is_honors"],
                "topics": topics,
            })
        courses.append({
            "id": course_data["course_id"],
            "name": course_data["course_name"],
            "units": units,
        })
    return courses


# ---------------------------------------------------------------------------
# Session creation (pre-session intake form → pending session)
# ---------------------------------------------------------------------------

class SessionCreateRequest(BaseModel):
    class_name: str = Field(..., description="Course name, e.g. 'Algebra I' or 'Other'")
    unit_names: list[str] = Field(default_factory=list)
    topic_ids: list[str] = Field(default_factory=list)
    freeform_topics: list[str] = Field(default_factory=list)
    why: Optional[str] = Field(default=None)
    notes: str = Field(default="", max_length=2000)
    session_type: Literal["1hr", "2hr"] = "1hr"
    exam_datetime: Optional[str] = Field(default=None, description="ISO datetime of upcoming exam (test_prep sessions)")


class SessionCreateResponse(BaseModel):
    session_id: str


@router.post("/session/create", response_model=SessionCreateResponse)
async def create_tutor_session(
    body: SessionCreateRequest,
    user: User = Depends(require_student),
):
    """
    Create a pending tutor session from intake form data.

    Tutor access is credits-only (no tier gate): this preflight checks that the
    student has an available credit so the intake form can show a friendly
    error instead of failing later at WebSocket connect. The credit itself is
    consumed at connect time, not here.
    """
    from credit_router import has_available_credit
    from ws_session import create_pending_session, SESSION_TYPES

    if not has_available_credit(user.id, kind=body.session_type):
        raise HTTPException(
            status_code=402,
            detail=f"No {body.session_type} session credits available. Purchase a session at /pricing to get started.",
        )

    if body.session_type not in SESSION_TYPES:
        raise HTTPException(status_code=422, detail="session_type must be '1hr' or '2hr'")

    session_id = str(uuid4())

    # Determine mode from why field
    why_to_mode = {
        "homework": "homework",
        "test_prep": "practice",
        "get_ahead": "practice",
        "learn_concept": "concept",
    }
    mode = why_to_mode.get(body.why or "", "practice")

    try:
        create_pending_session(
            session_id=session_id,
            user_id=user.id,
            session_type=body.session_type,
            class_name=body.class_name,
            unit_names=body.unit_names,
            topic_ids=body.topic_ids,
            freeform_topics=body.freeform_topics,
            why=body.why,
            notes=body.notes,
            mode=mode,
            exam_datetime=body.exam_datetime,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return SessionCreateResponse(session_id=session_id)


# ---------------------------------------------------------------------------
# Guest demo session (Phase 2.2)
# One free 30-min session per week per IP, no account required, DOB ≥ 13
# ---------------------------------------------------------------------------

GUEST_SESSION_DURATION = 1800  # 30 minutes
GUEST_TOKEN_GRACE = 300        # extra 5 min on token expiry for network lag
GUEST_DEMO_RATE_WINDOW = 7 * 24 * 3600  # 1 per week per IP


class GuestSessionRequest(BaseModel):
    date_of_birth: str  # ISO date "YYYY-MM-DD"


class GuestSessionResponse(BaseModel):
    guest_token: str
    session_id: str


def _guest_compute_age(dob_str: str) -> Optional[int]:
    try:
        dob = date.fromisoformat(dob_str)
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return age
    except Exception:
        return None


@router.post("/guest-session", response_model=GuestSessionResponse, status_code=201)
async def create_guest_session(
    body: GuestSessionRequest,
    request: Request,
):
    """
    Create a 30-minute free demo tutor session without requiring a user account.

    Rate limit: 1 per week per IP.
    Requires date_of_birth ≥ 13 years (under-13 hard blocked).
    Returns a short-lived guest JWT and a pre-created session_id.
    """
    import rate_limit as _rl
    from config import JWT_SECRET_KEY, JWT_ALGORITHM
    from auth_utils import create_access_token
    from ws_session import create_pending_session

    # ── Age gate ─────────────────────────────────────────────────────────────
    age = _guest_compute_age(body.date_of_birth)
    if age is None:
        raise HTTPException(status_code=422, detail="Invalid date_of_birth. Use YYYY-MM-DD.")
    if age < 13:
        raise HTTPException(status_code=403, detail="You must be 13 or older to start a session.")

    # ── Rate limit: 1 per week per IP ────────────────────────────────────────
    client_ip = request.client.host if request.client else "unknown"
    allowed, _ = _rl.hit(f"guest_demo:{client_ip}", 1, GUEST_DEMO_RATE_WINDOW)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Free sessions are limited to once per week. Come back next week, or create a free account to continue.",
        )

    # ── Create session ────────────────────────────────────────────────────────
    guest_id = f"guest_{uuid4().hex[:16]}"
    session_id = str(uuid4())
    try:
        session = create_pending_session(
            session_id=session_id,
            user_id=guest_id,
            session_type="1hr",  # slot type; max_duration overridden below
            class_name="",
            why="demo",
            mode="practice",
        )
        # Override duration for demo (30 min)
        session.max_duration_seconds = GUEST_SESSION_DURATION
        session.session_tier = "demo"
        from ws_session import update_session
        update_session(session)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    # ── Mint guest JWT ────────────────────────────────────────────────────────
    # Data minimization: the age gate already ran server-side above — the
    # minor's date of birth must NOT ride in the token (it ends up in URLs,
    # browser history, and access logs).
    guest_token = create_access_token(
        data={
            "guest": True,
            "guest_id": guest_id,
            "session_id": session_id,
        },
        secret_key=JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
        expires_delta=timedelta(seconds=GUEST_SESSION_DURATION + GUEST_TOKEN_GRACE),
    )

    return GuestSessionResponse(guest_token=guest_token, session_id=session_id)


# ---------------------------------------------------------------------------
# File upload + Claude Vision extraction
# ---------------------------------------------------------------------------

_ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf"}
_MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB per file
_MAX_FILES_PER_CALL = 5


class UploadResponse(BaseModel):
    files_saved: int
    problems_extracted: int
    problems: list[dict]


@router.post("/session/{session_id}/upload", response_model=UploadResponse)
async def upload_session_files(
    session_id: str,
    files: list[UploadFile] = File(...),
    user: User = Depends(require_student),
):
    """
    Upload problem-set images / PDFs to a pending tutor session.

    Files are saved to DATA_DIR/session_uploads/<session_id>/ and extracted
    via Claude Vision into structured problem dicts stored on the session.
    The upload directory is deleted when the session ends.

    Limits: 5 files per call, 10 MB each. Accepted: jpg, png, gif, webp, pdf.
    """
    from ws_session import get_session, update_session
    from agents.document_extractor import extract_problems
    from config import DATA_DIR

    # Auth: session must exist and belong to the calling user
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    upload_dir = DATA_DIR / "session_uploads" / session_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: list = []
    for file in files[:_MAX_FILES_PER_CALL]:
        filename = file.filename or f"upload_{len(saved_paths)}"
        # Sanitize: keep alphanumeric, dot, hyphen, underscore; cap at 100 chars
        safe_name = "".join(
            c for c in filename if c.isalnum() or c in "._-"
        )[:100] or f"upload_{len(saved_paths)}"
        suffix = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
        if f".{suffix}" not in _ALLOWED_SUFFIXES:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported file type '.{suffix}'. Allowed: jpg, png, gif, webp, pdf.",
            )

        content = await file.read()
        if len(content) > _MAX_FILE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File '{filename}' exceeds 10 MB limit.",
            )

        dest = upload_dir / safe_name
        dest.write_bytes(content)
        saved_paths.append(dest)

    # Extract problems via Claude Vision (async, best-effort)
    problems = await extract_problems(saved_paths)

    # Persist extracted problems on the session
    session.uploaded_problems = session.uploaded_problems + problems
    update_session(session)

    return UploadResponse(
        files_saved=len(saved_paths),
        problems_extracted=len(problems),
        problems=problems,
    )


def cleanup_session_uploads(session_id: str) -> None:
    """
    Delete session_uploads/<session_id>/ directory.
    Called from ws_router._end_session and the startup sweep.
    Silently swallowed — never blocks session cleanup.
    """
    try:
        from config import DATA_DIR
        import shutil
        upload_dir = DATA_DIR / "session_uploads" / session_id
        if upload_dir.exists():
            shutil.rmtree(upload_dir, ignore_errors=True)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Scratchpad validation
# ---------------------------------------------------------------------------

class ValidateRequest(BaseModel):
    session_id: str
    box: str = Field(..., pattern="^(reasoning|expression)$")
    content: str = Field(..., max_length=2000)
    context: Optional[str] = Field(default=None, max_length=500)


class ValidateResponse(BaseModel):
    valid: bool
    sympy_result: str   # 'valid' | 'invalid' | 'unknown' | 'reasoning'
    feedback: Optional[str] = None


@router.post("/validate", response_model=ValidateResponse)
async def validate_scratchpad(
    body: ValidateRequest,
    user: User = Depends(require_student),
):
    """
    Validate a scratchpad entry.

    reasoning box: always valid if non-empty.
    expression box: parsed with SymPy; invalid if parse fails.
    """
    if body.box == "reasoning":
        _persist_scratchpad_entry(body.session_id, "reasoning", body.content, "reasoning")
        return ValidateResponse(valid=True, sympy_result="reasoning")

    # Expression box — attempt SymPy parse
    result, feedback = _sympy_validate(body.content)
    _persist_scratchpad_entry(body.session_id, "expression", body.content, result)
    return ValidateResponse(valid=result != "invalid", sympy_result=result, feedback=feedback)


def _sympy_validate(expression: str) -> tuple[str, Optional[str]]:
    """
    Try to parse the expression with SymPy.
    Returns (result, feedback) where result is 'valid', 'invalid', or 'unknown'.
    """
    try:
        import sympy
        from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application

        transformations = standard_transformations + (implicit_multiplication_application,)

        # Handle equations (contains '=')
        if "=" in expression:
            parts = expression.split("=", 1)
            lhs = parse_expr(parts[0].strip(), transformations=transformations)
            rhs = parse_expr(parts[1].strip(), transformations=transformations)
            # Valid equation — both sides parse
            return "valid", None
        else:
            parsed = parse_expr(expression.strip(), transformations=transformations)
            return "valid", None
    except Exception as e:
        err = str(e)
        if "unexpected" in err.lower() or "invalid" in err.lower():
            return "invalid", "That expression couldn't be parsed. Check your notation."
        return "unknown", None


def _persist_scratchpad_entry(session_id: str, box: str, content: str, sympy_result: str) -> None:
    """Store scratchpad entry in DB if available."""
    from config import USE_DATABASE
    if not USE_DATABASE:
        return
    try:
        from db_models import ScrapbookEntryRecord
        from db_session import get_session
        db = get_session()
        try:
            record = ScrapbookEntryRecord(
                id=str(uuid4()),
                session_id=session_id,
                box=box,
                content=content,
                sympy_result=sympy_result,
            )
            db.add(record)
            db.commit()
        finally:
            db.close()
    except Exception:
        pass  # Non-critical — don't fail the request


# ---------------------------------------------------------------------------
# Scratchpad AI LaTeX conversion
# ---------------------------------------------------------------------------

class ConvertRequest(BaseModel):
    text: str = Field(..., max_length=4000)


class ConvertResponse(BaseModel):
    converted: str


@router.post("/convert", response_model=ConvertResponse)
async def convert_to_latex(
    body: ConvertRequest,
    user: User = Depends(require_student),
):
    """
    Use Claude Haiku to inject $...$ LaTeX delimiters around math in plain text.
    Falls back to the original text if conversion fails.
    """
    from config import ANTHROPIC_API_KEY
    if not ANTHROPIC_API_KEY or not body.text.strip():
        return ConvertResponse(converted=body.text)

    prompt = (
        "You are a LaTeX formatter for a math scratchpad.\n"
        "Wrap mathematical expressions in $...$ so they render with KaTeX.\n"
        "Rules:\n"
        "- Wrap variables, equations, and formulas in $...$\n"
        "- Keep English prose words outside the delimiters\n"
        "- Use proper LaTeX: \\sin, \\cos, \\frac{a}{b}, \\cdot, \\sqrt{}, \\prime, etc.\n"
        "- Preserve line breaks exactly\n"
        "- Return ONLY the converted text — no explanation, no markdown fences\n\n"
        "Examples:\n"
        "Input: outer function f(u) = sin(u), so f'(u) = cos(u)\n"
        "Output: outer function $f(u) = \\sin(u)$, so $f'(u) = \\cos(u)$\n\n"
        "Input: h'(x) = f'(g(x)) * g'(x) = cos(5x^3) * 15x^2\n"
        "Output: $h'(x) = f'(g(x)) \\cdot g'(x) = \\cos(5x^3) \\cdot 15x^2$\n\n"
        f"Input:\n{body.text}\n\nOutput:"
    )

    try:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        resp = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        return ConvertResponse(converted=resp.content[0].text.strip())
    except Exception:
        return ConvertResponse(converted=body.text)


# ---------------------------------------------------------------------------
# Validation dispute
# ---------------------------------------------------------------------------

class DisputeRequest(BaseModel):
    session_id: str
    expression: str = Field(..., max_length=2000)
    expected: Optional[str] = Field(default=None, max_length=500)


class DisputeResponse(BaseModel):
    accepted: bool
    method: str          # 'sympy_loose' | 'claude' | 'human_review'
    dispute_id: Optional[str] = None
    message: str


@router.post("/dispute", response_model=DisputeResponse)
async def dispute_validation(
    body: DisputeRequest,
    user: User = Depends(require_student),
):
    """
    "I think I'm right" dispute flow.

    1. SymPy loose equivalence check (simplify(a - b) == 0)
    2. If still fails, Claude evaluates
    3. If SymPy and Claude disagree → accept and log for human review
    """
    dispute_id = str(uuid4())

    # Step 1: SymPy loose check
    sympy_verdict = _sympy_loose_check(body.expression, body.expected)

    if sympy_verdict == "equivalent":
        _save_dispute(dispute_id, body.session_id, body.expression, body.expected,
                      "equivalent", None, True)
        return DisputeResponse(
            accepted=True,
            method="sympy_loose",
            dispute_id=dispute_id,
            message="You're right! The expressions are equivalent.",
        )

    # Step 2: Claude evaluation
    claude_verdict = await _claude_evaluate(body.expression, body.expected)

    if claude_verdict == "correct":
        # Claude says correct but SymPy said no → accept, flag for review
        _save_dispute(dispute_id, body.session_id, body.expression, body.expected,
                      sympy_verdict, claude_verdict, True)
        return DisputeResponse(
            accepted=True,
            method="human_review",
            dispute_id=dispute_id,
            message="We'll accept that — our system flagged it for review. Keep going!",
        )

    if claude_verdict == "incorrect":
        _save_dispute(dispute_id, body.session_id, body.expression, body.expected,
                      sympy_verdict, claude_verdict, False)
        return DisputeResponse(
            accepted=False,
            method="claude",
            dispute_id=dispute_id,
            message="Both our checks say that answer doesn't quite match. Want a hint?",
        )

    # Claude uncertain → accept and flag
    _save_dispute(dispute_id, body.session_id, body.expression, body.expected,
                  sympy_verdict, claude_verdict, True)
    return DisputeResponse(
        accepted=True,
        method="human_review",
        dispute_id=dispute_id,
        message="We'll give you the benefit of the doubt here — flagged for review.",
    )


def _sympy_loose_check(expression: str, expected: Optional[str]) -> str:
    """Return 'equivalent', 'not_equivalent', or 'error'."""
    if not expected:
        return "error"
    try:
        import sympy
        from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
        t = standard_transformations + (implicit_multiplication_application,)
        a = parse_expr(expression.strip(), transformations=t)
        b = parse_expr(expected.strip(), transformations=t)
        diff = sympy.simplify(a - b)
        return "equivalent" if diff == 0 else "not_equivalent"
    except Exception:
        return "error"


async def _claude_evaluate(expression: str, expected: Optional[str]) -> str:
    """Ask Claude if expression is mathematically equivalent to expected. Returns 'correct', 'incorrect', or 'uncertain'."""
    from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
    if not ANTHROPIC_API_KEY or not expected:
        return "uncertain"

    prompt = (
        f"Is this math expression equivalent to the expected answer?\n\n"
        f"Student's expression: {expression}\n"
        f"Expected answer: {expected}\n\n"
        f"Reply with exactly one word: correct, incorrect, or uncertain."
    )

    try:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        resp = await client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )
        word = resp.content[0].text.strip().lower()
        if "correct" in word and "in" not in word:
            return "correct"
        if "incorrect" in word:
            return "incorrect"
        return "uncertain"
    except Exception:
        return "uncertain"


def _save_dispute(
    dispute_id: str, session_id: str, expression: str, expected: Optional[str],
    sympy_loose: str, claude_verdict: Optional[str], accepted: bool,
) -> None:
    from config import USE_DATABASE
    if not USE_DATABASE:
        return
    try:
        from db_models import ValidationDisputeRecord
        from db_session import get_session
        db = get_session()
        try:
            record = ValidationDisputeRecord(
                id=dispute_id,
                session_id=session_id,
                expression=expression,
                expected=expected,
                sympy_loose=sympy_loose,
                claude_verdict=claude_verdict,
                accepted=accepted,
            )
            db.add(record)
            db.commit()
        finally:
            db.close()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Phase 3: Voice — STT (Deepgram) + TTS (ElevenLabs)
# ---------------------------------------------------------------------------

import functools
import re as _re

def _add_sentence_breaks(text: str) -> str:
    """Insert SSML break tags at sentence boundaries for natural pacing."""
    # After . ! ? followed by whitespace + capital letter or closing quote
    text = _re.sub(r'([.!?])\s+([A-Z\"‘’“”])', r'\1 <break time="450ms"/> \2', text)
    return text


def _expression_complexity(latex_text: str) -> int:
    """
    Rough complexity score of the ORIGINAL LaTeX (pre-conversion).
    Drives the slow-down rule: dense expressions (iterated integrals, chain
    rules, fundamental theorems) are spoken slower and more steadily.
    """
    score = 0
    score += latex_text.count("\\int")
    score += 2 * latex_text.count("\\iint") + 3 * latex_text.count("\\iiint")
    score += 2 * latex_text.count("\\oint")
    score += latex_text.count("\\frac")
    score += latex_text.count("\\partial")
    score += latex_text.count("\\sum") + latex_text.count("\\lim") + latex_text.count("\\prod")
    score += latex_text.count("\\sqrt")
    score += latex_text.count("\\nabla")
    return score


# ── Async TTS with an async-safe cache ────────────────────────────────────────
#
# The old implementation used synchronous httpx.post under functools.lru_cache:
# every synthesis blocked the entire event loop for up to 20s, freezing every
# live tutoring session in the process (audit C3). All ElevenLabs/Deepgram I/O
# now goes through a shared httpx.AsyncClient.

import asyncio as _asyncio

_TTS_CACHE: dict[tuple, bytes] = {}
_TTS_CACHE_MAX = 500
_TTS_CACHE_LOCK: Optional[_asyncio.Lock] = None
_HTTP_CLIENT: Optional["httpx.AsyncClient"] = None  # type: ignore[name-defined]


def _get_http_client():
    """Lazily create the shared AsyncClient (created on first use, inside the loop)."""
    global _HTTP_CLIENT
    import httpx
    if _HTTP_CLIENT is None or _HTTP_CLIENT.is_closed:
        _HTTP_CLIENT = httpx.AsyncClient(timeout=20.0)
    return _HTTP_CLIENT


def _get_tts_lock() -> _asyncio.Lock:
    global _TTS_CACHE_LOCK
    if _TTS_CACHE_LOCK is None:
        _TTS_CACHE_LOCK = _asyncio.Lock()
    return _TTS_CACHE_LOCK


def _elevenlabs_payload(text: str, speed: float, stability: float) -> dict:
    # Flash model by default: ~half the cost and lower latency than
    # multilingual_v2, quality is fine for tutoring speech (cost decision
    # 2026-06-12). Override with ELEVENLABS_MODEL for A/B.
    model_id = os.getenv("ELEVENLABS_MODEL", "eleven_flash_v2_5")
    return {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": 0.80,
            "style": 0.10,
            "use_speaker_boost": True,
            "speed": speed,
        },
    }


def _elevenlabs_headers() -> dict:
    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY", "")
    if not elevenlabs_key:
        raise HTTPException(status_code=503, detail="ElevenLabs API key not configured. Set ELEVENLABS_API_KEY.")
    return {"xi-api-key": elevenlabs_key, "Content-Type": "application/json"}


async def _tts_cached(text: str, voice_id: str, speed: float = 0.90, stability: float = 0.55) -> bytes:
    """Async ElevenLabs synthesis with a bounded in-memory cache."""
    key = (text, voice_id, speed, stability)
    async with _get_tts_lock():
        if key in _TTS_CACHE:
            return _TTS_CACHE[key]

    headers = _elevenlabs_headers()
    client = _get_http_client()
    resp = await client.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers=headers,
        json=_elevenlabs_payload(text, speed, stability),
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"ElevenLabs error: {resp.text[:200]}")

    audio = resp.content
    async with _get_tts_lock():
        if len(_TTS_CACHE) >= _TTS_CACHE_MAX:
            _TTS_CACHE.pop(next(iter(_TTS_CACHE)))
        _TTS_CACHE[key] = audio
    return audio


class SynthesizeRequest(BaseModel):
    text: str = Field(..., max_length=2000)


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    user: User = Depends(require_student),
):
    """
    Transcribe student speech to text using Deepgram Nova-2.

    Accepts audio/webm or audio/wav. Returns {text, confidence, low_confidence}.
    low_confidence is True when confidence < 0.7 — the UI should ask the student to repeat.
    """
    deepgram_key = os.getenv("DEEPGRAM_API_KEY", "")
    if not deepgram_key:
        raise HTTPException(status_code=503, detail="Deepgram API key not configured. Set DEEPGRAM_API_KEY.")

    audio_bytes = await file.read()
    if len(audio_bytes) > 10 * 1024 * 1024:  # 10 MB limit
        raise HTTPException(status_code=413, detail="Audio file too large (max 10 MB).")

    content_type = file.content_type or "audio/webm"

    try:
        client = _get_http_client()
        resp = await client.post(
            "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true",
            headers={
                "Authorization": f"Token {deepgram_key}",
                "Content-Type": content_type,
            },
            content=audio_bytes,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Deepgram error: {resp.text[:200]}")

        data = resp.json()
        channel = data.get("results", {}).get("channels", [{}])[0]
        alt = channel.get("alternatives", [{}])[0]
        transcript = alt.get("transcript", "").strip()
        confidence = float(alt.get("confidence", 0.0))

        return {
            "text": transcript if confidence >= 0.7 else None,
            "confidence": confidence,
            "low_confidence": confidence < 0.7,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Transcription failed: {exc}")


@router.post("/synthesize")
async def synthesize_speech(
    body: SynthesizeRequest,
    user: User = Depends(require_student),
    stream: int = 0,
):
    """
    Synthesize text to speech using ElevenLabs (default: eleven_flash_v2_5).

    LaTeX is converted to spoken English, sentence breaks are inserted for natural
    pacing, then audio is synthesized with naturalness tuning. Dense math
    (iterated integrals, chain rules) is spoken slower and more steadily.
    Responses are cached (same processed text + voice + settings = same bytes).

    ?stream=1 proxies ElevenLabs' chunked /stream endpoint so playback can begin
    on the first audio bytes (uncached; used by the voice pipeline for the
    first sentence of a turn).

    If LaTeX-to-speech conversion fails, this returns 502 and the client falls
    back to silent text — degraded speech (raw LaTeX tokens) is never synthesized.
    """
    from agents.latex_to_speech import latex_to_speech, SpeechConversionError
    from session_quota import check_tts_budget, record_tts_chars
    import rate_limit

    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel default
    raw_text = body.text.strip()

    # SECURITY (H1): per-user request-rate ceiling on TTS, independent of the
    # daily character budget — bounds a rapid scripted flood (each call bills
    # ElevenLabs). 30 syntheses/minute is far above genuine spoken-tutor cadence.
    allowed_rate, _ = rate_limit.hit(f"tts:{user.id}", 30, 60)
    if not allowed_rate:
        raise HTTPException(
            status_code=429,
            detail="Too many voice requests. Please slow down.",
        )

    # Daily per-user TTS character budget (cost control). Clients degrade to
    # silent text on any non-200, so hitting the cap is invisible-but-quiet.
    allowed, used_today, budget = check_tts_budget(user.id, len(raw_text))
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Daily voice budget reached ({used_today}/{budget} characters). "
                   "Voice returns tomorrow; text tutoring is unaffected.",
        )

    import time as _time
    import metrics as _metrics

    _t_l2s = _time.monotonic()
    try:
        spoken = await latex_to_speech(raw_text)
    except SpeechConversionError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Voice unavailable for this message (math-to-speech failed): {exc}",
        )
    _metrics.record_stage("server.latex_to_speech_ms",
                          (_time.monotonic() - _t_l2s) * 1000)
    spoken = _add_sentence_breaks(spoken)

    # Slow-down rule: complex expressions get a steadier, slower read
    if _expression_complexity(raw_text) >= 4:
        speed, stability = 0.85, 0.70
    else:
        speed, stability = 0.90, 0.55

    # ── Streaming path: chunked passthrough, playback starts on first bytes ──
    if stream:
        headers = _elevenlabs_headers()
        payload = _elevenlabs_payload(spoken, speed, stability)
        client = _get_http_client()
        record_tts_chars(user.id, len(raw_text))

        async def _proxy():
            _t0 = _time.monotonic()
            first = True
            try:
                async with client.stream(
                    "POST",
                    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream",
                    headers=headers,
                    json=payload,
                ) as resp:
                    if resp.status_code != 200:
                        return  # client falls back to silent text on short body
                    async for chunk in resp.aiter_bytes():
                        if first:
                            first = False
                            _metrics.record_stage(
                                "server.tts_first_byte_ms",
                                (_time.monotonic() - _t0) * 1000)
                        yield chunk
            except Exception:
                return

        return StreamingResponse(_proxy(), media_type="audio/mpeg")

    # ── Buffered path (cacheable) ─────────────────────────────────────────────
    _t_tts = _time.monotonic()
    try:
        audio_bytes = await _tts_cached(spoken, voice_id, speed, stability)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Speech synthesis failed: {exc}")
    _metrics.record_stage("server.tts_ms", (_time.monotonic() - _t_tts) * 1000)

    record_tts_chars(user.id, len(raw_text))

    return StreamingResponse(
        iter([audio_bytes]),
        media_type="audio/mpeg",
        headers={"Cache-Control": "public, max-age=3600"},
    )
