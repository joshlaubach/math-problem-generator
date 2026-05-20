# Manim Video Pipeline — Design Spec

**Date:** 2026-05-20
**Status:** Approved
**Scope:** Sub-project 1 of 4 — Script Generation + Render Pipeline (local batch)

---

## Overview

Generate 865 Manim videos (one per lesson) using AI-generated code fed by the existing
lesson JSON schema. Videos are split into per-section clips that are assembled into a
full lesson video. Each clip is narrated by AI voiceover synced to the animation.
The finished videos are embedded in lesson pages and served to the AI tutor on demand.

**Constraints:**
- No Manim mobjects may overlap accidentally
- No mobjects may extend outside the safe content area
- All 865 lessons must be processable in a resumable local batch job
- Videos must be usable both as standalone lesson content and as AI tutor references

---

## Architecture — 6-Stage Pipeline

Each lesson goes through six stages in sequence:

```
Lesson JSON (hook, concept, anatomy, worked_example, etc.)
         │
         ▼
┌─────────────────────┐
│ Stage 1: Plan       │  Claude reads lesson JSON → outputs a structured video plan:
│                     │  which sections to animate, visualization type per section,
│                     │  narration text with beat markers, timing estimates
└────────┬────────────┘
         ▼
┌─────────────────────┐
│ Stage 2: Generate   │  Claude writes full Manim Python for each section clip,
│                     │  prompted with layout bible (safe zones, required patterns,
│                     │  forbidden patterns) + section template skeleton
└────────┬────────────┘
         ▼
┌─────────────────────┐
│ Stage 3: Correct    │  Render preview frames (low quality, ~5 sec/clip) →
│ (max 3 rounds)      │  automated pixel check → Claude visual review →
│                     │  JSON patch applied → re-render → repeat up to 3×
└────────┬────────────┘
         ▼
┌─────────────────────┐
│ Stage 4: Render     │  Full 1080p render of approved Manim scripts.
│                     │  One .mp4 per section clip.
└────────┬────────────┘
         ▼
┌─────────────────────┐
│ Stage 5: Audio      │  Beat-marker narration → OpenAI TTS (.mp3 per beat) →
│                     │  durations injected into Manim wait() calls →
│                     │  ffmpeg merges audio + video per clip
└────────┬────────────┘
         ▼
┌─────────────────────┐
│ Stage 6: Assemble   │  ffmpeg concatenates section clips → full lesson .mp4.
│                     │  Upload all files to Cloudflare R2.
│                     │  Write video manifest JSON (lesson_id → clip URLs).
└─────────────────────┘
```

Videos that fail 3 correction rounds are written to `needs_review/` with a contact
sheet of the last 5 frames and Claude's last review comment. The batch continues
unblocked; failed lessons are re-run manually after fixing the underlying issue.

---

## Stage 1: Video Plan

Claude reads the full lesson JSON and outputs a structured video plan. The plan
determines what to animate and how before any Manim code is written.

### Video plan schema

```json
{
  "lesson_id": "a1_023",
  "topic": "Graphing Linear Equations",
  "clips": [
    {
      "type": "hook",
      "narration_beats": [
        { "beat": 1, "text": "What does it mean for a point to be on a line?" }
      ],
      "visualization": "coordinate_plane",
      "viz_params": { "x_range": [-5, 5], "y_range": [-4, 4] }
    },
    {
      "type": "concept",
      "narration_beats": [...],
      "visualization": "equation_anatomy",
      "viz_params": { "equation": "y = mx + b", "label_parts": ["slope", "y-intercept"] }
      // viz_params is always present; use {} when the visualization type needs no parameters
    },
    {
      "type": "worked_example",
      "narration_beats": [...],
      "visualization": "coordinate_plane_with_steps",
      "viz_params": { "plot_fn": "2*x - 1", "highlight_points": [[0, -1], [1, 1]] }
    },
    {
      "type": "common_mistakes",
      "narration_beats": [...],
      "visualization": "mistake_comparison",
      "viz_params": {}
    },
    {
      "type": "summary",
      "narration_beats": [...],
      "visualization": "equation_anatomy"
    }
  ]
}
```

### Narration rules

Narration text must be plain English — no LaTeX. Stage 1 applies a math-to-speech
conversion rule set before writing narration:

| LaTeX | Spoken form |
|---|---|
| `x^2` | "x squared" |
| `\frac{a}{b}` | "a over b" |
| `\sqrt{x}` | "the square root of x" |
| `\int_a^b` | "the integral from a to b" |
| `f'(x)` | "f prime of x" |
| `\lim_{x \to 0}` | "the limit as x approaches zero" |
| `\vec{v}` | "the vector v" |
| `A^{-1}` | "A inverse" |

### Visualization selection guide

Claude picks visualization type based on topic and section:

| Visualization type | Manim primitives | When to use |
|---|---|---|
| `equation_transform` | `MathTex` + `TransformMatchingTex` | Algebraic manipulation, solving steps |
| `equation_anatomy` | `MathTex` + `Brace` + `Text` labels | Defining parts of a formula |
| `coordinate_plane` | `Axes` + `Plot` + `Dot` | Graphing functions, plotting points |
| `number_line` | `NumberLine` + `Arrow` | Inequalities, intervals, absolute value |
| `geometric_figure` | `Polygon`, `Circle`, `Arc`, `Angle` | Geometry proofs, angle relationships |
| `vector_diagram` | `Arrow` + `Axes` | Vector addition, linear algebra |
| `matrix_transform` | `Matrix` + `ApplyMatrix` | Matrix operations, transformations |
| `bar_chart` | `BarChart` | Statistics, histograms, frequency |
| `probability_tree` | `VGroup` of arrows + `Text` | Conditional probability, combinatorics |
| `venn_diagram` | `Circle` overlaps + `Text` | Set theory, logic |
| `balance_scale` | Custom `VGroup` | Equation balance, properties of equality |
| `step_reveal` | `MathTex` + `FadeIn` sequence | Any multi-step worked example |
| `mistake_comparison` | Side-by-side `VGroup` + ✗/✓ markers | Common mistakes clip |
| `parameter_sweep` | `ValueTracker` + `always_redraw` | Continuously morph a shape as one parameter changes — e.g. eccentricity sweeping circle → ellipse → parabola → hyperbola; shows what each variable *does* |
| `geometric_construction` | `DashedLine`, `Dot`, `Brace`, `DoubleArrow` | Focus, directrix, distance annotations on conics; compass-and-straightedge style constructions |
| `conic_rotation` | `Rotate`, `ApplyMatrix`, `Axes`, `ParametricFunction` | Physically rotate a conic; show the rotation matrix alongside the transformed curve |
| `linear_transform_plane` | `NumberPlane` + `ApplyMatrix` | Apply a 2×2 matrix to the entire coordinate plane — grid lines deform — used for conic rotation in a linear algebra context |
| `unit_circle` | `Circle`, `Dot`, `Arc`, `DashedLine`, `DecimalNumber` | Trace a point around the unit circle; project to x/y axes to show sin/cos values updating live; label angle in degrees and radians simultaneously |
| `trig_graph_sync` | `Axes` + `Plot` + `Dot` + `always_redraw` | Unit circle on the left, sin or cos curve drawing on the right in sync as the angle sweeps — shows where the wave shape comes from |
| `angle_sweep` | `Arc`, `ValueTracker`, `MathTex` | Animate an angle opening from 0 to its terminal position; show reference angles, coterminal angles, quadrant labels |

### Topic-to-visualization mapping (Pre-Calculus)

Visualization type is determined by **topic**, not just section type. The Stage 1
prompt includes this mapping for the Pre-Calculus course so Claude picks consistently:

| Topic area | Primary visualization(s) |
|---|---|
| Conics — intro (ellipse, parabola, hyperbola) | `geometric_construction` + `equation_anatomy` |
| Conics — eccentricity, focus, directrix | `parameter_sweep` + `geometric_construction` |
| Rotation of conics | `conic_rotation` + `linear_transform_plane` |
| Trig functions — definitions | `unit_circle` |
| Trig functions — graphing | `trig_graph_sync` |
| Trig identities | `equation_transform` |
| Reference angles, coterminal | `angle_sweep` |
| Vectors | `vector_diagram` |
| Matrices | `matrix_transform` + `linear_transform_plane` |
| Sequences and series | `step_reveal` + `coordinate_plane` |
| Limits | `coordinate_plane` with labeled approaching values |

### Full topic-to-visualization mapping (all 72 Pre-Calculus lessons)

#### Functions and Graphs
| Topic ID | Topic | Visualization |
|---|---|---|
| pc_001 | Function notation, domain/range | Arrow mapping diagram; vertical line test sweep |
| pc_002 | Parent functions & transformations | `parameter_sweep` — ValueTracker controls h, k, a; graph redraws live |
| pc_003 | Combining functions | Two graphs side by side; y-values stack/cancel to produce combined graph |
| pc_004 | Composition of functions | Two "function machine" boxes in series; input transforms through each |
| pc_005 | Inverse functions | f(x) + mirror reflected over y=x; point (a,b) swaps to (b,a) with arc |
| pc_006 | Modeling with functions | Real-world context graph with labeled intercepts and key values |
| pc_007 | Parametric equations | Dot traces curve as t-value increments; t shown as live counter |

#### Polynomial, Power, and Rational Functions
| Topic ID | Topic | Visualization |
|---|---|---|
| pc_008 | Polynomial end behavior | Coordinate plane zooms out; left/right arms labeled with arrow notation |
| pc_009 | Polynomial division | Long division layout built step by step; remainder theorem evaluation |
| pc_010 | Real zeros | Graph with x-intercepts highlighted; factored form reveals beside each zero |
| pc_011 | Complex zeros | Complex plane with conjugate pairs mirrored across the real axis |
| pc_012 | Rational function graphs | Asymptote lines draw first; curve fills in around them; holes as open circles |
| pc_013 | Polynomial/rational inequalities | Sign chart on number line; factor signs per interval computed visually |
| pc_014 | Power functions | Family of curves (x², x³, x⁴…) on same axes; odd vs even behavior contrasted |

#### Exponential and Logarithmic Functions
| Topic ID | Topic | Visualization |
|---|---|---|
| pc_015 | Exponential functions | `parameter_sweep` on base — sweeps from <1 to >1 showing decay/growth flip |
| pc_016 | Natural exponential | Compound interest bars converging to e^x curve as compounding frequency increases |
| pc_017 | Logarithmic functions | e^x and ln(x) drawn as reflections over y=x; point bounces between the two |
| pc_018 | Properties of logarithms | `equation_transform` — log(ab) splits with each piece color-coded |
| pc_019 | Solving exp/log equations | `equation_transform` — "take ln of both sides" or "exponentiate both sides" |
| pc_020 | Modeling with exp/log | Growth/decay curve with real data points and asymptote |
| pc_021 | Logistic functions | S-curve sweeping up; carrying capacity ceiling; inflection point marked |

#### Trigonometric Functions
| Topic ID | Topic | Visualization |
|---|---|---|
| pc_022 | Angles and their measure | `angle_sweep` — degree and radian labels update simultaneously; arc length s=rθ |
| pc_023 | The unit circle | `unit_circle` — all 16 standard positions; dot traces full circle, coordinates appear at each stop |
| pc_024 | Trig functions of any angle (SOHCAHTOA) | Right triangle with color-coded sides (hyp=gold, opp=blue, adj=green); SOHCAHTOA mnemonic reveals each ratio in turn with matching colors; `parameter_sweep` on θ shows all three ratios updating live; similar-triangles scene shows the ratio is independent of triangle size |
| pc_025 | Graphs of sine and cosine | `trig_graph_sync` — unit circle left, wave drawing right, in sync |
| pc_026 | Graphs of other trig functions | Asymptote lines draw first; tan, cot, sec, csc curves fill in around them |
| pc_027 | Inverse trig functions | sin(x) with domain restricted, then reflected to get arcsin |
| pc_028 | Harmonic motion | Spring bouncing left; its height traces sinusoidal curve on right in real time |

#### Analytic Trigonometry
| Topic ID | Topic | Visualization |
|---|---|---|
| pc_029 | Fundamental identities | Unit circle: point (x,y) = (cosθ, sinθ); x²+y²=1 is visually obvious |
| pc_030 | Verifying identities | Two columns — LHS and RHS manipulated independently; meet in the middle |
| pc_031 | Sum and difference identities | Geometric proof on unit circle: two angles, chord, derive cos(α−β) from geometry |
| pc_032 | Double/half angle identities | Derived live from sum formulas via `equation_transform` (cos 2θ = cos(θ+θ)) |
| pc_033 | Solving trig equations | Unit circle with solutions marked; number line for general solution + 2πk pattern |
| pc_034 | Product-to-sum formulas | `equation_transform` with color-coded terms grouping and splitting |

#### Additional Topics in Trigonometry
| Topic ID | Topic | Visualization |
|---|---|---|
| pc_035 | Law of Sines | Triangle with labeled sides/angles; `parameter_sweep` showing ambiguous case (two triangles) |
| pc_036 | Law of Cosines | Triangle construction with altitude; Pythagorean theorem generalized |
| pc_037 | Area of a triangle | SAS triangle with height dropping down; Heron's formula with s labeled |
| pc_038 | Vectors in the plane | `vector_diagram` with component form; tip-to-tail addition |
| pc_039 | Dot product and projections | Projection shown as shadow; angle between vectors labeled |
| pc_040 | Complex trig form | Complex plane; rectangular → polar re-labeling with r and θ animated |
| pc_041 | DeMoivre's theorem | Complex plane; nth roots evenly spaced around a circle |

#### Linear Systems and Matrices
| Topic ID | Topic | Visualization |
|---|---|---|
| pc_042 | Solving linear systems | Two lines on coordinate plane; animated solving — intersection is the solution |
| pc_043 | Row reduction | Matrix with rows highlighted as each operation applies; steps shown beside |
| pc_044 | Matrix operations | Grid layout; element-wise operations with color coding |
| pc_045 | Matrix multiplication | Row × column highlighted in sync; dot product computed piece by piece |
| pc_046 | Inverse matrices | `linear_transform_plane` — A applied to plane, then A⁻¹ undoes it back to identity |
| pc_047 | Determinants | 2×2 case: parallelogram formed by row vectors; area = |det| shown geometrically |
| pc_048 | Linear programming | Feasible region shades as each constraint adds; objective function line sweeps corner points |

#### Sequences, Series, and Probability
| Topic ID | Topic | Visualization |
|---|---|---|
| pc_049 | Arithmetic & geometric sequences | Number line dots — arithmetic spaces evenly, geometric spaces by ratio |
| pc_050 | Series and sigma notation | Running sum bar grows as terms add; partial sums of geometric series converging |
| pc_051 | Binomial theorem | Pascal's triangle builds row by row; entries light up as (a+b)^n expands |
| pc_052 | Counting principles | Tree diagram branching for permutations; combinations collapse duplicate branches |
| pc_053 | Introduction to probability | Sample space rectangle; event regions shade in; P(A∩B) shown as overlap area |
| pc_054 | Mathematical induction | Domino-falling metaphor: base case tips first, each subsequent one falls automatically |

#### Topics in Analytic Geometry
| Topic ID | Topic | Visualization |
|---|---|---|
| pc_055 | Parabolas | `geometric_construction` (focus, directrix, distance equality); `parameter_sweep` on p |
| pc_056 | Ellipses | `parameter_sweep` on a and b; eccentricity changes shape from circle to flat ellipse |
| pc_057 | Hyperbolas | Asymptotes animate first; branches fill in; `parameter_sweep` on eccentricity |
| pc_058 | Rotation of conics | `conic_rotation` + `linear_transform_plane` (rotation matrix applied to coordinate plane) |
| pc_059 | Polar coordinates | Coordinate system transformation — Cartesian grid fades, polar grid fades in |
| pc_060 | Parametric equations and curves | Dot traces curve as t increments; x(t) and y(t) graphs shown beside the curve |
| pc_061 | Conic sections in polar form | Polar grid with conic curve; `parameter_sweep` on eccentricity changes conic type |

#### Analytic Geometry in 3 Dimensions *(ThreeDScene — more complex generation)*
| Topic ID | Topic | Visualization |
|---|---|---|
| pc_062 | 3D coordinate system | Three axes rotate into perspective; point plotted with dashed projections to each plane |
| pc_063 | Vectors in 3D | 3D arrow from origin; component breakdown with three projections |
| pc_064 | Cross product | Two vectors in 3D; result shown perpendicular to both; right-hand rule animated |
| pc_065 | Lines and planes in space | Plane as flat 3D slab; line piercing it; normal vector shown |
| pc_066 | Surfaces in 3D | Parametric surface (sphere, cylinder, paraboloid) rotating slowly |

#### Limits and Introduction to Calculus *(preview of Calculus I)*
| Topic ID | Topic | Visualization |
|---|---|---|
| pc_067 | Introduction to limits | Point approaches from left and right; bracket showing closeness |
| pc_068 | Evaluating limits | Table of values converging on left; graph converging on right — both meet at the limit |
| pc_069 | Continuity | Three discontinuity types animated: removable (hole), jump, infinite |
| pc_070 | Infinite limits | Curve shoots toward vertical asymptote; y-value counter races to ±∞ |
| pc_071 | Introduction to derivative | Secant line between two points; `ValueTracker` slides one point toward the other → tangent emerges |
| pc_072 | Introduction to integration | Riemann rectangles fill area under curve; as n increases they pack tighter, sum converges |

---

## Stage 2: Manim Code Generation

Claude generates one Manim Python file per section clip. The generation prompt has
three mandatory parts.

### Part A — Layout Bible (injected every call, never changes)

```
Manim coordinate system:
  Frame:        x ∈ [-7.1, 7.1],  y ∈ [-4.0, 4.0]
  Safe content: x ∈ [-6.5, 6.5],  y ∈ [-3.5, 3.5]
  Title zone:   y ∈ [2.8,  3.5]   (top strip)
  Content zone: y ∈ [-2.5, 2.5]   (main area)
  Footer zone:  y ∈ [-3.5, -2.8]  (bottom strip)

REQUIRED patterns:
  - Always stack items with VGroup().arrange(DOWN, buff=0.4)
  - Always call .scale_to_fit_width(max_width) before placing wide equations
  - Always insert self.wait("BEAT_N") after every animation block
  - Always add .to_edge(UP) for titles, .to_edge(DOWN) for footers

FORBIDDEN:
  - Never use .move_to() with hardcoded coordinates
  - Never place two objects without grouping them first
  - Never use font size > 36 for body text
  - Never use raw Manim positioning math (UP*3 + LEFT*2 etc.)
```

### Part B — Lesson content

The relevant JSON sections for the clip type, plus the narration beats from the video
plan. Only the fields relevant to that clip type are included (no full lesson dump).

### Part C — Section template skeleton

A pre-written Manim class stub showing expected structure for that clip type.
Claude fills in the content; it does not write structural code from scratch.

Example skeleton for `worked_example`:

```python
class WorkedExample(Scene):
    def construct(self):
        title = Text("Worked Example", font_size=32).to_edge(UP)
        self.play(Write(title))
        self.wait("BEAT_1")

        # Step 1 — Claude fills this in
        step1 = MathTex(r"FILL_IN").scale_to_fit_width(12)
        self.play(Write(step1))
        self.wait("BEAT_2")

        # Step 2 — Claude fills this in
        step2 = MathTex(r"FILL_IN").scale_to_fit_width(12)
        self.play(TransformMatchingTex(step1, step2))
        self.wait("BEAT_3")
```

---

## Stage 3: Self-Correction Loop

```
Generate code
     │
     ▼
Render preview (manim -ql, ~5 sec/clip)
Extract 5 key frames: t = 0%, 25%, 50%, 75%, 100%
     │
     ▼
Automated pixel check (PIL):
  - Any object within 5% of frame boundary?
  - Blank/black frame? (Manim crash indicator)
     │
     ├── Pass ──► Claude visual review (lighter prompt)
     └── Fail ──► Claude visual review (focused on flagged region)
          │
          ▼
     Claude outputs:
       APPROVED   ──────────────────────────────► Full render
       PATCH JSON
         { "line": 42,
           "old": ".move_to([3.5, 0, 0])",
           "new": ".move_to([2.8, 0, 0])" }
          │
          ▼
     Apply patch → re-render preview
     Round counter + 1
          │
     Round ≤ 3? ──yes──► back to review
          │
         no
          ▼
     Write to needs_review/
     Log: lesson_id, clip type, round count, last frames
     Continue to next clip
```

**Patch application:** Patches are strict JSON line replacements applied
deterministically. If a patch fails to apply (line mismatch after a prior patch),
the system requests a full rewrite of the file on that round instead.

**Failure manifest:** Each `needs_review/` entry includes:
- Lesson ID and course
- Which clip failed
- Contact sheet of last 5 frames (PIL montage)
- Claude's last review comment
- Round count and patch history

---

## Stage 4 & 5: Render + Audio

### Full render

```bash
manim -qh --format mp4 scene.py ClipClassName
```

Runs **after Stage 5 audio sync** — not immediately after Stage 3 approval. Stage 3
approves the layout; Stage 5 injects real beat durations into the source file and
re-renders at full quality with correct timing baked in. There is only one
full-quality render per clip.

### Audio pipeline

```
Beat-marker narration (from Stage 1 video plan)
         │
         ▼
OpenAI TTS (model: tts-1-hd, voice: onyx)
One API call per beat segment → beat_N.mp3
         │
         ▼
Inject real durations into Manim source:
  self.wait("BEAT_1") → self.wait(2.4)
  self.wait("BEAT_2") → self.wait(3.1)
         │
         ▼
Re-render Manim with correct timing
         │
         ▼
Concatenate beat audio files → narration.mp3
         │
         ▼
ffmpeg merge:
  ffmpeg -i clip.mp4 -i narration.mp3
         -c:v copy -c:a aac -shortest
         clip_with_audio.mp4
```

**Drift correction:** If an animation block runs longer than its narration beat,
up to 0.5 sec of silence is appended to that beat's audio. If narration runs over
the animation, ffmpeg `atempo` nudges playback speed by up to 5% — imperceptible
to listeners.

---

## Stage 6: Assembly & Storage

### Clip assembly

```bash
ffmpeg -f concat -safe 0 -i clip_list.txt -c copy lesson_full.mp4
```

`clip_list.txt` lists section clips in order: hook → concept → worked_example →
common_mistakes → summary.

### Video manifest

Written to `apps/api/data/video_manifests/{lesson_id}.json`:

```json
{
  "lesson_id": "a1_023",
  "generated_at": "2026-05-21T03:14:00Z",
  "full_video": "https://cdn.gradient.ai/videos/a1_023_full.mp4",
  "clips": {
    "hook":            { "url": "https://cdn.../a1_023_hook.mp4",     "duration_sec": 28 },
    "concept":         { "url": "https://cdn.../a1_023_concept.mp4",  "duration_sec": 47 },
    "worked_example":  { "url": "https://cdn.../a1_023_worked.mp4",   "duration_sec": 89 },
    "common_mistakes": { "url": "https://cdn.../a1_023_mistakes.mp4", "duration_sec": 34 },
    "summary":         { "url": "https://cdn.../a1_023_summary.mp4",  "duration_sec": 24 }
  }
}
```

### Storage

**Cloudflare R2** — S3-compatible API, zero egress fees for video streaming.
The existing FastAPI backend uses boto3-style access; R2 is a drop-in target.

---

## Website Integration

### Lesson page (Surface A)

A video player section appears above the written lesson content. The full video
loads by default; individual clips are accessible via a chapter selector.

```
┌─────────────────────────────────────┐
│  ▶  Graphing Linear Equations  3:42 │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  Chapters:                          │
│  0:00  Hook                         │
│  0:28  Concept                      │
│  1:15  Worked Example ◀ (current)   │
│  2:44  Common Mistakes              │
│  3:18  Summary                      │
└─────────────────────────────────────┘
```

The lesson page reads from the video manifest via a new API endpoint:
`GET /topics/{topic_id}/video` → returns the manifest JSON or 404 if not yet rendered.

### AI tutor (Surface B)

The tutor can emit a new WebSocket message type to the frontend:

```json
{ "type": "video", "clip": "worked_example", "lesson_id": "a1_023" }
```

The frontend renders this as an inline embedded player in the chat thread.

The tutor's system prompt for a session includes a summary of available clips:

```
Available video clips for this lesson:
- worked_example (1:29): shows solving x²-3x+2=0 step by step via factoring
- common_mistakes (0:34): covers sign errors and forgetting to check both roots
```

The tutor sends a clip when a student has made 2+ attempts at the same step
without progress (detected via existing misconception tracking).

---

## Batch Orchestration

### State file — `pipeline/state.json`

```json
{
  "a1_023": {
    "status": "done",
    "clips_done": ["hook", "concept", "worked_example", "common_mistakes", "summary"],
    "full_video": "outputs/a1_023_full.mp4",
    "correction_rounds": { "worked_example": 2 }
  },
  "a1_024": { "status": "rendering", "clips_done": ["hook", "concept"] },
  "a1_025": { "status": "needs_review", "failed_clip": "worked_example" }
}
```

`run.py` resumes from the last completed clip for any lesson in `rendering` state.
Lessons in `done` state are skipped entirely.

### Concurrency

3 parallel workers by default (configurable via `--workers N`). Each worker owns
one lesson at a time — completes all clips for that lesson before moving on.
3 workers ≈ 75–85% CPU utilization without thrashing.

`state.json` is protected by a file-level lock (Python `filelock`). Workers acquire
the lock only to read or write their lesson's entry — the lock is held for
milliseconds, never during rendering. This prevents race conditions without
meaningfully stalling workers.

### CLI

```bash
# Run everything (resumes automatically)
python pipeline/run.py

# Run a single lesson (for testing)
python pipeline/run.py --lesson a1_023

# Run one course only
python pipeline/run.py --course algebra1

# Re-run only needs_review lessons
python pipeline/run.py --only needs_review

# Show progress summary
python pipeline/status.py
```

### Status dashboard

```
Gradient Video Pipeline — Progress
────────────────────────────────────────
Done          312 / 865  ████████░░░░  36%
Rendering       3
Needs review   14
Pending       536

Estimated remaining: ~18 hours
Active workers: a1_089  a1_090  g1_012
```

---

## Out of Scope (Future Sub-Projects)

- **Sub-project 2:** Cloudflare R2 bucket setup, upload tooling, CDN configuration
- **Sub-project 3:** Lesson page video player component + chapter selector UI
- **Sub-project 4:** Tutor WebSocket `video` message type + inline chat player

These are independent and can be designed once the pipeline is producing good output
from a test batch of ~10 lessons.

---

## Cost Estimates

| Item | Unit cost | × 865 lessons | Total |
|---|---|---|---|
| Claude (plan + generate + correct) | ~$0.08/lesson | 865 | ~$70 |
| OpenAI TTS (tts-1-hd) | ~$0.03/1K chars | ~3M chars total | ~$90 |
| Cloudflare R2 storage | ~$0.015/GB/mo | ~50 GB | ~$0.75/mo |
| R2 egress | $0 | — | $0 |
| **Total one-time** | | | **~$160** |

Render time: ~1–3 days of continuous local CPU for 865 full lessons at 1080p.
