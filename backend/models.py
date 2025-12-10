"""
Core data models for the math problem generator.

Defines Problem, Solution, and SolutionStep dataclasses.
"""

from dataclasses import dataclass, field
from typing import Literal


CalculatorMode = Literal["none", "scientific", "graphing"]


@dataclass
class SolutionStep:
    """Represents a single step in a step-by-step solution."""
    index: int
    description_latex: str  # Natural language explanation in LaTeX-ready text
    expression_latex: str   # Equation/expression after this step, in LaTeX


@dataclass
class Solution:
    """Represents a complete solution to a problem."""
    full_solution_latex: str  # Full worked solution in LaTeX, concatenating steps
    steps: list[SolutionStep]
    final_answer_latex: str   # LaTeX for the final value of x
    sympy_verified: bool
    verification_details: str | None = None


@dataclass
class Problem:
    """Represents a math problem."""
    id: str
    course_id: str
    unit_id: str
    topic_id: str
    difficulty: int                           # 1–4 for this topic
    calculator_mode: CalculatorMode
    prompt_latex: str                         # Problem statement in LaTeX
    answer_type: Literal["numeric", "expression"]
    final_answer: object                      # SymPy or Python object for the answer
    metadata: dict[str, object] = field(default_factory=dict)
    concept_ids: list[str] = field(default_factory=list)  # IDs of concepts this problem addresses
    primary_concept_id: str | None = None     # Primary concept this problem is tagged with
