# AI Math Tutor — MVP Completion Spec

> Design finalized May 2026. All decisions recorded here supersede earlier ADRs for the tutor sub-system.

## Overview

Eight remaining sub-systems to complete the AI Math Tutor MVP. Build order matches data dependency flow: commitment screen → profiles → taxonomy → misconception tracking → context compression → email → Redis → whiteboard.

---

## 1. Session Commitment Warning Screen

**Problem:** Credits are charged silently the moment a WS connection opens. Students have no chance to confirm before being billed.

**Design:**
- Replace the current "Start" button in `/tutor/[topicId]/page.tsx` with a modal/screen that shows:
  - Session cost ("This session will use 1 credit — $40 value")
  - Three checkboxes (all must be checked to proceed):
    1. "I understand this session costs 1 credit"
    2. "I have uninterrupted time available"
    3. "Refunds are only issued for technical failures"
  - Two CTAs: **Start Now** (proceeds to WS connect) and **Schedule for Later** (opens date/time picker → fires Resend reminder → holds credit in SessionCreditRecord)
- Credit consumption stays at WS connect — the screen is a UX gate, not a transaction gate.
- `SessionCreditRecord` already exists in credit_router.py; no schema change needed.

---

## 2. Tutor Profiles

**Design:**
- Six profiles: James, Isaac, Robert, Sarah, Emily, Natalie (beta default: Josh)
- Schema (stored in Clerk user metadata, key `tutor_profile`): `{id: string, name: string, voice_id: string}`
- Voice IDs map to OpenAI TTS presets (alloy/echo/fable/onyx/nova/shimmer)
- Profile selection card shown once at first tutor session start; changeable in `/settings`
- Single system prompt in `socratic.py` with `{tutor_name}` injected at render time
- `TutorSession` dataclass gains `tutor_name: str` field
- WS connect reads profile from Clerk JWT metadata

**Profiles table:**

| ID | Name | Voice ID |
|---|---|---|
| josh | Josh | echo |
| james | James | onyx |
| isaac | Isaac | fable |
| robert | Robert | alloy |
| sarah | Sarah | nova |
| emily | Emily | shimmer |
| natalie | Natalie | nova |

---

## 3. Concept Label Taxonomy

**Design:**
- One-time generation script: `apps/api/scripts/generate_concept_taxonomy.py`
- Reads all `*_concepts.py` files, extracts concept names + descriptions
- Normalises to 3–6 word labels (e.g. "sign error when distributing")
- Output: `apps/api/data/concept_taxonomy.json` — format: `{course_id: [{id, label, description}]}`
- Runtime: loaded once at API startup into `CONCEPT_TAXONOMY` module-level dict
- Socratic agent receives `available_labels: list[str]` and must tag each wrong step with the closest matching label

---

## 4. Cross-Session Misconception Tracking

**Design:**

New Prisma table:
```prisma
model StudentConceptError {
  id          String   @id @default(cuid())
  userId      String
  conceptId   String
  count       Int      @default(1)
  lastSeenAt  DateTime @updatedAt
  @@unique([userId, conceptId])
}
```

SQLAlchemy mirror in `db_models.py`.

- WS session start: query top-5 errors for user → inject into Socratic system prompt as "Known weak concepts: ..."
- WS session end (background task): parse RL event log for this session → upsert `StudentConceptError` rows
- New repo method: `upsert_concept_error(user_id, concept_id)` in `repositories.py`

---

## 5. Problem-Boundary Context Compression

**Design:**
- Trigger: WS receives `problem_complete` event (answer marked correct, or student skips)
- Background asyncio task (non-blocking): calls `agents/session_summarizer.py` on current problem's conversation slice
- Summary bullet appended to `TutorSession.session_summary: list[str]`
- `TutorSession.conversation` trimmed to last 20 turns
- On next WS message: system prompt prepends summary bullets as context
- Token budget: each summary bullet ≤ 60 tokens; max 10 bullets retained (older bullets dropped)

---

## 6. Resend Email

**Design:**
- New module: `apps/api/email_service.py`
- `RESEND_API_KEY` in `.env`
- Two email types:
  - `send_session_report(user_email, summary_bullets, topic_name, duration_minutes)` — triggered as background task on WS close
  - `send_session_reminder(user_email, topic_name, scheduled_at_iso)` — triggered by "Schedule for Later" flow
- HTML templates inline in the module (no template files)
- Failure is silent (log + continue); never blocks session flow

---

## 7. Redis Session Storage

**Design:**
- `redis.asyncio` client; connection string via `REDIS_URL` env var (default `redis://localhost:6379`)
- Key pattern: `tutor:session:{session_id}` → JSON-serialised `TutorSession`
- TTL: `session_duration + GRACE_PERIOD_SECONDS + 120` (auto-expiry as safety net)
- API surface unchanged — all callers use `get_session / update_session / delete_session`
- Graceful fallback: if Redis unavailable, log warning and fall back to in-memory dict (dev mode)
- `ws_session.py` grows a `_redis_client` module-level async client; init called from `api.py` startup event

---

## 8. Interactive Whiteboard

**Design:**

### Layout
- Replaces the right-side scratchpad in `TutorChat.tsx`
- Full-width canvas: 65% of viewport height on desktop, collapsible on mobile
- Two stacked layers via `position: absolute`:
  - **Layer 0 (tutor):** `div` with GSAP-animated KaTeX content; z-index 5
  - **Layer 1 (student):** Fabric.js `canvas` for freehand; z-index 10; pointer events on
- Spatial convention: tutor content flows top-left → bottom-right; student zone implied lower-right quadrant (no hard divider)

### Tutor Zone (GSAP + KaTeX)
- Backend sends `{type: "whiteboard", action: "write", latex: "...", x: 0-100, y: 0-100}` WS messages
- Frontend renders KaTeX into a positioned `<span>`, then GSAP typewriter-animates it in (character reveal via `clipPath`)
- Mafs `<FunctionGraph>` rendered for plot actions: `{type: "whiteboard", action: "plot", fn: "x**2 - 3*x + 2", domain: [-2, 5]}`
- No-overlap: client tracks bounding boxes; new writes placed in next available row

### Student Zone (Fabric.js)
- Fabric.js canvas overlaid on tutor zone; transparent background
- Toolbar: pen / eraser / clear (Phosphor icons)
- MathLive input field docked at bottom of whiteboard for typed math expressions
- Student drawings persist in `TutorSession.whiteboard_state` (base64 PNG checkpoint every 30s)

### WS Protocol
New message types added to `ws_router.py`:
- Server → client: `{type: "whiteboard", action: "write"|"plot"|"clear", ...}`
- Client → server: `{type: "whiteboard_checkpoint", data: "<base64>"}` (every 30s)

### Socratic integration
- `edge_assessor.py` Demonstrate phase: fetches worked example from topic lesson → emits whiteboard write messages step by step
- Guide phase: tutor writes partial scaffold on whiteboard, asks student to complete

---

## Build & Test Protocol

Each sub-system ships with:
1. Backend unit or integration test (pytest)
2. Playwright smoke test confirming the happy-path UI flow
3. No new console errors at the browser level
