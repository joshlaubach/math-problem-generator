"""
Batch generate structured JSON lessons for all 818 topics.

Run from apps/api/:
    python scripts/generate_all_topic_lessons.py

Options:
    --workers N    Concurrent Claude calls (default: 8)
    --force        Regenerate even if cached (default: skip cached)
    --fallbacks    Only regenerate lessons that previously hit the fallback

Generates to: data/topic_lessons/{topic_id}.json

Reports:
    - Progress bar (topics completed / total)
    - Final summary: succeeded / fallbacks / errors
    - List of any fallback or error topic IDs
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

# Add apps/api to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATA_DIR
from topic_registry import TOPIC_REGISTRY
from agents.topic_lesson_writer import write_topic_lesson


LESSONS_DIR = DATA_DIR / "topic_lessons"
REQUIRED_FIELDS = {
    "hook", "concept", "anatomy", "worked_example",
    "partial_example", "practice_problems", "common_mistakes", "untested_variants",
}


def _is_cached(topic_id: str) -> bool:
    return (LESSONS_DIR / f"{topic_id}.json").exists()


def _is_fallback(topic_id: str) -> bool:
    path = LESSONS_DIR / f"{topic_id}.json"
    if not path.exists():
        return False
    try:
        d = json.loads(path.read_text())
        return bool(d.get("_fallback"))
    except Exception:
        return True  # Corrupt = treat as fallback


def _validate_fields(data: dict) -> list[str]:
    """Return list of missing required fields."""
    return [f for f in REQUIRED_FIELDS if f not in data or not data[f]]


async def generate_one(
    topic_id: str,
    topic_name: str,
    unit_name: str,
    course_name: str,
    semaphore: asyncio.Semaphore,
    results: dict,
    counter: list,
    total: int,
) -> None:
    """Generate and cache a single topic lesson, respecting the semaphore."""
    async with semaphore:
        # Small jitter to spread API calls and reduce rate-limit spikes
        await asyncio.sleep(0.5)
        try:
            lesson = await write_topic_lesson(
                topic_id=topic_id,
                topic_name=topic_name,
                unit_name=unit_name,
                course_name=course_name,
            )

            missing = _validate_fields(lesson)
            is_fallback = bool(lesson.get("_fallback")) or bool(missing)

            result = {
                "topic_id": topic_id,
                "topic_name": topic_name,
                "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
                "course_name": course_name,
                **lesson,
            }

            LESSONS_DIR.mkdir(parents=True, exist_ok=True)
            (LESSONS_DIR / f"{topic_id}.json").write_text(json.dumps(result, indent=2))

            if is_fallback:
                results["fallbacks"].append({"topic_id": topic_id, "topic_name": topic_name, "missing": missing})
            else:
                results["succeeded"] += 1

        except Exception as exc:
            results["errors"].append({"topic_id": topic_id, "topic_name": topic_name, "error": str(exc)[:120]})

        counter[0] += 1
        done = counter[0]
        elapsed = time.time() - results["start_time"]
        rate = done / elapsed if elapsed > 0 else 0
        remaining = (total - done) / rate if rate > 0 else 0

        bar_width = 30
        filled = int(bar_width * done / total)
        bar = "#" * filled + "-" * (bar_width - filled)
        pct = int(100 * done / total)
        print(
            f"\r[{bar}] {pct}% {done}/{total} "
            f"ok={results['succeeded']} "
            f"fallback={len(results['fallbacks'])} "
            f"err={len(results['errors'])} "
            f"~{remaining/60:.1f}m left   ",
            end="", flush=True
        )


async def main(workers: int, force: bool, fallbacks_only: bool) -> None:
    LESSONS_DIR.mkdir(parents=True, exist_ok=True)

    all_topics = list(TOPIC_REGISTRY.items())
    print(f"Total topics in registry: {len(all_topics)}")

    # Determine which to generate
    to_generate = []
    skipped = 0
    for topic_id, meta in all_topics:
        if fallbacks_only:
            if _is_fallback(topic_id):
                to_generate.append((topic_id, meta))
            else:
                skipped += 1
        elif force:
            to_generate.append((topic_id, meta))
        else:
            if _is_cached(topic_id) and not _is_fallback(topic_id):
                skipped += 1
            else:
                to_generate.append((topic_id, meta))

    print(f"Already cached (good): {skipped}")
    print(f"To generate: {len(to_generate)}")

    if not to_generate:
        print("Nothing to generate. Use --force to regenerate all.")
        return

    results = {
        "succeeded": 0,
        "fallbacks": [],
        "errors": [],
        "start_time": time.time(),
    }
    counter = [0]
    total = len(to_generate)

    semaphore = asyncio.Semaphore(workers)
    print(f"\nGenerating with {workers} concurrent workers...\n")

    tasks = [
        generate_one(
            topic_id=topic_id,
            topic_name=meta.topic_name,
            unit_name=meta.unit_name,
            course_name=meta.course_name,
            semaphore=semaphore,
            results=results,
            counter=counter,
            total=total,
        )
        for topic_id, meta in to_generate
    ]

    await asyncio.gather(*tasks)

    elapsed = time.time() - results["start_time"]
    print(f"\n\n{'='*60}")
    print(f"COMPLETE in {elapsed/60:.1f} minutes")
    print(f"{'='*60}")
    print(f"  OK  Succeeded:  {results['succeeded']}")
    print(f"  --  Fallbacks:  {len(results['fallbacks'])}")
    print(f"  XX  Errors:     {len(results['errors'])}")

    if results["fallbacks"]:
        print(f"\nFallback topics (JSON parse failed — lesson is stub):")
        for f in results["fallbacks"]:
            missing_str = f", missing: {f['missing']}" if f["missing"] else ""
            print(f"  [{f['topic_id']}] {f['topic_name']}{missing_str}")

    if results["errors"]:
        print(f"\nError topics (API call failed):")
        for e in results["errors"]:
            print(f"  [{e['topic_id']}] {e['topic_name']}: {e['error']}")

    # Write report
    report_path = LESSONS_DIR / "_generation_report.json"
    report = {
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "total_topics": len(all_topics),
        "generated": total,
        "skipped_cached": skipped,
        "succeeded": results["succeeded"],
        "fallback_count": len(results["fallbacks"]),
        "error_count": len(results["errors"]),
        "elapsed_minutes": round(elapsed / 60, 1),
        "fallbacks": results["fallbacks"],
        "errors": results["errors"],
    }
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport saved to {report_path}")

    # Exit with error code if any failures
    if results["fallbacks"] or results["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch generate topic lessons")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent Claude calls")
    parser.add_argument("--force", action="store_true", help="Regenerate all, even cached")
    parser.add_argument("--fallbacks", action="store_true", help="Only retry fallback lessons")
    args = parser.parse_args()

    asyncio.run(main(workers=args.workers, force=args.force, fallbacks_only=args.fallbacks))
