"""
Shared Pydantic schemas for agent inputs and outputs.
All agents are stateless — context is passed per-request.
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class OrchestratorRequest(BaseModel):
    action: Literal[
        "get_problem",
        "check_answer",
        "get_hint",
        "get_solution",
        "get_recommendation",
        "get_analytics",
    ]
    user_id: str
    topic_id: Optional[str] = None
    problem_id: Optional[str] = None
    student_answer: Optional[str] = None
    hint_level: Optional[int] = Field(None, ge=1, le=4)
    assignment_id: Optional[str] = None
    classroom_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Problem Generator
# ---------------------------------------------------------------------------

class WorkedStep(BaseModel):
    step: str
    explanation: str


class Distractor(BaseModel):
    answer: str
    mistake: str


class GeneratorInput(BaseModel):
    topic: str
    course: str
    unit: str
    conceptual_diff: int = Field(..., ge=1, le=5)
    computational_diff: int = Field(..., ge=1, le=5)
    calc_tier: Literal["none", "scientific", "graphing", "cas"] = "none"


class GeneratedProblem(BaseModel):
    statement: str
    answer: str
    worked_steps: list[WorkedStep]
    hint_ladder: list[str] = Field(..., min_length=4, max_length=4)
    distractors: list[Distractor] = Field(..., min_length=3, max_length=3)
    # "expression" (default), "numeric", "text" (proof reasons / theorem names)
    answer_type: str = "expression"
    # Two-column proof rows: [{"stmt": "...", "reason": "..."}, ...], reason "___" = blank
    proof_rows: Optional[list[dict]] = None
    # Bank identity: set when the problem came from / was persisted to the
    # problem bank. Drives per-student served-problem dedup. None for
    # ephemeral problems (uploads, dev without persistence).
    problem_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Debate Agent
# ---------------------------------------------------------------------------

class DebateRequest(BaseModel):
    task: Literal["problem_generation", "solution_explanation", "hint_ladder"]
    context: dict
    rounds: int = Field(default=2, ge=1)  # cost guard enforced in debate.run(), not here


class DebateResult(BaseModel):
    winner: Literal["A", "B", "neither"]
    output: Optional[dict] = None
    reason: str
    tokens_used: int = 0


# ---------------------------------------------------------------------------
# Verifier
# ---------------------------------------------------------------------------

class VerifierResult(BaseModel):
    verified: bool
    reason: str


# ---------------------------------------------------------------------------
# Answer Checker
# ---------------------------------------------------------------------------

class CheckAnswerRequest(BaseModel):
    student_answer: str
    canonical_answer: str
    answer_type: str = "algebraic"


class CheckAnswerResult(BaseModel):
    correct: bool
    equivalent_form: bool
    partial_credit_reason: Optional[str] = None
    severity: Optional[Literal["careless", "method", "fundamental"]] = None


# ---------------------------------------------------------------------------
# Hint Scaffolder
# ---------------------------------------------------------------------------

class HintRequest(BaseModel):
    problem_id: str
    hint_ladder: list[str]  # pre-generated 4-hint ladder from Problem record
    student_attempt: Optional[str] = None
    hint_level: int = Field(..., ge=1, le=4)


# ---------------------------------------------------------------------------
# Solution Explainer
# ---------------------------------------------------------------------------

class SolutionRequest(BaseModel):
    problem_id: str
    problem_statement: str
    worked_steps: list[WorkedStep]
    student_attempts: list[str]


class SolutionExplanation(BaseModel):
    explanation: str


# ---------------------------------------------------------------------------
# Adaptive Engine
# ---------------------------------------------------------------------------

class AdaptiveInput(BaseModel):
    user_id: str
    recent_attempts: list[dict]
    progress_records: list[dict]


class AdaptiveOutput(BaseModel):
    recommended_topic_id: str
    difficulty_adjustment: Literal[-1, 0, 1]
    topics_for_review: list[str]
    rationale: str


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

class AnalyticsInput(BaseModel):
    classroom_id: str
    student_mastery: list[dict]
    topic_stats: list[dict]
    inactive_students: list[str]


class AnalyticsOutput(BaseModel):
    insights: str
