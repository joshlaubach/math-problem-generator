"""
Math-aware sentence splitting for the streaming voice pipeline.

Port of the frontend splitIntoSentences (tutor session page): never breaks
inside a $...$ LaTeX span, and only treats ./!/? as a boundary when followed
by end-of-text or by a space + capital/quote (so "3.14" and "e.g. x" survive).

Used server-side to chunk streaming Claude output into agent_sentence WS
messages, so TTS can start on sentence 1 while the model is still writing
sentence 3.
"""

from __future__ import annotations

_OPENERS = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ"‘’“”\'')


def split_sentences(text: str) -> list[str]:
    """Split text into sentences without breaking $...$ math spans."""
    parts: list[str] = []
    current = ""
    in_math = False
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "$":
            in_math = not in_math
            current += c
            i += 1
            continue
        if not in_math and c in ".!?":
            nxt = text[i + 1] if i + 1 < n else ""
            after = text[i + 2] if i + 2 < n else ""
            if not nxt or (nxt == " " and after and after in _OPENERS):
                s = (current + c).strip()
                if len(s) > 2:
                    parts.append(s)
                current = ""
                i += 2
                continue
            # Not a boundary (e.g. the '.' in 3.14) — falls through to the
            # single append below. The frontend original appended twice here,
            # turning "3.14" into "3..14" in TTS text; do not port that bug.
        current += c
        i += 1
    tail = current.strip()
    if len(tail) > 2:
        parts.append(tail)
    return parts if parts else ([text] if text.strip() else [])


class SentenceAccumulator:
    """
    Incremental splitter for streaming deltas: feed() text chunks, get back
    any sentences that are now complete; flush() returns the remainder.

    A sentence is only released once the *next* sentence has started (or on
    flush) — this mirrors split_sentences' lookahead rule exactly, because we
    re-split the whole buffer and hold back the last segment.
    """

    def __init__(self) -> None:
        self._buf = ""
        self._emitted = 0  # chars of _buf already released

    def feed(self, delta: str) -> list[str]:
        self._buf += delta
        pending = self._buf[self._emitted:]
        parts = split_sentences(pending)
        if len(parts) <= 1:
            return []
        # Release all but the last (possibly incomplete) segment
        complete = parts[:-1]
        released = ""
        idx = 0
        for s in complete:
            # advance past this sentence within `pending` (tolerate whitespace)
            found = pending.find(s, idx)
            if found == -1:
                # Defensive: re-splitting diverged; hold everything
                return []
            idx = found + len(s)
            released += s + " "
        self._emitted += idx
        return complete

    def flush(self) -> list[str]:
        pending = self._buf[self._emitted:]
        self._emitted = len(self._buf)
        return split_sentences(pending) if pending.strip() else []

    @property
    def full_text(self) -> str:
        return self._buf
