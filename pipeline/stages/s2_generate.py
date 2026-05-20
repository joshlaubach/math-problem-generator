"""
pipeline/stages/s2_generate.py — Stage 2: Generate Manim source for each clip.

For each clip in the lesson plan, asks the LLM to write a Manim Scene class
using the appropriate viz template as a starting point.  Uses self.wait("BEAT_N")
placeholders that Stage 5 will later replace with actual TTS durations.
"""
from __future__ import annotations
import os
import re
import logging
import importlib.util
from typing import Any

from pipeline.config import ANTHROPIC_MODEL, GENERATED_DIR
from pipeline.state import read_state, write_state, mark_clip_done

logger = logging.getLogger(__name__)

_PROMPT_DIR  = os.path.join(os.path.dirname(__file__), "..", "prompts")
_TMPL_DIR    = os.path.join(os.path.dirname(__file__), "..", "templates")
_VIZ_DIR     = os.path.join(os.path.dirname(__file__), "..", "viz")


def _load_txt(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


GENERATE_SYSTEM = _load_txt(os.path.join(_PROMPT_DIR, "generate_prompt.txt"))
LAYOUT_BIBLE    = _load_txt(os.path.join(_PROMPT_DIR, "layout_bible.txt"))
MATH_TO_SPEECH  = _load_txt(os.path.join(_PROMPT_DIR, "math_to_speech.txt"))


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------

def _load_template(clip_type: str) -> str:
    """Load the Manim skeleton for a given clip type."""
    fname = os.path.join(_TMPL_DIR, f"{clip_type}.py")
    if os.path.exists(fname):
        return _load_txt(fname)
    return ""


def _load_viz_source(viz_type: str) -> str:
    """
    Load the viz library source for *viz_type* so the LLM can see what
    configurable attributes are available.
    """
    # Map class name → file (simple snake_case heuristic)
    # e.g. SOHCAHTOAScene → sohcahtoa.py, StepRevealScene → step_reveal.py
    name_map = {
        "SOHCAHTOAScene":               "sohcahtoa.py",
        "UnitCircleScene":              "unit_circle.py",
        "TrigGraphSyncScene":           "trig_graph_sync.py",
        "ConicEccentricitySweepScene":  "parameter_sweep.py",
        "FunctionFamilySweepScene":     "parameter_sweep.py",
        "EquationTransformScene":       "equation_transform.py",
        "AngleSweepScene":              "angle_sweep.py",
        "ParabolaConstructionScene":    "geometric_construction.py",
        "EllipseConstructionScene":     "geometric_construction.py",
        "LinearTransformPlaneScene":    "linear_transform_plane.py",
        "ConicRotationScene":           "linear_transform_plane.py",
        "CoordinatePlaneScene":         "coordinate_plane.py",
        "StepRevealScene":              "step_reveal.py",
        "EquationAnatomyScene":         "equation_anatomy.py",
        "NumberLineScene":              "number_line.py",
        "MistakeComparisonScene":       "mistake_comparison.py",
        "VectorDiagramScene":           "vector_diagram.py",
        "GeometricFigureScene":         "geometric_figure.py",
        "MatrixTransformScene":         "matrix_transform.py",
        "BarChartScene":                "bar_chart.py",
        "ProbabilityTreeScene":         "probability_tree.py",
        "VennDiagramScene":             "venn_diagram.py",
        "BalanceScaleScene":            "balance_scale.py",
        "ThreeDAxesScene":              "threed_axes.py",
        "ThreeDVectorsScene":           "threed_vectors.py",
        "ThreeDSurfaceScene":           "threed_surface.py",
    }
    fname = name_map.get(viz_type)
    if fname:
        path = os.path.join(_VIZ_DIR, fname)
        if os.path.exists(path):
            return _load_txt(path)
    return ""


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def regenerate_clip(lesson_id: str, clip_type: str) -> str:
    """
    Regenerate the Manim source for ONE clip only.
    Used by the Stage 3 correction loop when a single clip needs a full rewrite.
    Returns the output file path.
    """
    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError("anthropic package not installed") from e

    state = read_state(lesson_id)
    plan  = state.get("plan")
    if not plan:
        raise ValueError(f"[{lesson_id}] No plan found")

    clip = next((c for c in plan.get("clips", []) if c["clip_type"] == clip_type), None)
    if not clip:
        raise ValueError(f"[{lesson_id}] Clip type {clip_type!r} not in plan")

    client    = anthropic.Anthropic()
    out_path  = os.path.join(GENERATED_DIR, lesson_id, f"{clip_type}.py")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    logger.info("[%s] Regenerating %s (single-clip rewrite)", lesson_id, clip_type)
    source = _generate_clip(client, lesson_id, clip, plan)
    source = _post_process(source, clip_type, lesson_id)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(source)

    logger.info("[%s] %s rewritten → %s", lesson_id, clip_type, out_path)
    return out_path


def run(lesson_id: str) -> list[str]:
    """
    Generate Manim Python source for every clip in the lesson plan.
    Returns list of output file paths.
    """
    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError("anthropic package not installed") from e

    state = read_state(lesson_id)
    plan  = state.get("plan")
    if not plan:
        raise ValueError(f"[{lesson_id}] No plan found — run Stage 1 first")

    client     = anthropic.Anthropic()
    out_paths  = []
    lesson_dir = os.path.join(GENERATED_DIR, lesson_id)
    os.makedirs(lesson_dir, exist_ok=True)

    for clip in plan["clips"]:
        clip_type = clip["clip_type"]
        out_path  = os.path.join(lesson_dir, f"{clip_type}.py")

        # Skip if already generated and not stale
        existing = state.get("clips_done", [])
        if clip_type in existing and os.path.exists(out_path):
            logger.info("[%s] %s already generated — skipping", lesson_id, clip_type)
            out_paths.append(out_path)
            continue

        logger.info("[%s] Stage 2 — generating %s", lesson_id, clip_type)
        source = _generate_clip(client, lesson_id, clip, plan)
        source = _post_process(source, clip_type, lesson_id)

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(source)

        out_paths.append(out_path)
        logger.info("[%s] %s written to %s", lesson_id, clip_type, out_path)

    write_state(lesson_id, {"stage": "generated"})
    return out_paths


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_clip(client: Any, lesson_id: str, clip: dict, plan: dict) -> str:
    """Call the LLM for one clip and return raw Python source."""
    viz_type = clip.get("viz_type", "StepRevealScene")
    template = _load_template(clip["clip_type"])
    viz_src  = _load_viz_source(viz_type)

    user_msg = _build_user_message(lesson_id, clip, plan, template, viz_src)

    resp = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=3000,
        system=f"{GENERATE_SYSTEM}\n\n{LAYOUT_BIBLE}",
        messages=[{"role": "user", "content": user_msg}],
    )
    return resp.content[0].text.strip()


def _build_user_message(
    lesson_id: str,
    clip: dict,
    plan: dict,
    template: str,
    viz_src: str,
) -> str:
    parts = [
        f"Lesson ID: {lesson_id}",
        f"Clip type: {clip['clip_type']}",
        f"Title: {clip.get('title', '')}",
        f"Viz type to subclass: {clip.get('viz_type', 'StepRevealScene')}",
        "",
        "## Beats (narration):",
    ]
    for i, beat in enumerate(clip.get("beats", []), 1):
        parts.append(f"  BEAT_{i}: {beat}")

    if clip.get("viz_config"):
        import json
        parts += ["", "## Viz config hints:", json.dumps(clip["viz_config"], indent=2)]

    if template:
        parts += ["", "## Template to fill in:", "```python", template, "```"]

    if viz_src:
        parts += ["", "## Viz library source (read class attributes to understand config):", "```python", viz_src, "```"]

    parts += [
        "",
        "Write the complete Python file. "
        "Subclass the viz type shown above, override class attributes to match the content, "
        "use self.wait('BEAT_N') for every narration beat. "
        "Output ONLY Python — no prose, no markdown fences.",
    ]
    return "\n".join(parts)


def _post_process(source: str, clip_type: str, lesson_id: str) -> str:
    """Strip accidental markdown fences and add a header comment."""
    source = re.sub(r"^```(?:python)?\s*\n?", "", source, flags=re.MULTILINE)
    source = re.sub(r"\n?```\s*$",            "", source, flags=re.MULTILINE)
    source = source.strip()

    header = (
        f"# Generated by pipeline/stages/s2_generate.py\n"
        f"# lesson_id={lesson_id}  clip_type={clip_type}\n"
        f"# DO NOT EDIT — re-run Stage 2 to regenerate\n\n"
    )
    return header + source
