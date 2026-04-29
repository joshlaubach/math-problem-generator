# ADR-001: Monorepo Layout

**Date:** 2026-04-29  
**Status:** Accepted

## Context

The project started as two sibling directories (`backend/` and `frontend/`) under a single npm workspace root. The platform spec requires a Turborepo monorepo with `apps/api/` (FastAPI), `apps/web/` (Next.js 14), and `packages/shared-types/` (TypeScript).

## Decision

Migrate in-place using `git mv`:

- `backend/` → `apps/api/` (preserves full git history for 264 tests, 707 problems, generators, curriculum data)
- Build `apps/web/` fresh as a Next.js 14 App Router project; port React components from existing `frontend/` as each phase needs them
- Keep `frontend/` in place as a reference until `apps/web/` reaches feature parity (Phase 7), then delete it

Root tooling:
- **Turborepo 2.x** orchestrates `build`, `test`, `lint`, `dev` pipelines across all workspaces
- The Python backend participates via a minimal `apps/api/package.json` with `"test": "python -m pytest tests/ -v"` so turbo can run it
- `packages/shared-types/` holds TypeScript types shared between `apps/web/` and tooling; populated from Prisma schema in Phase 1 via `scripts/sync-types.ts`

## Consequences

- All 264 existing pytest tests run unchanged via `turbo run test` (or `cd apps/api && pytest`)
- Python imports within `apps/api/` are unaffected — `conftest.py` uses relative path resolution from `tests/` parent
- `frontend/` exists alongside `apps/web/` temporarily; this is intentional and documented here
