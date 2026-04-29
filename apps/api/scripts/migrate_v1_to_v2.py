"""
Migration script: v1 (backend/) schema → v2 (apps/api/) platform schema.

Usage:
    python scripts/migrate_v1_to_v2.py --dry-run    # Preview changes, no DB writes
    python scripts/migrate_v1_to_v2.py              # Execute migration

What this does:
  1. Reports existing table/row counts (--dry-run shows these without changes)
  2. Creates new tables via SQLAlchemy Base.metadata.create_all (uses CREATE IF NOT EXISTS)
  3. Migrates existing 'problems' JSONL rows to new Problem schema fields
  4. Creates ProgressRecord rows per (user_id, topic_id) from existing AttemptRecord data
  5. Adds clerk_user_id = NULL placeholder on existing UserRecord rows (populated in Phase 4)
  6. Adds tier = 'free' on existing UserRecord rows that don't have a tier

NOTE: This script is idempotent — running it twice is safe.
NOTE: Prisma migrations (schema.prisma) must be run separately via `prisma migrate dev`
      from apps/web/ before this script to create Prisma-managed tables.
"""

import argparse
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Add apps/api to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from db_models import (
    Base,
    UserRecord,
    ProblemRecord,
    AttemptRecord,
    ProgressRecord,
)
from db_session import get_engine


def get_engine_or_exit() -> object:
    engine = get_engine()
    if engine is None:
        print("ERROR: DATABASE_URL not set. Set it in .env before running.", flush=True)
        sys.exit(1)
    return engine


def report_counts(session) -> None:
    from sqlalchemy import text

    tables = [
        "users", "problems", "attempts", "assignments",
        "progress", "classrooms", "classroom_memberships",
        "platform_assignments", "assignment_submissions", "flagged_problems", "video_links",
    ]
    print("\n=== Current table row counts ===")
    for table in tables:
        try:
            count = session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"  {table}: {count}")
        except Exception:
            print(f"  {table}: (not yet created)")
    print()


def create_new_tables(engine, dry_run: bool) -> None:
    if dry_run:
        print("[DRY-RUN] Would create new tables: progress, classrooms, classroom_memberships,")
        print("          platform_assignments, assignment_submissions, flagged_problems, video_links")
        return
    print("Creating new tables (CREATE TABLE IF NOT EXISTS)...")
    Base.metadata.create_all(bind=engine, checkfirst=True)
    print("  Done.")


def backfill_user_fields(session, dry_run: bool) -> None:
    """Add default tier='free' to existing users that have no tier value."""
    from sqlalchemy import update

    users_needing_tier = session.query(UserRecord).filter(
        (UserRecord.tier == None) | (UserRecord.tier == "")  # noqa: E711
    ).count()

    if dry_run:
        print(f"[DRY-RUN] Would backfill tier='free' on {users_needing_tier} UserRecord rows.")
        return

    if users_needing_tier > 0:
        session.execute(
            update(UserRecord)
            .where((UserRecord.tier == None) | (UserRecord.tier == ""))  # noqa: E711
            .values(tier="free")
        )
        session.flush()
        print(f"  Backfilled tier='free' on {users_needing_tier} users.")


def backfill_progress_from_attempts(session, dry_run: bool) -> None:
    """Create a ProgressRecord per (user_id, topic_id) from AttemptRecord aggregates."""
    from sqlalchemy import func

    # Aggregate: for each (user_id, topic_id), compute success rate and attempt count
    results = (
        session.query(
            AttemptRecord.user_id,
            AttemptRecord.topic_id,
            func.count(AttemptRecord.id).label("total"),
            func.sum(AttemptRecord.is_correct.cast(int)).label("correct"),
            func.max(AttemptRecord.timestamp).label("last_seen"),
        )
        .group_by(AttemptRecord.user_id, AttemptRecord.topic_id)
        .all()
    )

    created = 0
    skipped = 0
    for row in results:
        existing = session.query(ProgressRecord).filter_by(
            user_id=row.user_id, topic_id=row.topic_id
        ).first()
        if existing:
            skipped += 1
            continue

        total = row.total or 1
        correct = int(row.correct or 0)
        mastery = min(1.0, correct / total)

        if not dry_run:
            record = ProgressRecord(
                id=str(uuid.uuid4()),
                user_id=row.user_id,
                topic_id=row.topic_id,
                mastery_score=mastery,
                last_reviewed_at=row.last_seen,
            )
            session.add(record)
        created += 1

    if dry_run:
        print(f"[DRY-RUN] Would create {created} ProgressRecord rows from AttemptRecord data.")
        print(f"[DRY-RUN] Would skip {skipped} (already exist).")
    else:
        session.flush()
        print(f"  Created {created} ProgressRecord rows, skipped {skipped}.")


def migrate_jsonl_problems(session, dry_run: bool) -> None:
    """
    Migrate legacy JSONL-style problems.jsonl to new ProblemRecord fields.
    Backfills: statement, answer, calc_tier, conceptual_diff, computational_diff.
    """
    jsonl_path = Path(__file__).parent.parent / "data" / "problems.jsonl"
    if not jsonl_path.exists():
        print("  problems.jsonl not found — skipping JSONL backfill.")
        return

    migrated = 0
    skipped = 0

    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                prob = json.loads(line)
            except json.JSONDecodeError:
                continue

            problem_id = prob.get("id")
            if not problem_id:
                continue

            record = session.query(ProblemRecord).filter_by(id=problem_id).first()
            if not record:
                skipped += 1
                continue

            # Only backfill if fields are still NULL
            if record.statement is None:
                if not dry_run:
                    record.statement = prob.get("prompt_latex", "")
                    final_ans = prob.get("final_answer", "")
                    if isinstance(final_ans, dict):
                        final_ans = final_ans.get("value", "")
                    record.answer = str(final_ans)
                    record.calc_tier = prob.get("calculator_mode", "none")
                    diff = prob.get("difficulty", 1)
                    record.conceptual_diff = min(5, max(1, int(diff)))
                    record.computational_diff = min(5, max(1, int(diff)))
                    record.verified = True
                    record.is_free = True
                migrated += 1

    if dry_run:
        print(f"[DRY-RUN] Would backfill {migrated} ProblemRecord rows from problems.jsonl.")
        print(f"[DRY-RUN] Would skip {skipped} (not found in DB).")
    else:
        session.flush()
        print(f"  Backfilled {migrated} ProblemRecord rows from JSONL, skipped {skipped}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Math Platform v1→v2 database migration")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    dry_run = args.dry_run
    mode = "DRY-RUN" if dry_run else "LIVE"
    print(f"=== Math Platform v1→v2 Migration ({mode}) ===\n")

    from sqlalchemy.orm import sessionmaker

    engine = get_engine_or_exit()
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        report_counts(session)
        create_new_tables(engine, dry_run)
        backfill_user_fields(session, dry_run)
        backfill_progress_from_attempts(session, dry_run)
        migrate_jsonl_problems(session, dry_run)

        if not dry_run:
            session.commit()
            print("\n✓ Migration committed successfully.")
        else:
            print("\n[DRY-RUN] No changes written. Run without --dry-run to apply.")

    except Exception as exc:
        session.rollback()
        print(f"\nERROR during migration: {exc}", flush=True)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
