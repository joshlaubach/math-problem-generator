"""Debug: capture raw async response for failing unit intros."""
import sys, asyncio, json
sys.path.insert(0, '.')
from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
from topic_registry import COURSE_REGISTRY
from agents.unit_intro_writer import _SYSTEM, _PROMPT
from llm_anthropic_client import _call_with_backoff


async def debug_unit(unit_id: str) -> None:
    for course in COURSE_REGISTRY.values():
        if unit_id in course["units"]:
            udata = course["units"][unit_id]
            course_name = course["course_name"]
            break

    topics = [{"topic_id": tid, "topic_name": m.topic_name} for tid, m in udata["topics"].items()]
    topic_list = "\n".join(
        f"  {i+1}. [{t['topic_id']}] {t['topic_name']}"
        for i, t in enumerate(topics)
    )
    prompt = _PROMPT.format(
        course_name=course_name,
        unit_name=udata["unit_name"],
        topic_list=topic_list,
    )

    print(f"\n=== {unit_id}: {udata['unit_name']} ({len(topics)} topics) ===")
    raw = await _call_with_backoff(
        messages=[{"role": "user", "content": prompt}],
        system=_SYSTEM,
        max_tokens=1500,
    )
    print(f"Raw length: {len(raw)} chars")
    print(f"Starts with: {repr(raw[:80])}")
    print(f"Ends with:   {repr(raw[-80:])}")

    # Try parsing
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
        print("Stripped markdown fences")

    try:
        data = json.loads(text)
        print(f"JSON parse OK, keys: {list(data.keys())}")
    except json.JSONDecodeError as e:
        print(f"JSON parse FAILED: {e}")
        start, end = text.find("{"), text.rfind("}") + 1
        print(f"Bracket search: start={start}, end={end}, len={len(text)}")
        if start != -1 and end > start:
            try:
                data = json.loads(text[start:end])
                print(f"Bracket extraction OK, keys: {list(data.keys())}")
            except json.JSONDecodeError as e2:
                print(f"Bracket extraction FAILED: {e2}")
                # Find the problem area
                problem_pos = e2.pos if hasattr(e2, 'pos') else 0
                print(f"Problem near char {problem_pos}: {repr(text[max(0,problem_pos-50):problem_pos+50])}")


async def main():
    await asyncio.gather(debug_unit("pc_u01"), debug_unit("pc_u11"))

asyncio.run(main())
