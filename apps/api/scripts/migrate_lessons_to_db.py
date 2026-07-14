"""
One-time migration: load cached topic lessons from data/topic_lessons/*.json
into the topic_lessons Postgres table.

The 866 generated lessons currently exist only as local files — the Railway
container filesystem is ephemeral, so production MUST serve lessons from
Postgres (see agents/lesson_store.py). Run this once against the prod database
(the script creates missing tables itself via init_db):

    cd apps/api
    USE_DATABASE=true DATABASE_URL=postgres://... python scripts/migrate_lessons_to_db.py
    python scripts/migrate_lessons_to_db.py --verify   # counts only, no writes

Idempotent: upserts by topic_id, so re-running is safe.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

LESSONS_DIR = pathlib.Path(__file__).resolve().parent.parent / "data" / "topic_lessons"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true",
                        help="Print file/DB counts and exit without writing")
    args = parser.parse_args()

    from config import USE_DATABASE
    if not USE_DATABASE:
        print("ERROR: USE_DATABASE is false. Set USE_DATABASE=true and DATABASE_URL "
              "to the target Postgres before running this migration.")
        return 1

    # Ensure tables exist (idempotent — SQLAlchemy owns the schema)
    from db_session import init_db
    init_db()

    from agents.lesson_store import lesson_count, save_lesson

    db_count, file_count = lesson_count()
    print(f"Lessons on disk: {file_count}   Lessons in DB: {db_count}")

    if args.verify:
        return 0

    files = sorted(LESSONS_DIR.glob("*.json")) if LESSONS_DIR.exists() else []
    if not files:
        print(f"ERROR: no lesson files found under {LESSONS_DIR}")
        return 1

    migrated, skipped = 0, 0
    for path in files:
        topic_id = path.stem
        try:
            content = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"  SKIP {topic_id}: unreadable JSON ({exc})")
            skipped += 1
            continue
        try:
            save_lesson(topic_id, content)
            migrated += 1
            if migrated % 100 == 0:
                print(f"  ...{migrated} migrated")
        except Exception as exc:
            print(f"  FAIL {topic_id}: {exc}")
            skipped += 1

    db_count_after, _ = lesson_count()
    print(f"Done. Migrated: {migrated}   Skipped: {skipped}   Now in DB: {db_count_after}")
    return 0 if skipped == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
