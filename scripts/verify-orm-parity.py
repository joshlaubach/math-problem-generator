"""
CI guard: verify that the SQLAlchemy models in apps/api/db_models.py
are consistent with the Prisma schema in apps/web/prisma/schema.prisma.

Fails the build (exit code 1) if any Prisma model is entirely missing from
the SQLAlchemy models, or if the set of Prisma models grows without
a corresponding SQLAlchemy table.

Usage:
    python scripts/verify-orm-parity.py

Add to CI:
    - name: Verify ORM parity
      run: python scripts/verify-orm-parity.py
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
PRISMA_SCHEMA = REPO_ROOT / "apps" / "web" / "prisma" / "schema.prisma"
ORM_MODELS = REPO_ROOT / "apps" / "api" / "db_models.py"

# Prisma model name → expected SQLAlchemy __tablename__ (or aliases for renamed tables)
PRISMA_TO_SA_TABLE: dict[str, list[str]] = {
    "Course": ["courses"],
    "Unit": ["units"],
    "Topic": ["topics"],
    "VideoLink": ["video_links"],
    "Problem": ["problems"],
    "User": ["users"],
    "Attempt": ["attempts"],
    "Progress": ["progress"],
    "FlaggedProblem": ["flagged_problems"],
    "Classroom": ["classrooms"],
    "ClassroomMembership": ["classroom_memberships"],
    "Assignment": ["platform_assignments", "assignments"],
    "AssignmentSubmission": ["assignment_submissions"],
}


def parse_prisma_models(schema_text: str) -> set[str]:
    """Extract model names from Prisma schema."""
    return set(re.findall(r"^model\s+(\w+)\s*\{", schema_text, re.MULTILINE))


def parse_sa_tablenames(orm_text: str) -> set[str]:
    """Extract __tablename__ values from SQLAlchemy models."""
    return set(re.findall(r'__tablename__\s*=\s*["\'](\w+)["\']', orm_text))


def main() -> int:
    if not PRISMA_SCHEMA.exists():
        print(f"ERROR: Prisma schema not found at {PRISMA_SCHEMA}")
        return 1

    if not ORM_MODELS.exists():
        print(f"ERROR: SQLAlchemy models not found at {ORM_MODELS}")
        return 1

    prisma_models = parse_prisma_models(PRISMA_SCHEMA.read_text(encoding="utf-8"))
    sa_tables = parse_sa_tablenames(ORM_MODELS.read_text(encoding="utf-8"))

    print(f"Prisma models found: {sorted(prisma_models)}")
    print(f"SQLAlchemy tables found: {sorted(sa_tables)}")

    failures: list[str] = []
    for prisma_model, expected_tables in PRISMA_TO_SA_TABLE.items():
        if prisma_model not in prisma_models:
            # Prisma model was removed — that's a schema change, not a parity failure
            continue
        if not any(t in sa_tables for t in expected_tables):
            failures.append(
                f"  Prisma model '{prisma_model}' has no matching SQLAlchemy table "
                f"(expected one of: {expected_tables})"
            )

    # Check for Prisma models not in our mapping at all
    unmapped = prisma_models - set(PRISMA_TO_SA_TABLE.keys())
    for model in unmapped:
        failures.append(
            f"  Prisma model '{model}' is not mapped in verify-orm-parity.py — "
            f"add it to PRISMA_TO_SA_TABLE and create a SQLAlchemy model."
        )

    if failures:
        print("\nFAIL ORM parity check FAILED:")
        for f in failures:
            print(f)
        return 1

    print("\nOK ORM parity check passed — all Prisma models have SQLAlchemy counterparts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
