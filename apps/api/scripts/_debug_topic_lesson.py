"""Debug: capture raw async response for a failing topic lesson."""
import sys, asyncio, json, re
sys.path.insert(0, '.')
from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
from topic_registry import TOPIC_REGISTRY
from agents.topic_lesson_writer import _SYSTEM, _PROMPT, _fix_latex_backslashes
from llm_anthropic_client import _call_with_backoff

TARGET = "la_048"  # The Gram-Schmidt Process


async def main() -> None:
    meta = TOPIC_REGISTRY[TARGET]
    prompt = _PROMPT.format(
        topic_id=TARGET,
        topic_name=meta.topic_name,
        unit_name=meta.unit_name,
        course_name=meta.course_name,
    )

    print(f"Topic: {meta.topic_name}")
    raw = await _call_with_backoff(
        messages=[{"role": "user", "content": prompt}],
        system=_SYSTEM,
        max_tokens=4000,
        retries=1,
    )
    print(f"Raw length: {len(raw)} chars")

    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    # Try 1: plain parse
    try:
        json.loads(text)
        print("Parse 1 (plain): OK")
        return
    except json.JSONDecodeError as e:
        print(f"Parse 1 (plain): FAILED — {e}")
        ctx = text[max(0, e.pos - 60):e.pos + 60]
        print(f"  Context: {repr(ctx)}")

    # Try 2: after backslash fix
    fixed = _fix_latex_backslashes(text)
    try:
        json.loads(fixed)
        print("Parse 2 (backslash fix): OK")
        return
    except json.JSONDecodeError as e:
        print(f"Parse 2 (backslash fix): FAILED — {e}")
        ctx = fixed[max(0, e.pos - 60):e.pos + 60]
        print(f"  Context: {repr(ctx)}")

    # Try 3: bracket trim + backslash fix
    start, end = fixed.find("{"), fixed.rfind("}") + 1
    if start != -1 and end > start:
        try:
            json.loads(fixed[start:end])
            print("Parse 3 (trimmed+fixed): OK")
            return
        except json.JSONDecodeError as e:
            print(f"Parse 3 (trimmed+fixed): FAILED — {e}")
            ctx = fixed[max(0, e.pos - 60):e.pos + 60]
            print(f"  Context: {repr(ctx)}")

    print("\nAll parse attempts failed. Raw snippet around first error:")
    print(repr(text[1750:1900]))


asyncio.run(main())
