"""
Maps course and unit IDs to default student input modes.
Used at session_ready to tell the frontend which work panel to show by default.
"""

from __future__ import annotations

COURSE_INPUT_MODES: dict[str, str] = {
    "prealgebra":             "latex",
    "algebra_1":              "latex",
    "geometry":               "drawing",
    "algebra_2":              "latex",
    "precalculus":            "mixed",
    "calculus_1":             "latex",
    "calculus_2":             "latex",
    "calculus_3":             "latex",
    "differential_equations": "latex",
    "linear_algebra":         "latex",
    "discrete_math":          "latex",
    "proofs":                 "latex",
    "contest_math":           "mixed",
    "intro_prob_stats":       "latex",
    "probability":            "latex",
    "mathematical_statistics":"latex",
}

# Unit-level overrides (take precedence over course defaults)
UNIT_INPUT_MODES: dict[str, str] = {
    # Geometry: most units are drawing-first
    "geo_u01": "drawing",
    "geo_u02": "drawing",
    "geo_u03": "drawing",
    "geo_u04": "drawing",
    "geo_u05": "drawing",
    "geo_u06": "drawing",
    "geo_u07": "drawing",
    "geo_u08": "drawing",
    "geo_u09": "drawing",
    "geo_u10": "drawing",
    "geo_u11": "drawing",
    "geo_u12": "drawing",
    # Calculus: related rates and optimization benefit from diagrams
    "c1_u04": "mixed",
    "c1_u05": "mixed",
    # Contest math: geometry units are drawing-first
    "cm_u03": "drawing",
}


def get_input_mode(course_id: str, unit_id: str | None = None) -> str:
    """Return the recommended input mode for a course/unit pair."""
    if unit_id and unit_id in UNIT_INPUT_MODES:
        return UNIT_INPUT_MODES[unit_id]
    return COURSE_INPUT_MODES.get(course_id, "latex")
