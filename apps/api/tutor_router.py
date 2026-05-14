"""
Tutor utility endpoints.

POST /tutor/validate   — SymPy expression validation for the scratchpad
POST /tutor/dispute    — "I think I'm right" dispute flow
POST /tutor/transcribe — Deepgram STT (Phase 3)
POST /tutor/synthesize — ElevenLabs TTS (Phase 3)
"""
from __future__ import annotations

import os
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth_dependencies import require_student, get_user_repository
from users_models import User

router = APIRouter(prefix="/tutor", tags=["tutor"])

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
from fastapi import UploadFile, File
from fastapi.responses import StreamingResponse

# Simple in-memory TTS cache: (text, voice_id) → bytes
@functools.lru_cache(maxsize=100)
def _tts_cached(text: str, voice_id: str) -> bytes:
    """Cached ElevenLabs synthesis — same text+voice returns cached bytes."""
    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY", "")
    if not elevenlabs_key:
        raise HTTPException(status_code=503, detail="ElevenLabs API key not configured. Set ELEVENLABS_API_KEY.")

    import httpx
    resp = httpx.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={
            "xi-api-key": elevenlabs_key,
            "Content-Type": "application/json",
        },
        json={
            "text": text,
            "model_id": "eleven_turbo_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        },
        timeout=15.0,
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"ElevenLabs error: {resp.text[:200]}")
    return resp.content


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

    import httpx
    try:
        resp = httpx.post(
            "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true",
            headers={
                "Authorization": f"Token {deepgram_key}",
                "Content-Type": content_type,
            },
            content=audio_bytes,
            timeout=20.0,
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
):
    """
    Synthesize text to speech using ElevenLabs Turbo v2.

    Returns audio/mpeg stream. Responses are cached (same text + voice = same bytes).
    """
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel default

    try:
        audio_bytes = _tts_cached(body.text.strip(), voice_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Speech synthesis failed: {exc}")

    return StreamingResponse(
        iter([audio_bytes]),
        media_type="audio/mpeg",
        headers={"Cache-Control": "public, max-age=3600"},
    )
