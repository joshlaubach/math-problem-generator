"""
One-time script to pre-generate lesson notes for all 125 units.

Usage:
    cd apps/api
    python scripts/generate_all_lessons.py

Output goes to apps/api/data/lesson_notes/{unit_id}.json.
Skips units that already have cached notes.
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure apps/api is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import LESSON_NOTES_DIR
from topic_registry import COURSE_REGISTRY, initialize_topic_registry  # noqa: F401 — side-effect import
from agents.lesson_writer import write_lesson


async def generate_unit(course_name: str, unit_id: str, unit_data: dict) -> None:
    cache_path = LESSON_NOTES_DIR / f"{unit_id}.json"
    if cache_path.exists():
        print(f"  [skip] {unit_id} — already cached")
        return

    unit_name = unit_data["unit_name"]
    topic_names = [t.topic_name for t in unit_data["topics"].values()]

    print(f"  [gen ] {unit_id}: {unit_name} ({len(topic_names)} topics)…", end=" ", flush=True)
    try:
        content = await write_lesson(
            unit_id=unit_id,
            unit_name=unit_name,
            course_name=course_name,
            topic_names=topic_names,
        )
        result = {
            "unit_id": unit_id,
            "unit_name": unit_name,
            "content": content,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        cache_path.write_text(json.dumps(result, indent=2))
        print("done")
    except Exception as e:
        print(f"FAILED: {e}")


async def main() -> None:
    LESSON_NOTES_DIR.mkdir(parents=True, exist_ok=True)
    total = sum(len(c["units"]) for c in COURSE_REGISTRY.values())
    print(f"Generating lesson notes for {total} units…\n")

    for course_data in COURSE_REGISTRY.values():
        course_name = course_data["course_name"]
        print(f"Course: {course_name}")
        for unit_id, unit_data in course_data["units"].items():
            await generate_unit(course_name, unit_id, unit_data)
        print()

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
