"""baseline

Revision ID: 17b0f1886919
Revises:
Create Date: 2026-06-25 00:00:00.000000

This is a *baseline* migration — a no-op placeholder that records the full
schema that was in production before Alembic was introduced.  All tables
were previously created (and maintained) by SQLAlchemy's create_all() in
db_session.py.

On a fresh database: run `alembic upgrade head` — subsequent migrations will
create the real schema.

On an existing production database: stamp it at this revision so Alembic
knows the baseline is already applied, then run upgrade head for any new
migrations:

    alembic stamp 17b0f1886919
    alembic upgrade head
"""

from __future__ import annotations
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "17b0f1886919"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Baseline — schema already exists on pre-Alembic databases.
    # New migrations added after this revision will contain real DDL.
    pass


def downgrade() -> None:
    # Cannot roll back below baseline.
    pass
