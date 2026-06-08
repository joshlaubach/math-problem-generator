# Josh's AI Math Tutor

A live AI tutoring platform for math students from pre-algebra through university level. Students work through problem sets with an AI tutor that watches what they draw, responds to their work, and guides them toward answers without giving them away.

## What it does

When a student starts a session, they upload a problem set or pick a topic from the curriculum. The tutor presents problems one at a time and engages Socratically — asking guiding questions, offering hints when the student is stuck, and evaluating their work when they submit an answer.

The tutor can see what the student draws on the shared whiteboard. If a student writes a wrong setup for a related rates problem, the tutor notices and places a correction annotation right next to the mistake. If they write a correct first step, the tutor confirms it and asks what comes next. This is the core interaction the platform is built around.

Students who prefer to work symbolically can type their steps as LaTeX in the Show My Work panel instead of drawing. The tutor evaluates each step and responds in chat.

Sessions run for one or two hours. At the end, the student gets a summary of what they covered, which topics need more work, and a set of practice problems to review before the next session.

## What's built

**Problem Generator** — Students and teachers can browse a full curriculum (pre-algebra through multivariable calculus, linear algebra, differential equations, statistics) and generate practice problems on any topic. This is the entry-level product; students access it with a subscription.

**AI Tutor Sessions** — Live sessions purchased as credits. The tutor is powered by Claude (Anthropic), runs over WebSockets for real-time interaction, and has a persistent whiteboard where it writes KaTeX-rendered math with GSAP animations. All tutor sessions include drawing recognition.

**Teacher tools** — Teachers can create classrooms, assign problem sets, and view student performance analytics per topic.

## Who it's for

Right now this is a solo project — I'm a math tutor and built this to scale my practice and figure out what AI tutoring can actually do well. The product is aimed at high school and college students working through math courses who want something closer to a real tutoring session than a chat window.

---

## For Engineers

### Stack

**Monorepo** — Turborepo with two apps: `apps/api/` (FastAPI, Python 3.10+) and `apps/web/` (Next.js 14, TypeScript, App Router).

**Backend** — FastAPI with WebSockets for tutor sessions. Claude (`claude-sonnet-4-6`) handles problem generation, Socratic responses, hint laddering, drawing recognition, and session summaries. PostgreSQL via SQLAlchemy (mirrored in Prisma for the frontend). Falls back to JSONL for local dev when `USE_DATABASE=false`.

**Frontend** — Next.js 14 App Router. Clerk for auth. KaTeX for math rendering, MathLive for interactive input. Fabric.js for the student drawing canvas. GSAP for the tutor whiteboard write animations.

**Auth** — Clerk in production. The backend supports a dual-auth window (legacy HS256 JWTs + Clerk JWTs simultaneously) controlled by `AUTH_PROVIDER` in env.

### Running it

```bash
# From repo root — starts both apps concurrently
npm run dev

# Backend only (port 8000)
npm run api:dev

# Frontend only (port 3000)
npm run web:dev
```

Copy `apps/api/.env.example` → `apps/api/.env` and `apps/web/.env.example` → `apps/web/.env.local` before first run. Required: `ANTHROPIC_API_KEY`, `DATABASE_URL` (or set `USE_DATABASE=false`), Clerk keys.

### Tests

```bash
# All backend tests
npm run api:test

# Single file
cd apps/api && python -m pytest tests/test_drawing_recognizer.py -v

# With coverage
cd apps/api && python -m pytest tests/ -v --cov
```

581 backend tests passing. Frontend tests are not yet implemented.

### Architecture notes

The tutor session runs over a single WebSocket (`/ws/tutor/{session_id}`). The session object lives in memory (with Redis for multi-instance deploys) and holds the conversation history, problem queue, and timer state. All LLM calls are async and non-blocking.

The whiteboard has two layers: a tutor layer (GSAP-animated KaTeX blocks, geometry renders via Mafs) and a student Fabric.js layer on top. When the student pauses drawing for 1.5 seconds, a snapshot is sent to the backend where Claude Vision analyzes it and returns a Socratic response plus an optional annotation instruction. Snapshots from the right-panel scratchpad are tagged `source: "scratchpad"` and get a chat response only — no whiteboard annotation.

The curriculum hierarchy (Course → Unit → Topic) is defined in Python dataclasses in `taxonomy.py`, not in the database. Each topic carries a `default_input_mode` that tells the frontend whether to open the Draw or Steps panel by default when a session starts.

Problem generation uses a solution-first approach: pick the target answer, build the equation around it, verify with SymPy, then send to the LLM to wrap in a word problem.

The full design plan lives at `.claude/plans/yes-mighty-moore.md`.
