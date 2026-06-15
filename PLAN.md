# Math Problem Generator — AI Tutor Platform: Launch Plan

<!-- /autoplan restore point: /c/Users/joshu/.gstack/projects/joshlaubach-math-problem-generator/main-autoplan-restore-20260526-105355.md -->

## LAUNCH PLAN (locked 2026-06-12, supersedes phase ordering below)

**Definition of done:** first paying stranger completes a session you'd happily
watch the replay of. Phases 9–10 deferred until post-revenue.

**Revenue goal:** $10k/mo net by Dec 31, 2026 → ~$16-17k/mo revenue →
~165 families at $99/mo average. Public launch ~mid-August leaves ~4.5 months
of selling: ~35-40 net new families/month. September back-to-school is the one
seasonal tailwind — the August launch date protects it.

**Pricing shape (forced by the goal):** MEMBERSHIP-PRIMARY HYBRID.
- Membership is the product: $99/mo (N tutor sessions + unlimited practice,
  sessions roll over 1 month), $149 tier with more sessions. Front and center,
  default CTA everywhere, pitched on the post-session summary screen.
- Pack is the on-ramp: ~$35 single-session starter; after it, CTA = "keep going
  monthly" with the $35 credited to the first month. Packs exist to create
  members, never as an equal choice.
- Consequence: Stripe subscription billing (renewals, dunning, cancel) moves
  from fast-follow INTO L1 (~+1 week).

**Acquisition (starts during beta, not after launch):**
1. Referral loop through current families — give-a-month/get-a-month. Beta
   families are the seed. (committed)
2. Local schools — math departments at students' schools, tutoring-center
   partnerships. (committed)
3. Content — only with a low-effort pipeline (e.g., weekly: platform surfaces
   the most common misconception → Josh films a 60-second explainer). (opportunistic)
4. Paid ads — VETOED until beta yields LTV/churn numbers; edtech CAC eats $99
   subscriptions otherwise.
5. Accountant before year-end re: S-corp election ("after taxes" target).

### Locked decisions

| Branch | Decision |
|---|---|
| 7A orchestrator refactor | In, before beta. Characterization tests FIRST (WS integration suite, LLM mocked, one test per message type + 3 stateful flows), frozen wire protocol, post-refactor live-audit re-run (`scripts/audit_scenarios.py`, `scripts/audit_voice_battery.py`) |
| 7B adaptive engine | All four parts: mastery persistence (all 3 exit paths: solved/timeout/disconnect, delta clamped ±0.15), history briefing from last 3 sessions, session-start difficulty seeding from Progress, streak rules + SRS. Streak-triggered problems via background pre-generation (fire async at 2-of-3 streak; fall back to queued problem if not ready) |
| Revenue model | Credits for tutor sessions — DELETE the `PAID_TIERS` gate in ws_router (credits-only access; optional hard abuse ceiling). Practice free + existing caps at launch. Practice subscription = fast-follow #1. Parent credit-gifting = fast-follow #2 |
| Catalog | All 14 courses paid-tutor at launch (Josh tutors all professionally) |
| Problem supply | Lazy cache in Postgres: cross-student reuse, per-student dedup (served-problem IDs), async audit pass prunes bad cached problems. Seed hot topics from current student roster (list TBD) |
| Minors | 13+ student-owned accounts, age attestation at signup, privacy page honestly discloses Anthropic/Deepgram/ElevenLabs data flows. Under-13 parent-initiated flow deferred |
| Voice | Ships, cost-engineered: switch to `eleven_flash_v2_5`, per-session TTS character budget (~30k, degrade to text), daily per-user cap. Complexity-based slowdown already in |
| Data layer | Postgres-everything in prod (`USE_DATABASE=true`): 866 topic lessons migrated off laptop into PG (LAUNCH-BLOCKING — currently untracked local files), problem cache table, Railway volume for session uploads, Redis for live session state |
| Launch path | Private beta: 3–6 real students, free credits, read every transcript, exit on criteria (≈10 clean sessions, cross-session memory visibly working, measured cost/session survives $35 bundle math) |
| Pre-beta guardrails | Anthropic spend cap + billing alerts, 5xx error alerting, admin transcript view, auto-refund on failed sessions (< N min or server-error end → credit restored), PG backups enabled + one restore drill |
| Storefront trio | ToS (incl. written refund rule), support@ address, in-app "report a problem" (emails session ID). Required before Stripe live mode |
| Mobile | Small-viewport gate on tutor sessions ("needs a tablet or computer"); practice works on phones. Revisit from beta demand |

### Build order (starts ASAP)

- **L0 — Stand up prod (~1 wk):** Railway API + Vercel web + managed Postgres +
  Redis + domain. Clerk production instance. Stripe test-mode checkout end-to-end.
  `USE_DATABASE=true`. Migrate 866 lessons into PG (`scripts/migrate_lessons_to_db.py`).
  Spend cap + billing alerts + 5xx alerting. PG backups on.
  Schema note (decided 2026-06-12): SQLAlchemy owns the schema via `init_db()`
  at startup — do NOT run Prisma migrations in prod; schema.prisma is reference
  only (web never queries Prisma; models diverge structurally).
- **L1 — Launch-cut engineering (~2–3 wk):** delete PAID_TIERS gate; problem-cache
  table + dedup + async pruning; mastery persistence (all exit paths) + briefing +
  difficulty seeding; voice cost controls; 13+ attestation + privacy text; admin
  transcript view; failed-session auto-refund; mobile viewport gate;
  **Stripe subscription billing** (membership SKUs, renewal webhooks, dunning,
  cancel flow, pack→membership credit) — pulled in from fast-follow by the
  revenue goal.
- **L2 — Risky refactor, pre-beta (~1–2 wk):** WS characterization tests → 7A
  extraction (frozen protocol) → re-run live audits → streak rules + background
  regen + SRS on the clean structure.
- **L3 — Private beta (2–3 wk):** real students, transcript review loop, measure
  cost/session, prune problem cache. Draft ToS/refund/support during.
- **L4 — Stripe live. Public.** Fast-follows: practice subscription → parent
  gifting → Phases 9/10 as product depth.

---

## Product Summary

An AI-powered math tutoring platform. Students select a topic, start a timed session
(1hr or 2hr), and work through problems in a Socratic dialogue with an AI tutor.
The tutor never gives answers — it guides via questions, hints, and lesson explanations.

**Revenue model:** $35/$99/$149 tiers (Student / Honors / Classroom). Clerk auth,
Stripe payments. Primary differentiator: personalized tutor personas + adaptive difficulty
tied to a per-student knowledge graph.

---

## Current State (Phases 1–6 Complete)

### Backend (`apps/api/`)

- **FastAPI** with 50+ Python modules, ~18k LOC
- **Auth:** Dual-auth window accepting both HS256 JWT (legacy) and Clerk JWTs
- **Session lifecycle:** `ws_router.py` (WebSocket), `ws_session.py` (Redis/in-memory store),
  `tutor_router.py` (REST: create session, upload files, validate scratchpad, TTS/STT)
- **Agents built:**
  - `agents/socratic.py` — Socratic questioning agent (~80% complete)
  - `agents/tutor_engine.py` — Phase-aware engine: EDGE assessment, lesson mode,
    problem queue builder, exam mode detection (~50%)
  - `agents/answer_checker.py` — SymPy symbolic equivalence checker (~80% complete)
  - `agents/hint_scaffolder.py` — Pre-generated 4-hint ladder with tier gating (~100%)
  - `agents/session_summarizer.py` — Post-session summary: bullets, per-topic
    performance, practice problems (~80%)
  - `agents/document_extractor.py` — Claude Vision extraction from uploaded images/PDFs (~70%)
  - `agents/edge_assessor.py` — EDGE entry phase detection (~90%)
  - `agents/generator.py` + `generators/` — Problem generation pipeline (~70%)
  - `agents/orchestrator.py` — Stub only; `get_problem`, `get_hint`, `get_solution`
    raise `NotImplementedError` (~25%)
  - `agents/adaptive_engine.py` — `recommend()` raises `NotImplementedError` (~5%)
- **Knowledge graph:** 14 course-level concept DAGs (`*_concepts.py`) covering
  Pre-Algebra through Multivariable Calc, Linear Algebra, Proofs (~75%)
- **Problem generation:** 4 topic-specific generators + LLM fallback
- **Subscription:** `session_quota.py`, `credit_router.py`, tier checking
- **Voice:** Deepgram STT + ElevenLabs TTS endpoints

### Frontend (`apps/web/`)

- **Next.js 14 App Router**, Clerk v6, KaTeX + MathLive
- **Routes:** `/tutor/new` (intake form), `/tutor/session/[id]` (session shell),
  `/catalog`, `/practice/[topicId]`, `/dashboard`, `/pricing`
- **Session UI:** 65% whiteboard (GSAP canvas) + 35% chat sidebar + MathLive scratchpad
- **Post-session:** Summary screen with bullets, per-topic performance, downloadable whiteboard
- **Components:** `MathText`, `MathInput`, `MathScratchpad`, `Whiteboard`, `CalculatorSidebar`

### Database

- Prisma schema owns the structure; SQLAlchemy mirrors it for Python side
- `Progress` table: per-user + per-topic mastery score, SRS schedule
- `TutorSession`, `ScrapbookEntryRecord`, `ValidationDisputeRecord` in DB

---

## Phase 7: Session Orchestrator + Adaptive Engine (NEXT — highest priority)

### 7A: Extract Session Orchestrator from `ws_router.py`

**Problem:** `ws_router.py` is 1,238 lines mixing transport (WebSocket), business logic
(EDGE phases, escalation, exam mode), and session state. This coupling blocks all
future agent additions.

**Work:**
1. Move all business logic from `ws_router.py` into `agents/orchestrator.py`
   - `_get_problem`, `_get_hint`, `_get_solution` implementations
   - EDGE phase dispatch (currently inline in ws_router)
   - Escalation threshold logic (currently in `tutor_engine.py`)
2. `ws_router.py` becomes a thin WebSocket transport: receive message → call
   `orchestrator.handle()` → send response
3. Add proactive phase transitions:
   - After N correct solves → propose exam mode
   - After N wrong attempts → escalate to Teaching Agent (lesson mode)
4. Tests: `tests/test_orchestrator.py` covering all action types

**Files changed:** `apps/api/agents/orchestrator.py`, `apps/api/ws_router.py`,
`apps/api/agents/tutor_engine.py`

### 7B: Implement Adaptive Engine

**Problem:** `agents/adaptive_engine.py::recommend()` raises `NotImplementedError`.
No adaptive difficulty in live sessions — all students get the same problem difficulty.

**Work:**
1. Port mastery/streak rules from `apps/api/adaptive.py`:
   - 3 correct in a row → `mastery_score += 0.1`, `difficulty = min(5, current+1)`
   - 2 wrong in a row → `difficulty = max(1, current-1)`
   - Mastery caps at 1.0
2. Add spaced-repetition scheduling: `next_review_at = last_reviewed_at + timedelta(days=mastery_score * 7)`
3. Wire to `Progress` table: read current mastery at session start, write back after session
4. Wire to `session_summarizer.py`: after `per_topic_performance` → write mastery delta to DB
5. Generate `history_briefing` from last 3 sessions' weak nodes (already a field on `TutorSession`,
   but not populated)

**Files changed:** `apps/api/agents/adaptive_engine.py`, `apps/api/agents/session_summarizer.py`,
`apps/api/ws_router.py`, `apps/api/repositories.py`

---

## Phase 8: Solution Evaluation (Step-Level) + Session Memory Persistence

### 8A: Step-Level Solution Evaluation

**Problem:** `answer_checker.py` only checks final answers. No analysis of WHERE in
a multi-step solution the student went wrong. The system can't tell a student "your
error is on step 3 — you dropped a negative sign."

**Work:**
1. Accept `worked_steps: list[str]` from scratchpad (parsed via SymPy)
2. Check consecutive step equivalence: `simplify(step_n - step_{n-1}) != 0` → flag
3. Map error to misconception label from `concept_taxonomy.py`
4. Return `{error_step, error_type, misconception_label}` to Socratic Agent for targeted questioning
5. Fallback to Claude when error is conceptual (wrong formula, wrong setup)

**Files changed:** `apps/api/agents/answer_checker.py` (extend),
`apps/api/agents/solution_explainer.py` (implement)

### 8B: Persist Mastery Updates Post-Session

**Problem:** Session summarizer generates performance data but never writes it back to
the `Progress` table. Every session starts with stale mastery scores.

**Work:**
1. After `session_summarizer.summarize_session()` returns → write `per_topic_performance`
   delta to `Progress` table via `repositories.py`
2. Read last 3 sessions' weak nodes at session start and populate `TutorSession.history_briefing`
3. Persist `error_patterns` (misconception labels from step evaluator) to `Progress`

**Files changed:** `apps/api/agents/session_summarizer.py`,
`apps/api/ws_router.py`, `apps/api/repositories.py`

---

## Phase 9: Teaching Agent Multi-Representation + Metacognitive Reflection

### 9A: Multi-Representation Switching in Teaching Agent

**Problem:** `tutor_engine._lesson_response()` always responds with algebraic/textual
explanation. If a student doesn't respond to algebraic explanation twice, there's no
fallback strategy.

**Work:**
1. Track `last_representation` per session (algebraic / visual / verbal)
2. Same error type twice → switch to verbal ("think of it as...")
3. Third time → return structured `{type: "diagram", spec: {...}}` that frontend
   Whiteboard can render
4. Update lesson JSON schema to include `visual_spec` alongside `worked_example`

### 9B: Metacognitive Reflection Agent

**Work:** New agent `agents/metacognitive.py`
- Trigger after every 3 solved problems or at session end
- Mode A (Feynman): "Explain this concept as if teaching it to someone who's never seen it"
- Mode B (test-readiness): "What would your first move be if you saw this on an exam?"
- Parse student explanation for missing concept labels → flag to Orchestrator as gap

---

## Phase 10: Whiteboard Agent MVP + Visual Layer

### Minimum viable whiteboard protocol

**Problem:** The Whiteboard (GSAP canvas) receives LaTeX from the chat stream but has
no structured command protocol. No step-by-step reveal, no color semantics, no replay.

**Work:**
1. Define `WhiteboardCommand` message type over the WebSocket:
   `{type, id, x, y, latex, color, annotation}` — a scene graph for the canvas
2. Implement `WhiteboardAgent` server-side: converts Teaching Agent output into
   an ordered command sequence
3. Implement Step Reveal: emit `write_latex` commands with 600ms delay between steps
4. Color Agent: session-scoped registry — error=red, correct=green, focus=blue
5. Frontend: parse `whiteboard_command` message type and execute on GSAP canvas

**Files:** `apps/api/agents/whiteboard_agent.py` (new),
`apps/web/app/tutor/session/[sessionId]/page.tsx`,
`apps/web/components/Whiteboard.tsx`

---

## Non-Goals (explicitly deferred)

- Affect Monitor Agent — post-Phase 10
- Graphing Agent (Desmos) — post-Phase 10
- Diagram Agent — post-Phase 10
- Handwriting Simulation — frontend polish, post-Phase 10
- Parent Reporter — post-Phase 10
- OpenAI client removal (`llm_openai_client.py`) — cleanup, no urgency

---

## Technical Risks

1. **`ws_router.py` refactor (7A)** — 1,238 lines of intertwined transport + logic.
   Risk of regression. Requires comprehensive WebSocket integration tests before merging.
2. **Mastery persistence (7B, 8B)** — Writes to `Progress` table in production. Risk of
   mastery decay if the session_summarizer LLM misclassifies performance. Need a floor:
   never write mastery delta > ±0.15 from a single session.
3. **Step-level SymPy parsing (8A)** — Students write non-standard notation. SymPy parse
   failures must fall back gracefully (don't block the hint system).
4. **Whiteboard command protocol (10)** — Real-time ordering of canvas commands over
   WebSocket requires careful sequencing; frontend animation queue must handle out-of-order
   delivery.

---

## Success Criteria for Phase 7

- `ws_router.py` reduced below 300 lines (transport only)
- `orchestrator.handle()` passes all 6 action types with tests
- `adaptive_engine.recommend()` returns non-NotImplementedError for any user_id with Progress records
- History briefing populated at session start from real prior session data
- Mastery written back to `Progress` table at session end

---

## Appendix: Agent Build Status (from AGENTS.md)

| Agent | Status |
|---|---|
| Session Orchestrator | 40% |
| Curriculum Planner | 25% |
| Session Memory | 50% |
| Diagnostic | 30% |
| Solution Evaluation | 35% |
| Affect Monitor | 5% |
| Teaching Agent | 50% |
| Socratic Questioning | 80% |
| Problem Generation | 70% |
| Metacognitive Reflection | 0% |
| OCR / Parsing | 70% |
| Input Router | 40% |
| Whiteboard Agent | 0% |
| LaTeX Rendering | 30% |
| Graphing Agent | 5% |
| Diagram / Color / Annotation / Step Reveal / Replay | 0% |
| Parent Reporter | 20% |
| Student Model | 40% |
| Curriculum Knowledge Graph | 75% |
