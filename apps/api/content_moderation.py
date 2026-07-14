"""
Content moderation pre-flight for student input (H3).

The tutor serves minors, so inbound chat is screened BEFORE it reaches the LLM.
The priority category is self-harm / crisis: a 13-year-old in distress must get
a safety response and a human-review flag, never a math deflection.

Design:
- A deterministic local screen (regex) runs first — no network, no latency,
  always available, and the part covered by tests. It is intentionally tuned
  to favor recall on crisis language (false positives are acceptable here; a
  missed crisis is not).
- `CRISIS_RESPONSE` is surfaced to the student in place of tutoring.
- Callers persist a FlaggedContentRecord and emit an admin alert (done in the
  transport layer so this module stays free of DB/IO side effects).

An optional LLM classifier can be layered on later for nuanced cases; the local
screen is the floor, not the ceiling.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# Category: self_harm — highest duty of care.
_SELF_HARM_PATTERNS = [
    r"\bkill(ing)?\s+my\s?self\b",
    r"\bkms\b",
    r"\bend(ing)?\s+(my\s+life|it\s+all)\b",
    r"\bwant\s+to\s+die\b",
    r"\bsuicid(e|al)\b",
    r"\bhurt(ing)?\s+my\s?self\b",
    r"\bself[\s-]?harm\b",
    r"\bcut(ting)?\s+my\s?self\b",
    r"\bno\s+reason\s+to\s+live\b",
    r"\bdon'?t\s+want\s+to\s+(be\s+here|live)\b",
]
# Category: violence_to_others
_VIOLENCE_PATTERNS = [
    r"\b(shoot|stab|kill|hurt|attack)\s+(everyone|them|him|her|people|my\s+(class|school|teacher))\b",
    r"\bbring\s+a\s+(gun|knife|weapon)\s+to\s+school\b",
    r"\bshoot\s+up\s+(the\s+)?school\b",
]

_COMPILED = [
    ("self_harm", [re.compile(p, re.IGNORECASE) for p in _SELF_HARM_PATTERNS]),
    ("violence_to_others", [re.compile(p, re.IGNORECASE) for p in _VIOLENCE_PATTERNS]),
]

CRISIS_RESPONSE = (
    "I'm really glad you told me, and I want to pause the math for a moment "
    "because you matter more than any problem set.\n\n"
    "If you're thinking about hurting yourself or you're in crisis, please reach "
    "out to someone who can help right now:\n"
    "• Call or text **988** (Suicide & Crisis Lifeline, US) — 24/7, free, confidential\n"
    "• Text **HOME** to **741741** (Crisis Text Line)\n"
    "• If you're in immediate danger, call **911** or go to the nearest emergency room\n\n"
    "If you can, please also tell a parent, teacher, or another adult you trust. "
    "You don't have to handle this alone. I'm here, and I'm not going anywhere."
)


@dataclass
class ModerationResult:
    flagged: bool
    category: Optional[str] = None
    matched_excerpt: Optional[str] = None
    response: Optional[str] = None  # what to show the student instead of tutoring


def screen(text: str) -> ModerationResult:
    """Run the deterministic crisis screen. Pure; never raises."""
    if not text:
        return ModerationResult(flagged=False)
    for category, patterns in _COMPILED:
        for pat in patterns:
            m = pat.search(text)
            if m:
                return ModerationResult(
                    flagged=True,
                    category=category,
                    matched_excerpt=m.group(0)[:120],
                    response=CRISIS_RESPONSE,
                )
    return ModerationResult(flagged=False)
