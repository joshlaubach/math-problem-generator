# AGENTS.md — AI Math Tutor: Agent Architecture

Full specification for every agent in the tutor system. Each entry includes the
build status, the files that implement it today, and the exact contract for what
a complete implementation looks like.

**Status key:**
- ✅ Complete — production-ready
- 🔶 Partial — skeleton or critical paths missing
- ❌ Not built

---

## Core Orchestration

### Session Orchestrator
**Status:** 🔶 ~40% — routing shell exists; proactive phase management not wired

**Purpose:** The conductor. Manages session state, decides which agent to invoke
at each moment, enforces the "I do → We do → You do" (EDGE) progression, and
controls pacing. All other agents report to and receive instructions from this
agent.

**Current files:**
- `apps/api/agents/orchestrator.py` — action router; `get_problem`, `get_hint`,
  `get_solution` raise `NotImplementedError`
- `apps/api/ws_router.py` — real-time WebSocket path; currently handles most
  session logic directly (to be extracted into the Orchestrator)
- `apps/api/agents/tutor_engine.py` — EDGE phase machinery, escalation logic,
  problem queue builder, exam mode detection

**Inputs:**
```python
OrchestratorRequest(
    action: Literal["get_problem","check_answer","get_hint","get_solution",
                    "get_recommendation","get_analytics"],
    user_id: str,
    topic_id: str | None,
    problem_id: str | None,
    student_answer: str | None,
    hint_level: int | None,
)
```

**Outputs:** Dispatches to the appropriate specialist agent and returns its
result. Also mutates session state (hint_level, attempts, consecutive_no_progress,
exam_mode).

**What remains:**
- Implement `_get_problem`, `_get_hint`, `_get_solution` in `orchestrator.py`
- Extract the WebSocket message-dispatch loop from `ws_router.py` into the
  Orchestrator so that ws_router is a thin transport layer only
- Add proactive phase transitions: after N correct solves → propose exam mode;
  after N wrong attempts → escalate to Teaching Agent

---

### Curriculum Planner Agent
**Status:** 🔶 ~25% — problem queue built at session start; no prerequisite gating

**Purpose:** Given diagnostic output + student model + session context (topics
requested, why, notes), decides what to teach in a session and in what order.
Queries the knowledge graph to verify prerequisite mastery before advancing to
new concepts.

**Current files:**
- `apps/api/agents/tutor_engine.py` → `build_problem_queue()` — generates 1-2
  problems per topic_id in session order; freeform topics via LLM-only Mode B

**Inputs:**
```python
{
    "session": TutorSession,          # topic_ids, class_name, why, notes, difficulty
    "student_model": StudentModel,    # mastery per concept node
    "knowledge_graph": ConceptGraph,  # prerequisite DAG
}
```

**Outputs:**
```python
{
    "ordered_problem_queue": list[GeneratedProblem],
    "prerequisite_gaps": list[str],   # concept nodes to address first
    "rationale": str,                  # why this ordering
}
```

**What remains:**
- Before adding a topic to the queue, check `Progress.mastery_score` for its
  prerequisite nodes (from `*_concepts.py` DAG); if any gap < 0.4 → insert
  prerequisite problem first
- Accept `test_date` from intake form; back-calculate topics to prioritise given
  the time remaining
- Re-plan mid-session when Diagnostic Agent signals a discovered gap

---

### Session Memory Agent
**Status:** 🔶 ~50% — end-of-session summary built; cross-session mastery update missing

**Purpose:** Handles read/write to the persistent student model. After every
session, summarises what was covered, what improved, and what remains weak.
Updates knowledge graph mastery scores. Makes the system longitudinal rather than
stateless.

**Current files:**
- `apps/api/agents/session_summarizer.py` — LLM-based; returns
  `{bullets, per_topic_performance, practice_problems}`; called at session end
  from `ws_router._end_session()`
- `apps/api/ws_session.py` → `TutorSession.session_summary` and
  `TutorSession.history_briefing` — mid-session bullet accumulation; briefing
  injected into Socratic system prompt at next session start

**Inputs:**
```python
summarize_session(
    topic_name, mode, conversation, problems_attempted,
    problems_solved, hints_used, duration_seconds,
    topics_covered, session_summary_bullets,
)
```

**Outputs (schema):**
```json
{
  "bullets": ["...", "...", "..."],
  "per_topic_performance": {"Topic": "strong|needs_work|attempted"},
  "practice_problems": ["...", "..."]
}
```

**What remains:**
- After `summarize_session()` returns, write `per_topic_performance` back to
  `Progress` table: for each topic marked "strong" → `mastery_score += 0.05`;
  "needs_work" → `mastery_score -= 0.05` (clamp 0–1)
- Populate `history_briefing` at session start from last 3 sessions' bullets for
  weak nodes — this plumbing exists in `TutorSession` but the DB read isn't wired
- Add a `generate_parent_report()` method (feeds the Parent Reporter Agent)

---

## Diagnostic & Assessment

### Diagnostic Agent
**Status:** 🔶 ~30% — EDGE entry phase implemented; continuous in-session diagnostics not built

**Purpose:** Runs at session start and continuously throughout. Analyses student
responses, worked solutions, and response latency to update the student model.
Answers: what does this student actually not understand, and why?

**Current files:**
- `apps/api/agents/edge_assessor.py` — LLM call that classifies the student's
  opening message into an EDGE phase (explain / demonstrate / guide / enable) and
  returns a diagnostic question
- `apps/api/agents/adaptive_engine.py` — skeleton only; `recommend()` raises
  `NotImplementedError`

**Inputs (edge_assessor):**
```python
assess_entry_phase(
    topic_name, course_name, mode,
    student_message, conversation_history,
) → {phase, diagnostic_question, reasoning}
```

**What remains:**
- Implement `adaptive_engine.recommend()`: port mastery/streak rules from
  `apps/api/adaptive.py` (80%/60% thresholds); add spaced-repetition scheduling
- Wire continuous diagnostics: after every `check_answer` result → update
  `consecutive_no_progress` (already tracked in `TutorSession`); after every
  incorrect attempt → tag with the closest misconception label from
  `concept_taxonomy.py` → persist to `Progress.error_patterns`
- Add response-latency tracking: record `submitted_at` on each student message,
  compare against topic mean; very fast wrong answers → confidence miscalibration
  signal; very slow correct answers → working memory load signal

---

### Solution Evaluation Agent
**Status:** 🔶 ~35% — answer correctness solid; step-level error localisation not built

**Purpose:** Takes a student's worked solution, parses each step, compares against
all valid solution paths (not just one "correct" method), and identifies the exact
step and underlying misconception where reasoning broke down.

**Current files:**
- `apps/api/agents/answer_checker.py` — SymPy symbolic equivalence (exact match →
  symbolic simplify → numeric approximation → trig identity); handles LaTeX, `x = val`
  form, `^` → `**` conversion
- `apps/api/tutor_router.py` → `/validate` and `/dispute` — scratchpad validation +
  SymPy loose check + Claude fallback for disputes

**Inputs:**
```python
check(
    student_answer: str,    # LaTeX or plain math
    canonical_answer: str,
    answer_type: str,       # 'algebraic' | 'numeric' | 'set'
) → CheckAnswerResult(correct, equivalent_form, partial_credit_reason)
```

**What remains (full Solution Evaluation):**
- Accept a `worked_steps: list[str]` from the scratchpad, not just a final answer
- Parse each step with SymPy; compare consecutive steps for algebraic equivalence;
  flag the first step where `simplify(step_n - step_{n-1})` is not valid (sign
  flip, dropped term, illegal operation)
- Map the error to a misconception label from `concept_taxonomy.py`; return
  `{error_step: int, error_type: str, misconception_label: str}`
- For non-algebraic errors (setup errors, wrong formula chosen) — fallback to
  Claude with the worked steps and canonical approach as context
- No Wolfram Alpha needed; SymPy handles the algebra; Claude handles the
  conceptual-error classification

---

### Affect Monitor Agent
**Status:** ❌ ~5% — single passive rule in Socratic prompt; no dedicated detection

**Purpose:** Lightweight, runs in parallel always. Watches for frustration or
disengagement signals — response latency, terse replies, repeated errors on easy
problems, explicit frustration statements. Signals the Orchestrator to slow down,
switch topics, or adjust tone.

**Current files:**
- `apps/api/agents/socratic.py` — system prompt rule: "If the student expresses
  frustration, acknowledge it warmly in one sentence, then redirect"
  (passive; not proactive detection)

**Target interface:**
```python
AffectSignal = Literal["frustrated", "disengaged", "confused", "confident", "neutral"]

def assess_affect(
    message: str,
    response_latency_seconds: float,
    recent_attempts: list[dict],   # last 5 attempts: {correct, hints_used}
    consecutive_errors: int,
) → AffectSignal
```

**What to build:**
- Deterministic heuristics first (no LLM): 3+ consecutive errors on problems below
  current mastery level → "frustrated"; message length < 5 chars for 2+ turns →
  "disengaged"; explicit keywords ("i dont get it", "this makes no sense") →
  "frustrated"
- When signal ≠ "neutral" → emit to Orchestrator; Orchestrator decides: slow
  down (reduce difficulty by 1), switch to a different topic, or inject an
  encouraging message
- Distress flag: explicit statements of distress beyond academic frustration
  ("i hate myself", "i want to give up") → log separately, surface in parent
  report with timestamp (no LLM judgement — keyword list only)

---

## Teaching & Interaction

### Teaching Agent
**Status:** 🔶 ~50% — lesson-mode fallback built; no multi-representation switching

**Purpose:** Generates explanations, analogies, and visual descriptions matched to
the student's inferred learning style. Never gives answers — only explanations and
examples. Switches representation (algebraic → visual → verbal) if the student
isn't responding to the current approach.

**Current files:**
- `apps/api/agents/tutor_engine.py` → `_lesson_response()` — escalation-triggered
  lesson mode; pulls `worked_example` from cached `topic_lessons/<id>.json`;
  Claude Sonnet 4.6 with 600-token cap
- `apps/api/data/topic_lessons/` — structured JSON lessons per topic (hook,
  concept, anatomy, worked_example, partial_example, practice_problems,
  common_mistakes)

**Inputs:**
```python
generate_lesson_response(
    session: TutorSession,
    student_message: str,
    force_lesson: bool,
    representation: Literal["algebraic","visual","verbal"] = "algebraic",
) → str
```

**What remains:**
- Track which representation was last used per session; if student makes the same
  error type twice with algebraic representation → switch to verbal; 3rd time →
  switch to visual (currently all three collapse to `_lesson_response`)
- Visual representation: return structured JSON `{type: "diagram"|"graph"|"table",
  spec: {...}}` that the Whiteboard Agent can render — not just text
- Add a "think aloud" mode: instead of explaining, demonstrate thinking ("What do
  I notice about this equation? I see a quadratic — my instinct is to factor...")

---

### Socratic Questioning Agent
**Status:** ✅ ~80% — well-built; minor enhancements remaining

**Purpose:** Distinct from the Teaching Agent. Its only job is generating the right
guiding question or minimal hint when a student is stuck — calibrated to give the
least help needed to unblock the student, never the full solution.

**Current files:**
- `apps/api/agents/socratic.py` — stateless per-call; uses concept misconception
  labels, hint ladder (as internal context only, never quoted), wrong attempts,
  session summary bullets, and cross-session `history_briefing`

**Inputs:**
```python
respond(
    problem_statement: str,
    conversation: list[dict],
    student_message: str,
    hint_ladder: list[str],
    hint_level: int,
    wrong_attempts: list[str],
    tutor_name: str,
    session_summary: list[str] | None,
    topic_id: str | None,
    history_briefing: str,
) → str   # always ends with "?"
```

**What remains:**
- Detect when the student is re-phrasing the same wrong idea and escalate to the
  Orchestrator (currently handled by `consecutive_no_progress` counter but the
  signal isn't clean)
- Add a `confidence_probe` mode: occasionally (every 3rd correct response) ask
  "Could you explain why that works?" — this feeds the Metacognitive Reflection
  Agent

---

### Problem Generation Agent
**Status:** 🔶 ~70% — generation pipeline solid; adaptive difficulty targeting incomplete

**Purpose:** Creates practice problems at the correct difficulty level targeting
specific weak nodes in the knowledge graph. Ensures problems are solvable,
unambiguous, correctly formatted, and progressively harder as mastery increases.

**Current files:**
- `apps/api/agents/generator.py` — LLM + SymPy solution-first pipeline
- `apps/api/generators/` — topic-specific implementations: `linear.py`,
  `inequalities.py`, `sat_math.py`, `ap_calculus.py`
- `apps/api/agents/verifier.py` — post-generation SymPy verification
- `apps/api/agents/debate.py` — optional adversarial quality check

**Inputs:**
```python
GeneratorInput(
    topic: str,
    course: str,
    unit: str,
    conceptual_diff: int,    # 1–5
    computational_diff: int, # 1–5
    calc_tier: Literal["none","scientific","graphing","cas"],
)
```

**Outputs:**
```python
GeneratedProblem(
    statement: str,
    answer: str,
    worked_steps: list[WorkedStep],
    hint_ladder: list[str],   # exactly 4 hints
    distractors: list[Distractor],  # exactly 3 wrong answers with mistake labels
)
```

**What remains:**
- Accept a `target_misconception_label` parameter from the Diagnostic Agent;
  generate a problem that specifically exercises the identified misconception
- Add a "novel context" flag: same mathematical structure but new word-problem
  wrapper (so students can't pattern-match from memory)
- Wire the generator to pull from a problem bank first (if a matching cached
  problem exists) before generating fresh — reduces LLM cost

---

### Metacognitive Reflection Agent
**Status:** ❌ Not built

**Purpose:** Prompts the student to explain concepts back in their own words
(Feynman technique) at the end of practice blocks. Surfaces lingering confusion
and builds self-assessment habits.

**Target interface:**
```python
async def generate_reflection_prompt(
    topic_name: str,
    concepts_covered: list[str],
    student_mastery: dict[str, float],
    tutor_name: str,
) → str
```

**What to build:**
- Trigger after every 3 solved problems or at session end
- Two modes: **Feynman** ("Explain this concept as if you're teaching it to
  someone who's never seen it") and **test-readiness** ("What would your first
  move be if you saw this on an exam?")
- Parse student's explanation for key missing terms or misconceptions; if a
  required concept label is absent → flag to Orchestrator as a gap
- Light touch — max 2 sentences prompt, never a quiz

---

## Input Processing

### OCR / Parsing Agent
**Status:** 🔶 ~70% — Claude Vision for uploaded files; no live stylus / handwriting path

**Purpose:** Converts student handwritten or typed work into structured LaTeX/MathML
that the Solution Evaluation Agent can process. Handles messy notation, crossed-out
steps, and non-standard formatting.

**Current files:**
- `apps/api/agents/document_extractor.py` — Claude Vision; accepts JPEG, PNG, GIF,
  WebP, PDF (via PyMuPDF); returns `[{number, statement_latex, points}]`
- Route: `POST /tutor/session/{session_id}/upload`

**Inputs:**
```python
extract_problems(
    file_paths: list[Path],
) → list[{number: int, statement_latex: str, points: int | None}]
```

**What remains:**
- Live stylus path: accept `InkML` or SVG stroke data from the frontend scratchpad
  and submit to Claude Vision (render strokes to PNG in the browser before upload)
- Step extraction: when a student uploads a worked solution (not just a problem
  statement), extract each step separately — `[{step_number, expression_latex,
  annotation}]` — so the Solution Evaluation Agent can analyse step-by-step
- No Mathpix API needed — Claude Vision handles this adequately

---

### Input Router Agent
**Status:** 🔶 ~40% — file upload routing exists; real-time typing and stylus paths not wired

**Purpose:** Determines which input modality the student used (photo upload, stylus
strokes, typed math) and routes it to the appropriate parser.

**Current files:**
- `apps/api/tutor_router.py` — `POST /session/{id}/upload` routes to
  `document_extractor.extract_problems()`
- Frontend: `MathInput.tsx` handles typed math via MathLive; scratchpad handles
  stylus via Tiptap

**Target routing table:**
| Input type | Detection | Route to |
|---|---|---|
| File upload (image/PDF) | `content-type` is image or PDF | `document_extractor` |
| Typed LaTeX | MathLive input box | Direct to Solution Evaluation Agent |
| Typed natural language | Text box, no LaTeX delimiters | `/convert` → LaTeX → Solution Evaluation Agent |
| Stylus strokes | Tiptap canvas data | Render PNG → `document_extractor` |

**What remains:**
- Add a WebSocket message type `{type: "scratchpad_submit", content, modality}`
  that routes through the Input Router before hitting the Solution Evaluation Agent
- Route freeform text answers through the `/convert` LaTeX normaliser before
  SymPy parsing

---

## Presentation Layer

### Whiteboard Agent
**Status:** ❌ Not built (frontend GSAP canvas exists; no scene-graph orchestrator)

**Purpose:** The spatial orchestrator for the visual canvas. Decides what gets
written where, manages layout, erases and reorganises content as the session
progresses. All other visual agents submit render instructions to this agent
rather than drawing independently.

**Target interface (WebSocket message type):**
```typescript
// Agent emits; frontend executes
type WhiteboardCommand =
  | { type: "write_latex"; id: string; x: number; y: number; latex: string }
  | { type: "erase"; id: string }
  | { type: "highlight"; id: string; color: string }
  | { type: "arrow"; from: string; to: string; label?: string }
  | { type: "clear_region"; region: "left"|"right"|"all" }
  | { type: "graph"; id: string; spec: GraphSpec }
  | { type: "diagram"; id: string; spec: DiagramSpec }
```

**Layout rules:**
- Left panel: current problem + student scratchpad
- Right panel: tutor working area (Whiteboard Agent owns this)
- Top strip: progress indicators (Color Agent writes here)
- Each `id` is a stable handle — subsequent commands on the same `id` update
  in place rather than appending

**What to build:**
- A `WhiteboardState` dict mapping `id → {x, y, content, visible}` maintained
  server-side so the Replay Agent can reconstruct any moment
- A command queue flushed to the WebSocket after each tutor turn
- Layout manager: track approximate y-coordinate usage and scroll/reflow when
  the right panel fills

---

### LaTeX Rendering Agent
**Status:** 🔶 ~30% — `/convert` endpoint exists; no step-synchronised revealing

**Purpose:** Converts math expressions into properly typeset notation in real time
as the tutor explains. Handles mid-explanation rendering so each algebraic step
appears line by line as the Teaching Agent narrates, not all at once.

**Current files:**
- `apps/api/tutor_router.py` → `POST /convert` — Claude Haiku wraps plain text
  expressions in `$...$` delimiters; returns full converted string

**What remains:**
- Emit `whiteboard_command: {type: "write_latex", id, latex}` for each step
  sequentially instead of sending all steps at once
- Frontend: treat `write_latex` commands as an animation queue (one per
  ~500ms) rather than rendering immediately
- Handle block math (`$$...$$`) separately from inline so the Whiteboard Agent
  places them correctly on the canvas

---

### Graphing Agent
**Status:** ❌ ~5% — frontend Desmos integration only; no backend agent

**Purpose:** Plots functions, inequalities, geometric figures, and number lines.
Produces interactive and animated output — e.g., animating `f(x)` shifting to
`f(x+2)` so students see transformations dynamically.

**Target interface:**
```python
GraphSpec = {
    "type": "function" | "parametric" | "inequality" | "scatter" | "number_line",
    "expressions": list[str],    # Desmos-compatible LaTeX
    "bounds": {"x": [min, max], "y": [min, max]},
    "animate": list[{"param": str, "from": float, "to": float, "steps": int}],
    "labels": list[{"x": float, "y": float, "text": str}],
}
```

**What to build:**
- Backend: `agents/graphing_agent.py` — takes a natural-language description of
  what to graph ("graph f(x) = 2x+1 and mark the y-intercept") and returns a
  `GraphSpec` using Claude to parse intent + SymPy to verify the expression
- Frontend: Whiteboard Agent renders `GraphSpec` via the existing Desmos embed
- Animation: `animate` array drives Desmos `setExpression` calls in a loop

---

### Diagram Agent
**Status:** ❌ Not built

**Purpose:** Constructs geometric figures, fraction bars, area models, coordinate
planes, Venn diagrams, and other composed shapes. Separate from the Graphing Agent
because these are composed shapes, not plotted functions.

**Target interface:**
```python
DiagramSpec = {
    "type": "triangle" | "fraction_bar" | "area_model" | "venn" | "number_line"
            | "coordinate_plane" | "circle",
    "params": dict,   # type-specific: triangle → {legs: [3,4], labels: True}
    "annotations": list[{"shape_id": str, "label": str, "color": str}],
}
```

**What to build:**
- A shape grammar: a small set of composable SVG primitives that Claude can
  describe declaratively
- Backend: `agents/diagram_agent.py` — Claude produces a `DiagramSpec` from a
  natural-language description; no custom rendering engine needed — SVG templates
  per diagram type

---

### Color Agent
**Status:** ❌ Not built

**Purpose:** Assigns and enforces semantic color meaning consistently across the
entire session. Red = error, green = confirmed correct, blue = the variable being
solved for, yellow = highlight this step. Colors must remain consistent across all
turns.

**Target interface:**
```python
@dataclass
class ColorPalette:
    error: str = "#E53E3E"
    correct: str = "#38A169"
    focus_variable: str = "#3182CE"
    highlight: str = "#D69E2E"
    neutral: str = "#718096"

class ColorAgent:
    def assign(self, element_id: str, semantic: Literal["error","correct",
               "focus_variable","highlight","neutral"]) -> WhiteboardCommand
    def get_color(self, element_id: str) -> str  # returns consistent color
```

**What to build:**
- Session-scoped color registry: once an element `id` is assigned a semantic role,
  all subsequent references use the same color
- Injected into Whiteboard Agent: all `write_latex` and `highlight` commands pass
  through Color Agent before reaching the frontend

---

### Annotation Agent
**Status:** ❌ Not built

**Purpose:** Draws arrows, circles key terms, underlines, and adds margin notes.
Mimics what a human tutor does with a marker — circling the sign that keeps
flipping, bracketing the expression being factored.

**Target interface:**
```python
AnnotationSpec = {
    "type": "circle" | "arrow" | "underline" | "bracket" | "margin_note",
    "target_id": str,       # ID of the whiteboard element being annotated
    "label": str | None,
    "color": str,
}
```

**What to build:**
- Backend: `agents/annotation_agent.py` — Teaching Agent and Socratic Agent can
  call `annotate(element_id, annotation_type, label)` which the Annotation Agent
  converts to `WhiteboardCommand` objects
- Common patterns to pre-encode: "circle the term that changes sign", "bracket the
  expression being factored", "arrow from step N to step N+1 labelled 'simplify'"

---

### Step Reveal Agent
**Status:** ❌ Not built

**Purpose:** Controls the timing of what appears on screen. Never dumps a full
solution — reveals one line at a time, synchronised with the Teaching Agent's
narration. Pacing of reveal is a core comprehension mechanism.

**Target interface:**
```python
async def reveal_steps(
    worked_steps: list[WorkedStep],
    tutor_narration: str,
    delay_ms: int = 600,
) → AsyncIterator[WhiteboardCommand]
```

**What to build:**
- Segment `worked_steps` into individual `write_latex` commands
- Emit them as a timed stream over the WebSocket (`delay_ms` between each)
- The frontend buffers and displays sequentially; never all at once
- Pause signal: if the student sends a message mid-reveal, pause the queue
  and handle the message first

---

### Handwriting Simulation Agent
**Status:** ❌ Not built

**Purpose:** Renders math appearing as if hand-drawn, at human writing speed,
rather than snapping text onto the board. Research shows students learn better when
they feel they're watching someone think through a problem.

**Implementation note:** This is entirely a frontend concern. The backend emits
`write_latex` commands; the frontend renders them using a progressive SVG stroke
animation library (e.g., `vivus.js` or a custom Canvas path animation) rather than
instant KaTeX snap.

**What to build (frontend only):**
- When a `write_latex` whiteboard command is received, render it character-by-
  character via a stroke animation at ~40 chars/second
- Use a handwriting-style font (e.g., `Caveat` from Google Fonts) in the whiteboard
  panel only (not in problem statements or student input)
- No backend changes required

---

### Highlighting / Replay Agent
**Status:** ❌ Not built

**Purpose:** Can replay any portion of the session on demand. "Show me that step
again" rewinds and re-animates the exact whiteboard sequence. Also highlights the
specific line in a student's submitted work where an error occurred.

**Target interface:**
```python
class ReplayAgent:
    def record(self, command: WhiteboardCommand, timestamp: float) → None
    def replay_from(self, timestamp: float) → list[WhiteboardCommand]
    def highlight_error(self, step_number: int, element_id: str) → list[WhiteboardCommand]
```

**What to build:**
- `WhiteboardState` (from Whiteboard Agent) already stores element state; add
  a `command_log: list[(timestamp, WhiteboardCommand)]` to `TutorSession`
- Replay endpoint: `GET /tutor/session/{id}/replay?from_ts=<float>` returns the
  command log slice; frontend re-executes
- Error highlight: Solution Evaluation Agent returns `error_step_id`; Replay Agent
  emits `{type: "highlight", id: error_step_id, color: Color.error}`

---

## Reporting & Communication

### Parent / Progress Reporter Agent
**Status:** 🔶 ~20% — session_summarizer output is student-facing; parent report not built

**Purpose:** Generates human-readable session summaries for parents or teachers.
Translates internal model state (e.g., `mastery: 0.43, trending_up`) into plain
language. Configurable for frequency (per-session, weekly, monthly).

**Current files:**
- `apps/api/agents/session_summarizer.py` — produces `bullets`, `per_topic_performance`,
  `practice_problems`; currently surfaced to the student, not parents

**Target interface:**
```python
async def generate_parent_report(
    student_name: str,
    sessions: list[SessionSummary],   # last N sessions
    mastery_snapshot: dict[str, float],
    frequency: Literal["session","weekly","monthly"],
) → str   # plain English, no jargon, no internal labels
```

**What to build:**
- Backend: `agents/parent_reporter.py` — takes the session summary dict and
  mastery snapshot; renders a 3-paragraph plain-English report: what was covered,
  how the student is progressing, what to reinforce at home
- Tone rules: no technical labels ("mastery score", "EDGE phase"), no alarm language
  for low mastery — frame everything as "areas to keep practising"
- Delivery: email via the existing notification infrastructure (or a
  `/teacher/student/{id}/report` endpoint for teachers)

---

## Data Layer

### Student Model
**Status:** 🔶 ~40% — Progress table exists; mastery updates not wired post-session

**What exists:**
- `apps/api/db_models.py` → `Progress` table: per-user + per-topic mastery score,
  last reviewed timestamp, SRS schedule
- `apps/api/ws_session.py` → `TutorSession`: per-session tracking of attempts,
  hints, solved count, `consecutive_no_progress`, `session_summary`

**What remains:**
- After `session_summarizer` returns `per_topic_performance` → write mastery delta
  to `Progress` table (Session Memory Agent's responsibility)
- Persist `error_patterns` field: list of misconception labels tagged by the
  Diagnostic Agent during the session
- Add `inferred_learning_style` field: seeded by whether the student responded
  better to algebraic, verbal, or visual representations (tracked by Teaching Agent)

---

### Curriculum Knowledge Graph
**Status:** ✅ ~75% — all courses have concept DAGs; analytics wired

**What exists:**
- `apps/api/alg1_concepts.py`, `alg2_concepts.py`, `calc1_concepts.py`,
  `calc2_concepts.py`, `calc3_concepts.py`, `diffeq_concepts.py`,
  `geometry_concepts.py`, `linalg_concepts.py`, `precalc_concepts.py`,
  `prealg_concepts.py`, `probstat_concepts.py`, `proofs_contest_concepts.py`,
  `ap_calculus_concepts.py`, `sat_math_concepts.py`
- `apps/api/concept_taxonomy.py` → `labels_for_topic()` — misconception labels
  per topic; used by Socratic Agent
- `apps/api/concepts.py`, `concept_analytics.py`

**What remains:**
- Validate that every `topic_id` in `taxonomy.py` has a corresponding node in the
  relevant `*_concepts.py` graph — there are likely gaps for newer topics
- Expose a `get_prerequisites(topic_id) → list[topic_id]` function that the
  Curriculum Planner Agent can call directly

---

## Agent Interaction Map

```
Student Input
    └─► Input Router Agent
            ├─► OCR/Parsing Agent (file upload or stylus PNG)
            └─► [structured math] ──► Solution Evaluation Agent
                                              │
                                              ▼
                                      Diagnostic Agent ──► Student Model
                                              │
                                              ▼
                                    Session Orchestrator
                                    ┌───────┼───────────┐
                                    ▼       ▼           ▼
                        Curriculum  Teaching  Socratic
                        Planner     Agent     Questioning
                        Agent               Agent
                                    │
                                    ▼
                            Whiteboard Agent (scene manager)
                            ┌──────┼──────┬──────┬──────┐
                            ▼      ▼      ▼      ▼      ▼
                          LaTeX  Graph  Color  Annot. Step
                          Agent  Agent  Agent  Agent  Reveal
                                                      Agent

Running in parallel always:
    Affect Monitor Agent ──► signals Orchestrator on frustration/disengagement
    Session Memory Agent ──► reads/writes Student Model after each exchange
```

---

## Build Priority Order

| Priority | Agent | Why |
|---|---|---|
| 1 | **Session Orchestrator** — extract from `ws_router.py` | Nothing else can be cleanly added until transport and logic are separated |
| 2 | **Diagnostic Agent** — implement `adaptive_engine.recommend()` | Core differentiator; enables all personalization downstream |
| 3 | **Solution Evaluation** — step-level error localisation | Determines whether the system actually understands student errors vs just checking final answers |
| 4 | **Teaching Agent** — multi-representation switching | Instructional loop is incomplete without representation fallbacks |
| 5 | **Session Memory** — wire mastery updates post-session | Makes the system longitudinal; currently every session starts cold |
| 6 | **Metacognitive Reflection Agent** | High ROI for retention; lightweight to build |
| 7 | **Affect Monitor** | Emotional intelligence layer; heuristics only, no LLM needed |
| 8 | **OCR** — live stylus path | Enable handwritten input beyond file uploads |
| 9 | **Whiteboard + LaTeX + Step Reveal** | Minimum viable visual layer for the GSAP canvas |
| 10 | **Graphing + Diagram + Color + Annotation** | Enrich the visual layer |
| 11 | **Curriculum Planner** — prerequisite gating | Personalized session planning |
| 12 | **Problem Generation** — misconception targeting | Target specific gaps |
| 13 | **Parent Reporter** | Longitudinal reporting |
| 14 | **Replay Agent** | Polish; not on critical path |
| 15 | **Handwriting Simulation** | Frontend-only; purely aesthetic |
