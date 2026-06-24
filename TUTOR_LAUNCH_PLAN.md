# MathNotes AI — Tutor Launch Build Plan

> The existing `PLAN.md` holds DB-ownership decisions referenced by CLAUDE.md and is left
> intact. This is the launch build plan. Rename on request.

## Context

Josh is a professional math tutor turning this repo into a launchable AI tutoring
platform during summer break (June–Aug 2026), soft-launching in September via physical
flyers in a competitive local school district. There are no students yet, so the
September target is "credible enough to demo and sell," not "serve a roster."

The problem generator is done. The tutoring session is ~85% built but does not yet
behave like Josh at a whiteboard. Exam Mode (standalone) does not exist. This plan turns
the locked design decisions (two `/grill-me` sessions, saved in memory:
`project_tutor_design.md`, `project_business.md`) into an ordered, unambiguous build.

**Build order (Josh-confirmed):** 1) core tutoring session → 2) landing/demo/age gate →
3) pricing rework → 4) exam mode → 5) rewards/referral.

---

## Locked decisions (do not re-litigate)

- **Pedagogy:** EDGE method. 3-way error severity. Wrong final answer → student narrates
  steps by voice, tutor finds the error. Numeric answers by voice; complex algebra typed.
- **Voice:** Full open-mic VAD + barge-in **now** (not phased). 3–5s latency OK. Random
  filler clip ("Hmm.", "Okay.", "Interesting.", "I see.", "Let me think.") on speech-final.
  Model B (board + speech fire together).
- **Sessions:** Soft termination at problem boundaries, never mid-problem. Auto-reconnect
  for 10 min on drop, then end + email, credit not consumed.
- **Pricing:** **Two separate session products** — 1hr $20, 2hr $35 (each its own credit
  type). Exams: custom $4.99, SAT/AP preset $7.99. Round numbers only.
- **Quiz-Me:** keep the existing in-session "exam mode" behavior, **rename to "Quiz Me"**
  everywhere to free the word "Exam" for the standalone product.
- **Demo:** 30-min free guest tutor session, **DOB required before start** (under-13 blocked),
  one per week per IP / per email if account created.
- **Age:** 13+ with enforced parental consent, 18+ open. Add real DOB, not just a checkbox.
- **Mobile:** blocked below 768px on session/exam routes. No responsive work.
- **Exam Mode:** standalone proctored product — server-side timer, integrity monitor
  (flags for Josh, no auto-accusation), SAT/AP presets, static worked-solution review,
  AI-guided review sold as a session credit.

---

## Current state (ground truth from code)

| Area | State |
|---|---|
| Tutor LLM loop (Socratic/lesson/EDGE) | Fully wired: `agents/socratic.py`, `agents/tutor_engine.py`, `agents/tutor_guide.py`, `agents/prompt_assembler.py` |
| Voice | Push-to-talk **blob upload**: `VoiceInput.tsx` + `POST /tutor/transcribe` (Deepgram Nova-2) and `POST /tutor/synthesize` (ElevenLabs, `latex_to_speech`, LRU-cached). No streaming/VAD/barge-in. |
| `VoiceIndicator.tsx` | Built (5 states), not wired to a real pipeline |
| Answer check | `agents/answer_checker.py::check()` → `CheckAnswerResult(correct, equivalent_form, partial_credit_reason)`. No severity. |
| Whiteboard | `Whiteboard.tsx`: `wb_write` supports `latex` **and `scene: GeometryElement[]`**, plus `wb_clear`/`wb_new_section`/`wb_annotate_student`. `markIncorrect()` reddens the **last** block. |
| Session state | `ws_session.py::TutorSession` (Redis + in-mem). Handlers in `session_orchestrator.py`; lifecycle/timer in `ws_router.py`. |
| Timer | `_run_session_timer` warns at −10min then **hard-ends** after grace. Disconnect → `_end_session(reason="disconnect")` immediately (10-min credit refund only). |
| Quiz/"exam_mode" | In-session only: after 3 clean solves, proposes, clears board, blocks hints. `session_orchestrator._exam_mode_accept`, `tutor_engine.check_exam_readiness`. **No** standalone exam, timer, proctor, or report. |
| Credits/Stripe | Production-ready: `credit_router.py` BUNDLES **$40/$99/$149** generic credits; checkout + webhook + consume/restore. Envs `STRIPE_TUTOR_*_PRICE_ID`, `STRIPE_WEBHOOK_SECRET`. |
| Problem gen | `GET /generate?topic_id&difficulty` + `agents/generator.py::generate(GeneratorInput)`. No batch endpoint. `topic_registry.TOPIC_REGISTRY` enables topic queries. |
| Landing/demo | **Exists**: `app/page.tsx` marketing + `DemoProblem.tsx` one-problem demo via `/demo/problem`, `/demo/check-answer` (IP rate-limited, no auth). |
| Age | `onboarding/page.tsx` checkbox "13+/parent consented" → `POST /users/me/confirm-age` → `age_confirmed` bool + `consent_log`. **No DOB, no enforced consent.** Tutor WS gates on `age_confirmed` (`ws_router.py`). |
| Referral/rewards | Do not exist. (`reward` in code = session score only.) |

---

## Phase 1 — Core Tutoring Session

### 1.1 Voice pipeline — full open-mic VAD + barge-in
**Replace** push-to-talk blob flow with continuous streaming.

- **Backend audio WS** (new, e.g. `voice_ws.py`): browser streams mic frames; server proxies
  to **Deepgram streaming** (`wss://api.deepgram.com/v1/listen`, nova-2, interim + endpointing).
  On `speech_final`, hand the transcript to the existing tutor turn on the session socket.
  Reuse the Deepgram key/config already in `tutor_router.py`.
- **Browser VAD + capture** (rewrite `VoiceInput.tsx` → streaming hook; retire blob path in
  `tutor/session/[sessionId]/page.tsx::toggleVoice`): WebAudio capture + `@ricky0123/vad-web`
  (Silero). **800ms** sustained speech to confirm intent (avoids "hmm" cutting the tutor).
- **Barge-in:** when VAD fires during TTS, immediately stop the `<audio>` element and send an
  interrupt; tutor stops talking.
- **Filler clips:** pre-synthesize 5 clips at startup via existing `/synthesize` path; cache as
  audio buffers; play one at random on `speech_final`, before the LLM responds.
- **Streamed TTS (sentence-by-sentence):** stream Claude output; at each sentence boundary that
  does **not** split a `$...$` LaTeX span, run `agents/latex_to_speech.py` → ElevenLabs → enqueue
  to a sequential play queue. First audio in ~1.5s.
- **Spoken answers:** route by `answer_type` (already on the problem) — `numeric` accepted by
  voice; else tutor says "type it in the answer box." For spoken math, one Claude micro-call
  "spoken → LaTeX," then **confirm readback** via TTS on ambiguity, then existing
  `answer_checker.check()`.
- **Wire `VoiceIndicator.tsx`** states to real events: idle/recording/transcribing/thinking/speaking.

**Risk:** largest, highest-risk item; streaming + barge-in + interrupt races. Build and harden
this first.

### 1.2 Error severity (3-way) + correction behavior
- Extend `CheckAnswerResult` with `severity: "careless"|"method"|"fundamental"|None`. SymPy can't
  judge severity → on a **wrong** answer, add a lightweight LLM classifier (compare student answer
  to canonical/worked steps) in `answer_checker.py` (or a small `agents/severity.py`).
- Route response + board:
  - **careless** → no board change; lead into step-walkthrough ("look between step X and Y"); do
    **not** pinpoint. Change `Whiteboard.markIncorrect()` so careless never reddens a single line.
  - **method** → keep student work; emit `wb_new_section` + work the correct method beside it.
  - **fundamental** → emit `wb_clear` (currently never emitted by lesson mode) and start fresh.
- Severity also gates escalation instead of the flat `ESCALATION_THRESHOLD = 2` in `tutor_engine.py`.

### 1.3 Step-walkthrough mode
- New `ROLE_LAYERS["STEP_WALKTHROUGH"]` in `tutor_guide.py`; new `TutorSession.walkthrough_active`.
- Trigger after a wrong final answer (esp. careless/method). Each student message = one narrated
  step; tutor replies "okay, keep going" or "wait — look at that," until the error surfaces.
- Hook as a handler branch in `session_orchestrator.py` (sits alongside hint/answer handlers).

### 1.4 Soft session termination
- Replace hard cut in `ws_router.py::_run_session_timer`. At budget, set
  `TutorSession.time_budget_exhausted`; check it **only at problem boundaries** (post-solve) →
  run closing sequence ("any last questions?") → end. Keep an absolute safety cap (e.g. budget
  +30 min) to prevent runaway sessions.

### 1.5 Reconnect
- On WS disconnect, **do not** end immediately. Mark `disconnected_at`, keep session in Redis,
  start a 10-min timer. Reconnect (same `session_id` + token) → resume, replay conversation, tutor
  says a short resume line. After 10 min → `_end_session(reason="disconnect")` (credit restored) +
  interruption email. Frontend: auto-retry WS every 5s for 10 min (banner "Reconnecting…",
  indicator idle). Reuse `within_restore_window`, `get_session`.

### 1.6 Modality-switch cascade + exam-night honesty
- Track per-concept escalation count on the session. After 3 lesson cycles on one concept:
  (1) show the pre-authored intro diagram (1.7); (2) back up to a prerequisite (from
  `*_concepts.py` DAG); (3) terminal: if a test is <8h away → **honesty close** ("you're not
  ready, sleep, fresh start"); else suggest a break + flag the concept in the session summary.
- Add **exam date/time** to the intake form (`tutor/new`) when `why="test_prep"`; store
  `TutorSession.exam_datetime`. Honesty close fires when <8h + 3+ cycles. No blame logic.

### 1.7 Pre-authored intro diagrams (once per topic)
- Author `GeometryElement[]` **scenes** (reuse existing `wb_write { scene }` support — no new
  render engine) for ~30–40 key visual topics (completing the square, slope, etc.). Store on the
  cached lesson in `agents/lesson_store.py` (new `intro_scene` field). Emit once at Demonstrate
  entry, Model B (board + narration together).

### 1.8 Off-topic handling
- Add a short rule to `CONSTITUTION` in `tutor_guide.py`: brief in-character human reply + redirect
  (dinner → "something nutritious"; "write my essay" → one firm sentence, no lecture). Reflects
  Josh's voice (sleep, nutrition, independence).

### 1.9 Rename Quiz-Me
- Rename in-session "exam mode" → **"Quiz Me"** across `session_orchestrator.py` (`_exam_mode_accept`
  → `_quiz_accept`), `tutor_engine.py` (`check_exam_readiness`/proposal/start messages), WS message
  types (`exam_mode_propose/active/accept` → `quiz_*`), and frontend handlers. Frees "Exam" for Phase 4.

---

## Phase 2 — Landing, Demo, Age Gate

### 2.1 DOB + enforced parental consent
- Add `date_of_birth` to `users_models.py::User` and `db_models.py::UserRecord` (+ migration via
  `init_db` create_all). Collect DOB in `onboarding/page.tsx` (replace bare checkbox).
- Gate: **<13** hard block (no account); **13–17** account created but **locked** (`age_confirmed`
  stays False) until a parent completes consent; **18+** open. Wire consent into `parent_router.py`
  (the code already anticipates this: consent gate clears/sets `age_confirmed`). Make the
  parent-link **mandatory** for minors, not opt-in. New "account locked" UI state. Keep writing
  `consent_log`.

### 2.2 30-min guest demo tutor session
- New guest identity: short-lived signed **guest token** (not Clerk). DOB one-field screen first;
  <13 blocked. `TutorSession.session_tier="demo"`, `max_duration_seconds=1800`, no credit, no
  history persistence, no report. One per week **per IP and per email** (if account made mid-demo).
  Multi-kid same-network: show "first paid session is $20," not a hard block.
- Relax the `ws_router.py` auth gate to accept a valid guest token with DOB≥13 in lieu of
  `age_confirmed`. At 25min: soft spoken warning; at 30min: graceful modal → create account → buy.

### 2.3 Landing page updates
- `app/page.tsx` exists — update copy to the one-liner ("A patient, professional math tutor
  available 24/7 — at a fraction of the cost"), add a **"Try a full session free"** CTA → guest
  demo (alongside the existing one-problem `DemoProblem`), and show the new pricing. Do **not**
  claim "never gets a problem wrong."

### 2.4 Mobile gate
- Client-side viewport check (<768px) on `tutor/*` and future `exam/*` routes → "Sessions require a
  tablet or laptop" screen. (No `middleware.ts` today — implement in the route/layout.)

---

## Phase 3 — Pricing / Credits Rework

- Convert generic credits → **two typed products** in `credit_router.py`:
  `BUNDLES`/credit records gain a `kind: "1hr" | "2hr"`; 1hr=$20, 2hr=$35 (+ optional 5×1hr bundle
  $90–100). New Stripe price IDs (`STRIPE_SESSION_1HR_PRICE_ID`, `STRIPE_SESSION_2HR_PRICE_ID`).
  `consume_credit`/`has_available_credit`/`restore_credit` and `SessionCreditRecord` filter by kind;
  session create requires the matching kind for `session_type`. Update `/pricing` and webhook grant.

---

## Phase 4 — Exam Mode (standalone, new)

- **Model:** new `ExamAttempt` table (db_models) — user, template, problems (JSON), answers,
  `start_time`, `time_limit`, `submitted_at`, score, integrity flags. New `exam_router.py`.
- **Generation:** drive existing `agents/generator.py` from a **template JSON**
  `{name, total_problems, time_limit_minutes, calculator_allowed, concept_distribution:[{topic_area,
  weight, difficulty_range}]}`, selecting topics from `TOPIC_REGISTRY`. Presets: SAT Math, AP Calc
  AB, AP Calc BC, AP Statistics (+ custom). Structures aren't copyrightable — clean.
- **Timer:** **server-side only** — elapsed = `now − start_time`; never client-trusted. Untimed
  toggle. Reconnect resumes with remaining time; timer never pauses. Auto-submit on expiry;
  disconnect window logged.
- **Integrity monitor** (not "cheating detector"): frontend reports tab blur/focus, paste, and
  per-item timing; backend also flags performance anomalies vs. session history. **Flags surface to
  Josh; no automated accusation.**
- **Grading:** loop `answer_checker.check()` over submissions (stateless; no batch endpoint needed).
- **Review:** static worked solutions (already generated per problem) for wrong answers, self-serve;
  closing AI paragraph linking weak concepts → practice catalog. **AI-guided** review = a tutoring
  session credit, exam problems preloaded as context (reuses the session WS).
- **Pricing:** new exam Stripe products — custom $4.99, preset $7.99; exam-typed credit consumed on
  **submit**. Worked solutions are **not** paywalled (they drive the session upsell).

---

## Phase 5 — Rewards / Referral (after first paying customers)

- Referral code per user; reward triggers on a referred user's **first payment** (not signup).
  Free session after **5 paid** sessions or **3 paid referrals**. New table + webhook hook in the
  Stripe `checkout.session.completed` path. Zero punitive mechanics on any assignment UI.

---

## Cross-cutting notes

- Reuse, don't rebuild: `wb_write { scene }` for diagrams; `latex_to_speech` for TTS;
  `CheckAnswerResult.partial_credit_reason` slot near severity; `consent_log`, `parent_router`,
  Stripe checkout/webhook, `TOPIC_REGISTRY`, `prompt_assembler` caching.
- Naming: keep "Exam" exclusively for Phase 4 after the 1.9 rename.

## Verification

- **Voice (1.1):** run API + web locally; open a session; speak, confirm interim transcript,
  filler clip on stop, first TTS sentence <~2s, barge-in stops audio within ~300ms. Drive via the
  Claude Preview / Chrome MCP and check `preview_console_logs`/network for the Deepgram WS frames.
- **Severity/board (1.2):** submit a sign-flip vs. a wrong-method vs. nonsense answer; assert
  no-pinpoint / new-section / `wb_clear` respectively.
- **Walkthrough (1.3):** wrong final answer → narrate 3 steps; tutor catches the bad step.
- **Termination/reconnect (1.4/1.5):** let budget expire mid-problem (no cut; closes after solve);
  kill the socket, reconnect <10min (resumes), >10min (ends, no credit consumed, email).
- **Age/demo (2.1/2.2):** DOB <13 blocked; 13–17 locked until parent consent; guest demo ends at
  30min → signup→buy; second demo same week blocked.
- **Pricing (3):** buy 1hr vs 2hr; assert correct kind consumed; wrong-kind session blocked.
- **Exam (4):** generate preset; reload page mid-exam (timer keeps running); tab-switch flagged;
  submit → graded → review shows worked solutions for misses.
- Backend regression: `npm run api:test` (264+ tests) green after each phase; tests default
  `AUTH_PROVIDER=jwt`, `USE_DATABASE=false`.

## Timeline realism (10–12 weeks, solo)

Aggressive given full open-mic VAD now. Recommended sequencing: Phase 1 (esp. 1.1) consumes the
most calendar; Phases 2–3 unblock a sellable demo; Phase 4 can slip to October without users; Phase
5 follows first revenue. If 1.1 slips, the incremental voice fallback (filler + streamed TTS, keep
push-to-talk) is the pressure valve — but per decision, open-mic is the target.
