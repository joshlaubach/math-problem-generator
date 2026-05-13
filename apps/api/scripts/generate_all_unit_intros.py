"""
Batch generate structured JSON unit introductions for all 129 units.

Run from apps/api/:
    python scripts/generate_all_unit_intros.py

Options:
    --workers N    Concurrent Claude calls (default: 8)
    --force        Regenerate even if cached (default: skip cached)
    --fallbacks    Only regenerate intros that previously hit the fallback

Generates to: data/unit_intros/{unit_id}.json

Reports:
    - Progress bar (units completed / total)
    - Final summary: succeeded / fallbacks / errors
    - List of any fallback or error unit IDs
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
from topic_registry import COURSE_REGISTRY  # auto-initializes on import
from agents.unit_intro_writer import write_unit_intro


INTROS_DIR = DATA_DIR / "unit_intros"
REQUIRED_FIELDS = {"hook", "concept", "topic_roadmap"}


def _is_cached(unit_id: str) -> bool:
    return (INTROS_DIR / f"{unit_id}.json").exists()


def _is_fallback(unit_id: str) -> bool:
    path = INTROS_DIR / f"{unit_id}.json"
    if not path.exists():
        return False
    try:
        d = json.loads(path.read_text())
        return bool(d.get("_fallback"))
    except Exception:
        return True  # Corrupt = treat as fallback


async def generate_one(
    unit_id: str,
    unit_name: str,
    course_name: str,
    topics: list[dict],
    semaphore: asyncio.Semaphore,
    results: dict,
    counter: list,
    total: int,
) -> None:
    async with semaphore:
        await asyncio.sleep(0.5)
        try:
            intro = await write_unit_intro(
                unit_id=unit_id,
                unit_name=unit_name,
                course_name=course_name,
                topics=topics,
            )

            missing = [f for f in REQUIRED_FIELDS if f not in intro or not intro[f]]
            is_fallback = bool(intro.get("_fallback")) or bool(missing)

            result = {
                "unit_id": unit_id,
                "unit_name": unit_name,
                "course_name": course_name,
                "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
                **intro,
            }

            INTROS_DIR.mkdir(parents=True, exist_ok=True)
            (INTROS_DIR / f"{unit_id}.json").write_text(json.dumps(result, indent=2))

            if is_fallback:
                results["fallbacks"].append({"unit_id": unit_id, "unit_name": unit_name, "missing": missing})
            else:
                results["succeeded"] += 1

        except Exception as exc:
            results["errors"].append({"unit_id": unit_id, "unit_name": unit_name, "error": str(exc)[:300]})

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
            end="", flush=True,
        )


async def main(workers: int, force: bool, fallbacks_only: bool) -> None:
    INTROS_DIR.mkdir(parents=True, exist_ok=True)

    # Collect all units from COURSE_REGISTRY
    all_units = []
    for course_data in COURSE_REGISTRY.values():
        course_name = course_data["course_name"]
        for unit_id, unit_data in course_data["units"].items():
            topics = [
                {"topic_id": tid, "topic_name": meta.topic_name}
                for tid, meta in unit_data["topics"].items()
            ]
            all_units.append({
                "unit_id": unit_id,
                "unit_name": unit_data["unit_name"],
                "course_name": course_name,
                "topics": topics,
            })

    print(f"Total units in registry: {len(all_units)}")

    to_generate = []
    skipped = 0
    for unit in all_units:
        uid = unit["unit_id"]
        if fallbacks_only:
            if _is_fallback(uid):
                to_generate.append(unit)
            else:
                skipped += 1
        elif force:
            to_generate.append(unit)
        else:
            if _is_cached(uid) and not _is_fallback(uid):
                skipped += 1
            else:
                to_generate.append(unit)

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
            unit_id=u["unit_id"],
            unit_name=u["unit_name"],
            course_name=u["course_name"],
            topics=u["topics"],
            semaphore=semaphore,
            results=results,
            counter=counter,
            total=total,
        )
        for u in to_generate
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
        print(f"\nFallback units (JSON parse failed — intro is stub):")
        for f in results["fallbacks"]:
            missing_str = f", missing: {f['missing']}" if f["missing"] else ""
            print(f"  [{f['unit_id']}] {f['unit_name']}{missing_str}")

    if results["errors"]:
        print(f"\nError units (API call failed):")
        for e in results["errors"]:
            print(f"  [{e['unit_id']}] {e['unit_name']}: {e['error']}")

    report_path = INTROS_DIR / "_generation_report.json"
    report = {
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "total_units": len(all_units),
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

    if results["fallbacks"] or results["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch generate unit introductions")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent Claude calls")
    parser.add_argument("--force", action="store_true", help="Regenerate all, even cached")
    parser.add_argument("--fallbacks", action="store_true", help="Only retry fallback intros")
    args = parser.parse_args()

    asyncio.run(main(workers=args.workers, force=args.force, fallbacks_only=args.fallbacks))
