# Manim Video Pipeline — Implementation Plan

**Spec:** `docs/superpowers/specs/2026-05-20-manim-video-pipeline-design.md`
**Date:** 2026-05-20
**First target:** Pre-Calculus and Trigonometry (72 lessons)

---

## Prerequisites

Before writing any pipeline code:

- [ ] Install Manim CE: `pip install manim`
- [ ] Install ffmpeg (via `winget install ffmpeg` or Chocolatey)
- [ ] Install Python deps: `pip install openai filelock pillow anthropic`
- [ ] Verify Manim renders a hello-world scene successfully
- [ ] Confirm OpenAI API key has TTS access (`tts-1-hd` model)
- [ ] Pin Manim version in `pipeline/requirements.txt`

---

## Phase 1 — Project scaffold

**Goal:** Empty pipeline directory with the right structure before writing any logic.

### Step 1.1 — Create directory layout

```
pipeline/
  __init__.py
  requirements.txt
  run.py                  # CLI entry point
  status.py               # Progress dashboard
  state.py                # state.json read/write with filelock
  config.py               # paths, API keys, worker count
  stages/
    __init__.py
    s1_plan.py            # Stage 1: video plan generation
    s2_generate.py        # Stage 2: Manim code generation
    s3_correct.py         # Stage 3: screenshot self-correction loop
    s4_render.py          # Stage 4: full 1080p render
    s5_audio.py           # Stage 5: TTS + ffmpeg audio sync
    s6_assemble.py        # Stage 6: clip assembly + manifest write
  prompts/
    layout_bible.txt      # injected into every Stage 2 call
    plan_prompt.txt       # Stage 1 system prompt
    generate_prompt.txt   # Stage 2 system prompt
    correct_prompt.txt    # Stage 3 review prompt
    math_to_speech.txt    # LaTeX → spoken English rules
  templates/
    hook.py               # Manim skeleton for hook clip
    concept.py            # Manim skeleton for concept clip
    worked_example.py     # Manim skeleton for worked_example clip
    common_mistakes.py    # Manim skeleton for common_mistakes clip
    summary.py            # Manim skeleton for summary clip
  viz/
    __init__.py
    # one file per visualization type (added in Phase 3)
  outputs/                # rendered .mp4 files (gitignored)
  needs_review/           # failed lessons (gitignored)
  state.json              # pipeline state (gitignored)
```

### Step 1.2 — Write `config.py`

Constants only — no logic:
- `PIPELINE_ROOT`, `OUTPUTS_DIR`, `NEEDS_REVIEW_DIR`
- `STATE_FILE`, `LOCK_FILE`
- `MANIM_QUALITY` (`-ql` for preview, `-qh` for full render)
- `MAX_CORRECTION_ROUNDS = 3`
- `DEFAULT_WORKERS = 3`
- `OPENAI_TTS_MODEL = "tts-1-hd"`, `OPENAI_TTS_VOICE = "onyx"`
- `ANTHROPIC_MODEL` (read from env, default `claude-sonnet-4-6`)

### Step 1.3 — Write `state.py`

Two public functions — nothing else:
- `read_state(lesson_id) -> dict` — reads state.json under filelock, returns lesson entry or `{}`
- `write_state(lesson_id, updates: dict)` — reads, merges updates, writes under filelock

Test: write a lesson entry, read it back, verify round-trip.

---

## Phase 2 — Layout bible and prompt files

**Goal:** All prompt content written and reviewed before any Claude calls are made.

### Step 2.1 — Write `prompts/layout_bible.txt`

Exact content from spec Section "Part A — Layout Bible":
- Frame and safe zone coordinates
- Required patterns (VGroup, scale_to_fit_width, wait("BEAT_N"), to_edge)
- Forbidden patterns (hardcoded move_to, font > 36, raw positioning math)

### Step 2.2 — Write `prompts/math_to_speech.txt`

Full LaTeX → spoken English conversion table from spec.
Add at minimum: fractions, exponents, roots, integrals, limits, derivatives,
vectors, matrices, set notation, Greek letters (θ, π, α, β, Σ, Δ).

### Step 2.3 — Write `prompts/plan_prompt.txt`

System prompt for Stage 1. Must instruct Claude to:
- Output valid JSON matching the video plan schema (no markdown fences)
- Apply math_to_speech rules to all narration text
- Pick visualization type from the approved library only
- Use the Pre-Calculus topic-to-visualization mapping table
- Include `viz_params: {}` even when no parameters are needed

### Step 2.4 — Write `prompts/generate_prompt.txt`

System prompt for Stage 2. Must instruct Claude to:
- Output a complete, runnable Python file (no markdown fences, no explanation)
- Use only the approved Manim primitives listed in the layout bible
- Use `self.wait("BEAT_N")` placeholders — never hardcoded floats
- Animate the provided content exactly — never derive or simplify math

### Step 2.5 — Write `prompts/correct_prompt.txt`

System prompt for Stage 3 review. Must instruct Claude to:
- Output either `APPROVED` (one word) or a JSON patch array
- Patch format: `[{"line": N, "old": "...", "new": "..."}]`
- Check specifically: boundary violations, overlaps, unreadable text, blank frames

### Step 2.6 — Write Manim skeleton templates (`templates/*.py`)

One file per clip type. Each file contains a single `Scene` subclass with:
- Correct class name (`HookScene`, `ConceptScene`, `WorkedExampleScene`, etc.)
- `FILL_IN` placeholders where content goes
- `self.wait("BEAT_N")` at every animation beat
- All positioning using the required patterns (VGroup, to_edge, scale_to_fit_width)

---

## Phase 3 — Visualization library

**Goal:** Pre-built, tested Manim components for each visualization type.
These are the building blocks Claude assembles — not generated from scratch.

### Step 3.1 — Core geometry helpers (`viz/helpers.py`)

Utility functions used by multiple visualization types:
- `make_right_triangle(theta, hyp_color, opp_color, adj_color)` — returns VGroup
- `make_unit_circle(radius=2.5)` — Circle + axes + tick marks
- `make_axes(x_range, y_range, labels=True)` — returns Axes with standard styling
- `color_equation_parts(mathtex, part_colors: dict)` — color-codes named substrings

Test each function renders without errors at low quality.

### Step 3.2 — Implement visualization types (one per file)

Implement in this priority order (most lessons use these first):

1. **`viz/equation_transform.py`** — `TransformMatchingTex` step sequence
2. **`viz/equation_anatomy.py`** — `MathTex` + `Brace` + `Text` label layout
3. **`viz/coordinate_plane.py`** — `Axes` + `Plot` + optional `Dot` markers
4. **`viz/unit_circle.py`** — full unit circle with tracing dot + sin/cos projections
5. **`viz/trig_graph_sync.py`** — unit circle left + wave right, synchronized
6. **`viz/angle_sweep.py`** — `Arc` + `ValueTracker` + degree/radian labels
7. **`viz/parameter_sweep.py`** — `ValueTracker` + `always_redraw` for any shape
8. **`viz/sohcahtoa.py`** — right triangle with color-coded sides + ratio reveals
9. **`viz/geometric_construction.py`** — `DashedLine`, `Dot`, `Brace`, `DoubleArrow`
10. **`viz/conic_rotation.py`** — `Rotate` / `ApplyMatrix` on parametric conic
11. **`viz/linear_transform_plane.py`** — `NumberPlane` + `ApplyMatrix`
12. **`viz/number_line.py`** — `NumberLine` + `Arrow` + interval shading
13. **`viz/geometric_figure.py`** — `Polygon`, `Circle`, `Arc`, `Angle`
14. **`viz/vector_diagram.py`** — `Arrow` + component breakdown
15. **`viz/matrix_transform.py`** — `Matrix` + row/column highlighting
16. **`viz/step_reveal.py`** — sequential `FadeIn` of `MathTex` items
17. **`viz/mistake_comparison.py`** — side-by-side VGroup with ✗/✓ markers
18. **`viz/bar_chart.py`** — `BarChart` with animated bar growth
19. **`viz/probability_tree.py`** — `VGroup` of arrows + branch labels
20. **`viz/venn_diagram.py`** — overlapping `Circle`s + region labels

Each file exports one function: `build_scene(params: dict) -> Scene`.
Each file has a `if __name__ == "__main__"` block that renders a test example.

**3D visualizations** (`viz/threed_*.py`) — implement last, after all 2D types are working:
- `viz/threed_axes.py`, `viz/threed_vectors.py`, `viz/threed_surface.py`

---

## Phase 4 — Pipeline stages

Implement stages in dependency order. Each stage is independently testable.

### Step 4.1 — Stage 1: Video plan (`stages/s1_plan.py`)

**Input:** `lesson_id: str`
**Output:** `dict` matching video plan schema, written to `outputs/{lesson_id}/plan.json`

1. Load lesson JSON from `apps/api/data/topic_lessons/{lesson_id}.json`
   - If not found, call the existing `topic_lesson_writer.py` to generate it first
2. Load Pre-Calculus topic-to-visualization mapping from spec
3. Build Claude prompt: system=`plan_prompt.txt` + math_to_speech rules, user=lesson JSON + mapping
4. Call Claude API, parse JSON response, validate against schema
5. Write to `outputs/{lesson_id}/plan.json`
6. Return the plan dict

**Error handling:** If Claude returns invalid JSON, retry once with "your response was not valid JSON, try again." If second attempt fails, raise `PlanGenerationError`.

**Test:** Run on `pc_024` (SOHCAHTOA). Inspect `plan.json` — verify narration has no LaTeX, visualization types are from the approved library, `viz_params` present on every clip.

### Step 4.2 — Stage 2: Manim code generation (`stages/s2_generate.py`)

**Input:** `lesson_id: str`, `clip_type: str`, `plan: dict`
**Output:** Python file written to `outputs/{lesson_id}/{clip_type}.py`

1. Load `layout_bible.txt`
2. Extract the clip's entry from the plan (narration beats, viz type, viz_params)
3. Load the template skeleton for this clip type from `templates/{clip_type}.py`
4. Build Claude prompt: system=layout_bible + generate_prompt, user=clip plan entry + template
5. Call Claude API, extract Python code (strip any accidental markdown fences)
6. Write raw Python to `outputs/{lesson_id}/{clip_type}.py`
7. Run quick syntax check: `python -c "import ast; ast.parse(open(path).read())"` — if fails, retry once

**Test:** Generate `pc_024` worked_example clip. Open the `.py` file and verify it imports Manim correctly and has `self.wait("BEAT_")` placeholders.

### Step 4.3 — Stage 3: Self-correction loop (`stages/s3_correct.py`)

**Input:** `lesson_id: str`, `clip_type: str`
**Output:** Approved `.py` file in `outputs/{lesson_id}/` or entry written to `needs_review/`

```
for round in range(1, MAX_CORRECTION_ROUNDS + 1):
    1. Run: manim -ql outputs/{lesson_id}/{clip_type}.py ClassName
       Capture stdout/stderr. If non-zero exit, treat as layout failure.
    2. Extract 5 frames using ffmpeg (at 0%, 25%, 50%, 75%, 100% of duration)
    3. Automated pixel check (PIL):
       - Scan for non-background pixels within 5% of frame edge
       - Check for >90% black frame (crash indicator)
       - If clean: send lighter review prompt to Claude
       - If flagged: include flagged coordinates in review prompt
    4. Send frames + code + correct_prompt to Claude (vision call)
    5. If response == "APPROVED": break
    6. If response is JSON patch array: apply patches to .py file
       - If a patch line doesn't match: request full rewrite instead
    7. If round == MAX_CORRECTION_ROUNDS: write to needs_review/, break
```

**Failure manifest:** Write `needs_review/{lesson_id}_{clip_type}/`:
- `last_code.py` — final state of the script
- `frames.png` — PIL contact sheet of last 5 frames
- `review_comment.txt` — Claude's last review text
- `patch_history.json` — all patches applied

**Test:** Intentionally inject a layout violation (`.move_to([8, 0, 0])`) into a generated script and verify the loop catches and corrects it within 3 rounds.

### Step 4.4 — Stage 5: Audio generation and sync (`stages/s5_audio.py`)

**Input:** `lesson_id: str`, `clip_type: str`, `plan: dict`, approved `.py` file path
**Output:** `outputs/{lesson_id}/{clip_type}_with_audio.mp4`

1. Extract narration beats from plan for this clip type
2. For each beat, call OpenAI TTS:
   ```python
   client.audio.speech.create(model="tts-1-hd", voice="onyx", input=beat["text"])
   ```
   Save to `outputs/{lesson_id}/{clip_type}_beat_{N}.mp3`
3. Get duration of each `.mp3` using ffprobe:
   `ffprobe -v quiet -show_entries format=duration -of csv=p=0 beat_N.mp3`
4. Replace `self.wait("BEAT_N")` with `self.wait({duration})` in the approved `.py` file
5. Run full render: `manim -qh outputs/{lesson_id}/{clip_type}.py ClassName`
   Output: `outputs/{lesson_id}/{clip_type}.mp4`
6. Concatenate beat audio files: `ffmpeg -f concat beat_list.txt -c copy narration.mp3`
7. Merge audio + video:
   ```
   ffmpeg -i clip.mp4 -i narration.mp3 -c:v copy -c:a aac -shortest clip_with_audio.mp4
   ```
8. Verify output duration is within 0.5 sec of narration duration; if over, apply `atempo`

**Test:** Run on `pc_024` hook clip. Listen to the output — verify narration is audible, synced, and contains no LaTeX strings spoken aloud.

### Step 4.5 — Stage 6: Assembly and manifest (`stages/s6_assemble.py`)

**Input:** `lesson_id: str`, all `*_with_audio.mp4` clip files
**Output:** `outputs/{lesson_id}/full.mp4`, `outputs/{lesson_id}/manifest.json`

1. Write `clip_list.txt` listing clips in order: hook → concept → worked_example → common_mistakes → summary
2. Run: `ffmpeg -f concat -safe 0 -i clip_list.txt -c copy full.mp4`
3. Get duration of each clip via ffprobe
4. Write `manifest.json` matching schema from spec
5. Update `state.json` entry to `"status": "done"`

**Test:** Verify `full.mp4` plays end-to-end, total duration equals sum of clip durations.

---

## Phase 5 — Orchestrator

### Step 5.1 — Write `run.py`

CLI with argparse:
```
python pipeline/run.py [--lesson LESSON_ID] [--course COURSE_ID]
                       [--only needs_review] [--workers N]
```

Logic:
1. Build lesson queue from taxonomy (all lessons, or filtered by course/lesson/status)
2. Skip lessons where `state.json` shows `status == "done"`
3. For `status == "rendering"`: resume from last completed clip
4. Spin up `--workers` threads using `concurrent.futures.ThreadPoolExecutor`
5. Each worker calls `process_lesson(lesson_id)` which runs Stages 1–6 in sequence
6. On any unhandled exception: log, mark lesson as `needs_review`, continue

`process_lesson(lesson_id)` sequence:
```python
plan = s1_plan.run(lesson_id)
for clip_type in ["hook", "concept", "worked_example", "common_mistakes", "summary"]:
    if clip_type in state.read_state(lesson_id).get("clips_done", []):
        continue  # resume support
    s2_generate.run(lesson_id, clip_type, plan)
    s3_correct.run(lesson_id, clip_type)
    s5_audio.run(lesson_id, clip_type, plan)
    state.write_state(lesson_id, {"clips_done": [...existing..., clip_type]})
s6_assemble.run(lesson_id)
```

### Step 5.2 — Write `status.py`

Reads `state.json`, prints dashboard:
```
Gradient Video Pipeline — Pre-Calculus
────────────────────────────────────────
Done            0 / 72   ░░░░░░░░░░░░   0%
Rendering       0
Needs review    0
Pending        72

Run: python pipeline/run.py --course precalculus
```

---

## Phase 6 — Manual test run (3–5 lessons)

**Before running the full batch, validate the pipeline end-to-end on a hand-picked sample.**

### Step 6.1 — Choose test lessons

Pick 5 lessons that exercise different visualization types:
- `pc_024` — SOHCAHTOA (sohcahtoa viz)
- `pc_025` — Graphs of sine/cosine (trig_graph_sync)
- `pc_002` — Parent functions (parameter_sweep)
- `pc_056` — Ellipses (geometric_construction + parameter_sweep)
- `pc_072` — Introduction to integration (coordinate_plane)

### Step 6.2 — Run each lesson individually

```bash
python pipeline/run.py --lesson pc_024
python pipeline/run.py --lesson pc_025
# ... etc.
```

For each lesson:
- Watch the full output video
- Check audio sync (no drift, no raw LaTeX spoken aloud)
- Check layout (nothing clipped or overlapping)
- Check mathematical accuracy (equations match lesson JSON)

### Step 6.3 — Fix any systematic issues

Common issues to watch for:
- Claude using a forbidden Manim method → add to layout bible forbidden list
- Narration too fast/slow → adjust TTS voice speed via `speed` parameter
- Visualization type wrong for topic → update Stage 1 mapping prompt
- Beat count mismatch (more waits than beats or vice versa) → add beat validation to Stage 2

Re-run affected lessons after fixes:
```bash
python pipeline/run.py --only needs_review
```

---

## Phase 7 — Full Pre-Calculus batch

### Step 7.1 — Run overnight

```bash
python pipeline/run.py --course precalculus --workers 3
```

Monitor with:
```bash
python pipeline/status.py
```

### Step 7.2 — Review needs_review lessons

After batch completes, open each `needs_review/` contact sheet.
Group failures by pattern (same clip type? same visualization type? same unit?).
Fix the root cause in the prompt or template, then re-run:

```bash
python pipeline/run.py --only needs_review
```

### Step 7.3 — Spot-check final output

Watch one video per unit (11 videos). Focus on:
- Mathematical correctness of worked examples
- Visualization quality for the 3D topics (pc_062–066) — these are most likely to need manual fixes
- Limit/derivative/integration videos (pc_067–072) — verify the ValueTracker animations render smoothly

---

## Phase 8 — Website integration (separate sub-project)

Out of scope for this plan. Begins after Pre-Calculus batch is reviewed and approved.

Involves:
- Cloudflare R2 bucket setup and upload tooling
- `GET /topics/{topic_id}/video` API endpoint
- Lesson page video player component with chapter selector
- Tutor WebSocket `video` message type + inline chat player

---

## File checklist

```
pipeline/
  config.py                     Phase 1
  state.py                      Phase 1
  run.py                        Phase 5
  status.py                     Phase 5
  requirements.txt              Phase 1
  prompts/
    layout_bible.txt            Phase 2
    math_to_speech.txt          Phase 2
    plan_prompt.txt             Phase 2
    generate_prompt.txt         Phase 2
    correct_prompt.txt          Phase 2
  templates/
    hook.py                     Phase 2
    concept.py                  Phase 2
    worked_example.py           Phase 2
    common_mistakes.py          Phase 2
    summary.py                  Phase 2
  stages/
    s1_plan.py                  Phase 4
    s2_generate.py              Phase 4
    s3_correct.py               Phase 4
    s5_audio.py                 Phase 4
    s6_assemble.py              Phase 4
  viz/
    helpers.py                  Phase 3
    equation_transform.py       Phase 3
    equation_anatomy.py         Phase 3
    coordinate_plane.py         Phase 3
    unit_circle.py              Phase 3
    trig_graph_sync.py          Phase 3
    angle_sweep.py              Phase 3
    parameter_sweep.py          Phase 3
    sohcahtoa.py                Phase 3
    geometric_construction.py   Phase 3
    conic_rotation.py           Phase 3
    linear_transform_plane.py   Phase 3
    number_line.py              Phase 3
    geometric_figure.py         Phase 3
    vector_diagram.py           Phase 3
    matrix_transform.py         Phase 3
    step_reveal.py              Phase 3
    mistake_comparison.py       Phase 3
    bar_chart.py                Phase 3
    probability_tree.py         Phase 3
    venn_diagram.py             Phase 3
    threed_axes.py              Phase 3 (last)
    threed_vectors.py           Phase 3 (last)
    threed_surface.py           Phase 3 (last)
```

---

## Dependency order summary

```
Phase 1 (scaffold + state)
    ↓
Phase 2 (prompts + templates)
    ↓
Phase 3 (viz library — 2D first, 3D last)
    ↓
Phase 4 (pipeline stages — s1 → s2 → s3 → s5 → s6)
    ↓
Phase 5 (orchestrator: run.py + status.py)
    ↓
Phase 6 (manual test: 5 lessons)
    ↓
Phase 7 (full Pre-Calculus batch: 72 lessons)
    ↓
Phase 8 (website integration — separate sub-project)
```
