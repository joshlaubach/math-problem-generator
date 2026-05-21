"""
pipeline/run.py — Batch orchestrator for the Manim video pipeline.

Usage examples:

  # Process a single lesson (all stages):
  python -m pipeline.run --lesson pc_024

  # Process all Pre-Calc lessons with 3 workers:
  python -m pipeline.run --course precalculus --workers 3

  # Resume only lessons that haven't been assembled yet:
  python -m pipeline.run --course precalculus --resume

  # Run only specific stages (e.g., re-generate audio):
  python -m pipeline.run --lesson pc_025 --stages s5_audio s6_assemble

  # Dry-run: print what would be processed without calling the API:
  python -m pipeline.run --course precalculus --dry-run
"""
from __future__ import annotations
import argparse
import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

from pipeline.config import (
    DEFAULT_WORKERS,
    GENERATED_DIR,
    CLIP_ORDER,
)
from pipeline.state import read_state, write_state

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pipeline.run")

# Stage execution order
ALL_STAGES = ["s1_plan", "s2_generate", "s3_correct", "s4_render", "s5_audio", "s6_assemble"]


# ---------------------------------------------------------------------------
# Lesson loading
# ---------------------------------------------------------------------------

def _load_lesson(lesson_id: str) -> dict | None:
    """
    Load a lesson JSON.  Tries the API data dir first, then falls back to
    a mock stub so the pipeline can be tested without the full backend running.
    """
    from pipeline.config import PIPELINE_ROOT
    # Real path (API-generated lessons)
    api_path = PIPELINE_ROOT.parent / "apps" / "api" / "data" / "topic_lessons" / f"{lesson_id}.json"
    if api_path.exists():
        with open(api_path, encoding="utf-8") as f:
            return json.load(f)

    # Pipeline-local cache (populated by a previous plan run)
    cache_path = Path(GENERATED_DIR) / lesson_id / "lesson.json"
    if cache_path.exists():
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)

    logger.warning("[%s] Lesson file not found — using minimal stub", lesson_id)
    return {
        "lesson_id":    lesson_id,
        "title":        lesson_id.replace("_", " ").title(),
        "topic":        lesson_id,
        "course":       "unknown",
        "worked_example": {"steps": []},
        "common_mistakes": [],
        "concept": "",
    }


def _get_course_lessons(course: str) -> list[str]:
    """Return lesson IDs for a given course slug."""
    # Pre-Calculus / Trigonometry — 72 lessons (pc_001 … pc_072)
    course_map = {
        "precalculus": [f"pc_{i:03d}" for i in range(1, 73)],
    }
    return course_map.get(course.lower(), [])


# ---------------------------------------------------------------------------
# Single-lesson pipeline execution
# ---------------------------------------------------------------------------

def run_lesson(
    lesson_id: str,
    stages: list[str],
    resume: bool = False,
) -> dict:
    """
    Execute the pipeline for one lesson.
    Returns a result dict: {lesson_id, status, duration_sec, error?}
    """
    from pipeline.stages import s1_plan, s2_generate, s3_correct, s4_render, s5_audio, s6_assemble
    stage_map = {
        "s1_plan":      s1_plan.run,
        "s2_generate":  s2_generate.run,
        "s3_correct":   s3_correct.run,
        "s4_render":    s4_render.run,
        "s5_audio":     s5_audio.run,
        "s6_assemble":  s6_assemble.run,
    }

    state = read_state(lesson_id)
    if resume and state.get("stage") == "assembled":
        logger.info("[%s] Already assembled — skipping", lesson_id)
        return {"lesson_id": lesson_id, "status": "skipped", "duration_sec": 0}

    lesson = _load_lesson(lesson_id)
    # Cache lesson JSON for later stages
    lesson_dir = Path(GENERATED_DIR) / lesson_id
    lesson_dir.mkdir(parents=True, exist_ok=True)
    with open(lesson_dir / "lesson.json", "w", encoding="utf-8") as f:
        json.dump(lesson, f, ensure_ascii=False, indent=2)

    t0 = time.time()
    try:
        for stage_name in stages:
            fn = stage_map[stage_name]
            logger.info("[%s] Running %s …", lesson_id, stage_name)

            # Stage 1 needs lesson data; others work from state
            if stage_name == "s1_plan":
                fn(lesson_id, lesson)
            else:
                fn(lesson_id)

        duration = time.time() - t0
        logger.info("[%s] Done in %.1fs", lesson_id, duration)
        return {"lesson_id": lesson_id, "status": "done", "duration_sec": duration}

    except Exception as exc:
        duration = time.time() - t0
        logger.error("[%s] Failed after %.1fs: %s", lesson_id, duration, exc, exc_info=True)
        return {"lesson_id": lesson_id, "status": "error", "duration_sec": duration, "error": str(exc)}


# ---------------------------------------------------------------------------
# Batch orchestrator
# ---------------------------------------------------------------------------

def run_batch(
    lesson_ids: list[str],
    stages: list[str],
    workers: int = DEFAULT_WORKERS,
    resume: bool = False,
    dry_run: bool = False,
) -> list[dict]:
    """
    Run the pipeline for multiple lessons in parallel.
    Returns list of result dicts.
    """
    if dry_run:
        for lid in lesson_ids:
            print(f"  would process: {lid}  stages={stages}")
        return []

    logger.info("Processing %d lessons, %d workers, stages=%s", len(lesson_ids), workers, stages)
    results = []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(run_lesson, lid, stages, resume): lid
            for lid in lesson_ids
        }
        for fut in as_completed(futures):
            lid    = futures[fut]
            result = fut.result()
            results.append(result)
            status = result["status"]
            dur    = result.get("duration_sec", 0)
            if status == "error":
                logger.error("[%s] FAILED: %s", lid, result.get("error", ""))
            else:
                logger.info("[%s] %s in %.1fs", lid, status.upper(), dur)

    done    = sum(1 for r in results if r["status"] == "done")
    errors  = sum(1 for r in results if r["status"] == "error")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    logger.info("Batch complete — done=%d  errors=%d  skipped=%d", done, errors, skipped)
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Manim lesson video pipeline")

    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--lesson",  help="Single lesson ID (e.g. pc_024)")
    target.add_argument("--course",  help="Course slug (e.g. precalculus)")
    target.add_argument("--ids",     nargs="+", help="Explicit list of lesson IDs")

    parser.add_argument("--stages",  nargs="+", default=ALL_STAGES,
                        choices=ALL_STAGES, help="Stages to run (default: all)")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS,
                        help=f"Parallel workers (default {DEFAULT_WORKERS})")
    parser.add_argument("--resume",  action="store_true",
                        help="Skip lessons already in 'assembled' state")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would run without calling any APIs")

    args = parser.parse_args()

    if args.lesson:
        lesson_ids = [args.lesson]
    elif args.course:
        lesson_ids = _get_course_lessons(args.course)
        if not lesson_ids:
            parser.error(f"Unknown course: {args.course!r}")
    else:
        lesson_ids = args.ids

    results = run_batch(
        lesson_ids=lesson_ids,
        stages=args.stages,
        workers=args.workers,
        resume=args.resume,
        dry_run=args.dry_run,
    )

    errors = [r for r in results if r["status"] == "error"]
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
