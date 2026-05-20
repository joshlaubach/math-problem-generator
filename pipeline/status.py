"""
pipeline/status.py — Terminal dashboard showing pipeline progress.

Usage:
  python -m pipeline.status              # show all lessons
  python -m pipeline.status --course precalculus
  python -m pipeline.status --lesson pc_024
  python -m pipeline.status --watch      # refresh every 5s
"""
from __future__ import annotations
import argparse
import json
import os
import time
from pathlib import Path

from pipeline.state import read_all


# ANSI colour helpers
_R  = "\033[31m"   # red
_G  = "\033[32m"   # green
_Y  = "\033[33m"   # yellow
_C  = "\033[36m"   # cyan
_W  = "\033[37m"   # white
_B  = "\033[34m"   # blue
_DIM = "\033[2m"
_RST = "\033[0m"


STAGE_ICON = {
    "planned":      "[plan]",
    "generated":    "[gen] ",
    "corrected":    "[qc]  ",
    "rendered":     "[rend]",
    "audio_done":   "[aud] ",
    "assembled":    "[DONE]",
    "needs_review": "[WARN]",
}


def _bar(done: int, total: int, width: int = 30) -> str:
    filled = int(width * done / total) if total else 0
    return f"[{'#' * filled}{'.' * (width - filled)}] {done}/{total}"


def _render_lesson(lid: str, state: dict) -> str:
    stage    = state.get("stage", "pending")
    clips    = state.get("clips_done", [])
    icon     = STAGE_ICON.get(stage, "[ .. ]")
    review   = state.get("needs_review", False)
    color    = _R if review else (_G if stage == "assembled" else _Y if stage else _DIM)
    return f"  {color}{lid:<10}{_RST}  {icon} {stage:<14}  clips={len(clips)}/5"


def show(
    lesson_ids: list[str] | None = None,
    course: str | None = None,
) -> None:
    all_state = read_all()

    if lesson_ids:
        items = [(lid, all_state.get(lid, {})) for lid in lesson_ids]
    elif course:
        prefix = course[:2].lower() + "_"
        items = [(lid, s) for lid, s in sorted(all_state.items()) if lid.startswith(prefix)]
    else:
        items = sorted(all_state.items())

    if not items:
        print("  No lessons in state yet.")
        return

    total     = len(items)
    assembled = sum(1 for _, s in items if s.get("stage") == "assembled")
    errors    = sum(1 for _, s in items if s.get("needs_review"))

    print(f"\n{_C}{'-' * 60}{_RST}")
    print(f"  {_W}Manim Video Pipeline Status{_RST}  ({total} lessons tracked)")
    print(f"  {_G}assembled:{_RST} {assembled}/{total}   {_R}needs review:{_RST} {errors}")
    print(f"  {_bar(assembled, total)}")
    print(f"{_C}{'-' * 60}{_RST}")

    for lid, state in items:
        print(_render_lesson(lid, state))

    print(f"{_C}{'-' * 60}{_RST}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline status dashboard")
    group  = parser.add_mutually_exclusive_group()
    group.add_argument("--course", help="Course slug filter (e.g. precalculus)")
    group.add_argument("--lesson", help="Single lesson ID")
    parser.add_argument("--watch", action="store_true", help="Refresh every 5 seconds")
    args = parser.parse_args()

    lesson_ids = [args.lesson] if args.lesson else None

    if args.watch:
        try:
            while True:
                os.system("cls" if os.name == "nt" else "clear")
                show(lesson_ids=lesson_ids, course=args.course)
                print("  [Ctrl+C to exit]  refreshing every 5s …")
                time.sleep(5)
        except KeyboardInterrupt:
            pass
    else:
        show(lesson_ids=lesson_ids, course=args.course)


if __name__ == "__main__":
    main()
