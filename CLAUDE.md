# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Monorepo Layout

Turborepo monorepo with two apps:
- `apps/api/` — FastAPI (Python 3.10+) backend
- `apps/web/` — Next.js 14 frontend (TypeScript, App Router)
- `data/` — JSONL fallback storage (dev only)
- `docs/` — Architecture Decision Records

## Commands

**Run everything (from repo root):**
```bash
npm run dev        # Start both apps concurrently
npm run build      # Build both apps
npm run test       # Run all tests
npm run lint       # Lint both apps
```

**Backend (from `apps/api/` or root):**
```bash
npm run api:dev    # uvicorn api:app --reload --port 8000
npm run api:test   # pytest tests/ -v

# Single test file or test:
cd apps/api && python -m pytest tests/test_api.py -v
cd apps/api && python -m pytest tests/test_api.py::test_health -v
cd apps/api && python -m pytest tests/ -v --cov
```

**Frontend (from `apps/web/` or root):**
```bash
npm run web:dev    # next dev (port 3000)
cd apps/web && npm run build
cd apps/web && npm run lint
```

## Environment Setup

**`apps/api/.env`** — copy from `.env.example`:
- `DATABASE_URL` — PostgreSQL; falls back to JSONL if `USE_DATABASE=false`
- `AUTH_PROVIDER` — `"jwt"` (tests/dev) or `"clerk"` (production)
- `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` — default model is `claude-sonnet-4-6`
- `CLERK_SECRET_KEY`, `CLERK_JWKS_URL` — required when `AUTH_PROVIDER=clerk`
- `LLM_PROVIDER` — `"anthropic"` (default) or `"openai"` (deprecated fallback)

**`apps/web/.env.local`** — copy from `.env.example`:
- `DATABASE_URL` — Prisma direct connection
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`
- `NEXT_PUBLIC_API_BASE_URL` — backend URL (default `http://localhost:8000`)
- `STRIPE_*` — payment keys for subscription tiers

## Architecture

### Backend (apps/api/)

**Problem generation pipeline:**
1. Client requests a problem via `GET /generate?topic=...&difficulty=...`
2. `api.py` routes to the topic-specific generator (e.g., `generator_linear_impl.py`)
3. Generator uses **solution-first** approach: pick target answer → build equation → verify with SymPy
4. LLM (`llm_anthropic_client.py`) generates word-problem wrappers, hints, and step-by-step solutions
5. Problems are persisted to PostgreSQL (`db_models.py`) or JSONL (`storage.py`) via the repository pattern

**Key design patterns:**
- **Factory pattern** — `llm_factory.py` selects the LLM provider; `repo_factory.py` selects DB vs. JSONL backend based on `USE_DATABASE`
- **Repository pattern** — all data access goes through `repositories.py`, `repositories_assignments.py`; never query directly in route handlers
- **Dependency injection** — auth (`auth_dependencies.py`), DB sessions (`db_session.py`), and repositories are all FastAPI `Depends()`
- **Dual-auth window** — `auth_dependencies.py` accepts both legacy HS256 JWTs and Clerk JWTs simultaneously during migration; controlled by `AUTH_PROVIDER`
- **Curriculum as code** — the full course→unit→topic hierarchy is defined in Python dataclasses in `taxonomy.py`, not in the database schema

**Auth roles:** `student`, `teacher`, `admin`. Teacher and admin roles gate `/teacher/*` endpoints. API Key (`X-API-Key` header) is also accepted for backward compatibility.

**Concept graph** (`concepts.py`, `concept_analytics.py`, `alg1_concepts.py`, etc.): each course has a companion `*_concepts.py` file defining prerequisite relationships as a DAG. This feeds adaptive difficulty (`adaptive.py`) and spaced-repetition progress (`db_models.py::Progress`).

### Frontend (apps/web/)

**Auth:** Clerk v6 wraps the entire app in `app/layout.tsx`. `middleware.ts` enforces authentication on protected routes with graceful degradation when Clerk keys are absent (dev mode).

**Data access split:** The frontend talks to the FastAPI backend via a typed HTTP client (`lib/api-client.ts`) for all problem/attempt/hint data. It uses Prisma directly (`lib/prisma.ts`) only for user/subscription data that lives in the same Postgres DB.

**Math rendering:** KaTeX for static display, MathLive for interactive input. The `MathInput.tsx` and `MathText.tsx` components abstract this; do not call KaTeX or MathLive directly in page code.

**Routing:** App Router with dynamic segments:
- `/catalog/[courseId]/[unitId]` — curriculum browser
- `/practice/[topicId]` — practice session (problem → hint → solution flow)
- `/dashboard` — student progress overview

### Database

Schema is owned by **Prisma** (`apps/web/prisma/schema.prisma`). SQLAlchemy models in `apps/api/db_models.py` mirror it for the Python side — keep both in sync when making schema changes.

Core hierarchy: `Course → Unit → Topic → Problem`. Progress and SRS state live in `Progress` (per user + topic). Classroom/assignment features use `Classroom`, `ClassroomMembership`, `Assignment`, `AssignmentSubmission`.

## Testing

- 264+ backend tests across 26 files in `apps/api/tests/`
- `conftest.py` provides pytest fixtures including DB session management
- Tests default to `AUTH_PROVIDER=jwt` and `USE_DATABASE=false` (JSONL) unless overridden
- Frontend tests are not yet implemented (planned Phase 8)

## Model Selection

The ADR (`docs/ADR-002-claude-model.md`) standardizes on `claude-sonnet-4-6` for all LLM calls. Override via `ANTHROPIC_MODEL` in the API env. The OpenAI client (`llm_openai_client.py`) is deprecated and will be removed.
