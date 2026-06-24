"""
Exam Mode — preset templates and template registry.

Each preset defines the problem count, time limit, calculator tier, and the
weighted concept distribution used to select topics from TOPIC_REGISTRY.

Structures (not verbatim questions) are not copyrightable — clean to replicate
SAT/AP distribution without licensing concerns.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ConceptDistribution:
    """Weighted group of courses from which exam problems are drawn."""
    course_ids: list[str]
    weight: float             # relative weight; will be normalized across groups
    difficulty_min: int = 2   # 1-5 conceptual difficulty floor
    difficulty_max: int = 4   # 1-5 conceptual difficulty ceiling


@dataclass
class ExamTemplate:
    id: str
    name: str
    description: str
    total_problems: int
    time_limit_minutes: Optional[int]   # None = untimed
    calc_tier: str                       # "none" | "scientific" | "graphing"
    concept_distribution: list[ConceptDistribution]
    kind: str = "preset"                 # "preset" | "custom"


PRESET_TEMPLATES: dict[str, ExamTemplate] = {
    "sat_math": ExamTemplate(
        id="sat_math",
        name="SAT Math",
        description="Algebra, advanced math, problem solving, and data analysis. No calculator.",
        total_problems=10,
        time_limit_minutes=25,
        calc_tier="none",
        concept_distribution=[
            ConceptDistribution(
                course_ids=["algebra_1", "algebra_2"],
                weight=0.5, difficulty_min=2, difficulty_max=4,
            ),
            ConceptDistribution(
                course_ids=["precalculus"],
                weight=0.3, difficulty_min=2, difficulty_max=4,
            ),
            ConceptDistribution(
                course_ids=["intro_prob_stats"],
                weight=0.2, difficulty_min=1, difficulty_max=3,
            ),
        ],
    ),

    "ap_calc_ab": ExamTemplate(
        id="ap_calc_ab",
        name="AP Calculus AB",
        description="Limits, derivatives, integrals, and the Fundamental Theorem of Calculus.",
        total_problems=12,
        time_limit_minutes=30,
        calc_tier="graphing",
        concept_distribution=[
            ConceptDistribution(
                course_ids=["calculus_1"],
                weight=1.0, difficulty_min=3, difficulty_max=5,
            ),
        ],
    ),

    "ap_calc_bc": ExamTemplate(
        id="ap_calc_bc",
        name="AP Calculus BC",
        description="All of Calc AB plus infinite series, parametric, and polar equations.",
        total_problems=12,
        time_limit_minutes=30,
        calc_tier="graphing",
        concept_distribution=[
            ConceptDistribution(
                course_ids=["calculus_1"],
                weight=0.5, difficulty_min=3, difficulty_max=5,
            ),
            ConceptDistribution(
                course_ids=["calculus_2"],
                weight=0.5, difficulty_min=3, difficulty_max=5,
            ),
        ],
    ),

    "ap_statistics": ExamTemplate(
        id="ap_statistics",
        name="AP Statistics",
        description="Data analysis, probability, inference, and regression.",
        total_problems=10,
        time_limit_minutes=25,
        calc_tier="scientific",
        concept_distribution=[
            ConceptDistribution(
                course_ids=["intro_prob_stats"],
                weight=1.0, difficulty_min=2, difficulty_max=4,
            ),
        ],
    ),
}
