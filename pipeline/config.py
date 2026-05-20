"""
Pipeline configuration — constants only, no logic.
All paths are absolute so stages can be called from any working directory.
"""
from __future__ import annotations

import os
from pathlib import Path

# ── Root paths ────────────────────────────────────────────────────────────────

PIPELINE_ROOT   = Path(__file__).parent
PROJECT_ROOT    = PIPELINE_ROOT.parent
API_ROOT        = PROJECT_ROOT / "apps" / "api"

OUTPUTS_DIR     = PIPELINE_ROOT / "outputs"
NEEDS_REVIEW_DIR = PIPELINE_ROOT / "needs_review"
PROMPTS_DIR     = PIPELINE_ROOT / "prompts"
TEMPLATES_DIR   = PIPELINE_ROOT / "templates"
VIZ_DIR         = PIPELINE_ROOT / "viz"

TOPIC_LESSONS_DIR = API_ROOT / "data" / "topic_lessons"

STATE_FILE      = PIPELINE_ROOT / "state.json"
LOCK_FILE       = PIPELINE_ROOT / "state.lock"

# ── Manim settings ────────────────────────────────────────────────────────────

MANIM_PREVIEW_QUALITY = "-ql"   # low quality, fast — used during correction loop
MANIM_RENDER_QUALITY  = "-qh"   # high quality 1080p — used for final render
MANIM_FORMAT          = "mp4"
PREVIEW_FRAME_COUNT   = 5       # frames extracted for visual review

# ── Correction loop ───────────────────────────────────────────────────────────

MAX_CORRECTION_ROUNDS = 3
BOUNDARY_MARGIN_PCT   = 0.05    # objects within 5% of frame edge trigger auto-flag
BLACK_FRAME_THRESHOLD = 0.90    # >90% black pixels = crash indicator

# ── Concurrency ───────────────────────────────────────────────────────────────

DEFAULT_WORKERS = 3

# ── API settings ──────────────────────────────────────────────────────────────

ANTHROPIC_MODEL    = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
OPENAI_TTS_MODEL   = "tts-1-hd"
OPENAI_TTS_VOICE   = "onyx"     # change to: alloy, echo, fable, nova, shimmer

# ── Clip ordering ─────────────────────────────────────────────────────────────

CLIP_ORDER = ["hook", "concept", "worked_example", "common_mistakes", "summary"]

# ── Frame dimensions (Manim default) ─────────────────────────────────────────

FRAME_WIDTH    = 14.222   # Manim units (1920px at 135px/unit)
FRAME_HEIGHT   = 8.0      # Manim units
SAFE_X_MIN     = -6.5
SAFE_X_MAX     =  6.5
SAFE_Y_MIN     = -3.5
SAFE_Y_MAX     =  3.5

# ── ffmpeg ────────────────────────────────────────────────────────────────────

def _find_ffmpeg() -> str:
    """Return ffmpeg path: system PATH first, then imageio-ffmpeg bundle."""
    import shutil
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"  # will fail loudly if not found

def _find_ffprobe() -> str:
    import shutil, os
    sys_ffprobe = shutil.which("ffprobe")
    if sys_ffprobe:
        return sys_ffprobe
    # Try same dir as imageio ffmpeg (usually ships with ffprobe too)
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        probe = os.path.join(os.path.dirname(ffmpeg_exe),
                             os.path.basename(ffmpeg_exe).replace("ffmpeg", "ffprobe"))
        if os.path.exists(probe):
            return probe
    except ImportError:
        pass
    return "ffprobe"

FFMPEG_EXE  = _find_ffmpeg()
FFPROBE_EXE = _find_ffprobe()

# Convenience aliases used by stages
FFMPEG_BIN  = FFMPEG_EXE
FFPROBE_BIN = FFPROBE_EXE

# ── Generated source / media directories ─────────────────────────────────────

GENERATED_DIR = str(PIPELINE_ROOT / "generated")   # AI-written .py files
MEDIA_DIR     = str(PIPELINE_ROOT.parent / "media") # Manim output & audio

# ── Manim quality flags (list form for subprocess) ───────────────────────────

MANIM_QL_FLAGS  = ["-ql"]   # 480p 15fps — fast preview / correction loop
MANIM_HQ_FLAGS  = ["-qh"]   # 1080p 60fps — final render

QA_FRAME_COUNT  = 5   # frames to extract per correction round

# ── Approved viz library class names ─────────────────────────────────────────

VIZ_TYPES: list[str] = [
    "SOHCAHTOAScene",
    "UnitCircleScene",
    "TrigGraphSyncScene",
    "ConicEccentricitySweepScene",
    "FunctionFamilySweepScene",
    "EquationTransformScene",
    "AngleSweepScene",
    "ParabolaConstructionScene",
    "EllipseConstructionScene",
    "LinearTransformPlaneScene",
    "ConicRotationScene",
    "CoordinatePlaneScene",
    "StepRevealScene",
    "EquationAnatomyScene",
    "NumberLineScene",
    "MistakeComparisonScene",
    "VectorDiagramScene",
    "GeometricFigureScene",
    "MatrixTransformScene",
    "BarChartScene",
    "ProbabilityTreeScene",
    "VennDiagramScene",
    "BalanceScaleScene",
    "ThreeDAxesScene",
    "ThreeDVectorsScene",
    "ThreeDSurfaceScene",
]
