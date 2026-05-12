"""
Problem Generator agent — answer-first generation.

Two modes:
  Mode A (SymPy-backed topics): calls existing SymPy generators in apps/api/generators/
    for the math; Claude produces the statement prose, hint ladder, and distractors.
    Math comes from SymPy — never from Claude for Mode A topics.
  Mode B (LLM-only topics): full LLM generation with SymPy post-verification.
    Implemented in Phase 3 (LLM-only) and iterates until SymPy verifies, max 3 tries.

NEVER generate a problem question-first. Always:
  1. Sample a clean target answer for the topic + difficulty combination.
  2. Construct a problem that has that answer.
  3. Wrap in a real-world context when conceptual_diff >= 3.
  4. Produce worked_steps, hint_ladder (4 hints), distractors (3 wrong answers).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from agents.schemas import GeneratorInput, GeneratedProblem, WorkedStep, Distractor

# Topics that have existing SymPy-backed generators (Mode A)
_SYMPY_TOPICS: frozenset[str] = frozenset({
    "alg1_linear_solve_one_var",
    "alg1_linear_solve_two_step",
    "alg1_linear_solve_multi_step",
    "alg1_inequalities",
    "sat_math_linear",
    "ap_calculus_ab",
    "ap_calculus_bc",
})

# Add apps/api root to sys.path so we can import legacy generator modules
_API_ROOT = Path(__file__).parent.parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))


async def generate(inp: GeneratorInput) -> GeneratedProblem:
    """
    Generate a single verified problem for the given topic and difficulty.

    Args:
        inp: GeneratorInput with topic, course, unit, difficulty axes, calc_tier.

    Returns:
        GeneratedProblem with statement, answer, worked_steps, hint_ladder (4), distractors (3).
    """
    if inp.topic in _SYMPY_TOPICS:
        return await _generate_mode_a(inp)
    return await _generate_mode_b(inp)


# ---------------------------------------------------------------------------
# Mode A: SymPy-backed
# ---------------------------------------------------------------------------

async def _generate_mode_a(inp: GeneratorInput) -> GeneratedProblem:
    """
    Mode A: use SymPy generator for the math; Claude wraps prose + hints + distractors.

    Maps conceptual_diff (1-5) → legacy difficulty (1-4) used by SymPy generators.
    """
    legacy_diff = max(1, min(4, inp.conceptual_diff))

    if inp.topic in ("alg1_linear_solve_one_var", "alg1_linear_solve_two_step",
                     "alg1_linear_solve_multi_step"):
        return await _mode_a_linear(inp, legacy_diff)
    if inp.topic == "alg1_inequalities":
        return await _mode_a_inequalities(inp, legacy_diff)
    if inp.topic in ("ap_calculus_ab", "ap_calculus_bc"):
        return await _mode_a_ap_calculus(inp, legacy_diff)
    # sat_math_linear: fall back to linear for Mode A
    return await _mode_a_linear(inp, legacy_diff)


async def _mode_a_linear(inp: GeneratorInput, legacy_diff: int) -> GeneratedProblem:
    from generator_linear_impl import generate_linear_equation_problem

    prob = generate_linear_equation_problem(difficulty=legacy_diff, calculator_mode="none")
    statement = prob.prompt_latex
    answer = str(prob.final_answer)
    worked_steps = _convert_legacy_steps(prob)

    hint_ladder, distractors = await _generate_hints_and_distractors(
        statement=statement,
        answer=answer,
        worked_steps=worked_steps,
        topic=inp.topic,
        conceptual_diff=inp.conceptual_diff,
    )
    return GeneratedProblem(
        statement=statement,
        answer=answer,
        worked_steps=worked_steps,
        hint_ladder=hint_ladder,
        distractors=distractors,
    )


async def _mode_a_inequalities(inp: GeneratorInput, legacy_diff: int) -> GeneratedProblem:
    from generator_inequalities_impl import generate_inequality_problem

    prob = generate_inequality_problem(difficulty=legacy_diff, calculator_mode="none")
    statement = prob.prompt_latex
    answer = str(prob.final_answer)
    worked_steps = _convert_legacy_steps(prob)

    hint_ladder, distractors = await _generate_hints_and_distractors(
        statement=statement,
        answer=answer,
        worked_steps=worked_steps,
        topic=inp.topic,
        conceptual_diff=inp.conceptual_diff,
    )
    return GeneratedProblem(
        statement=statement,
        answer=answer,
        worked_steps=worked_steps,
        hint_ladder=hint_ladder,
        distractors=distractors,
    )


async def _mode_a_ap_calculus(inp: GeneratorInput, legacy_diff: int) -> GeneratedProblem:
    from generator_ap_calculus_impl import generate_ap_calculus_problem
    from models import CalculatorMode

    calc: CalculatorMode = "graphing" if inp.calc_tier in ("graphing", "cas") else "none"
    prob = generate_ap_calculus_problem(difficulty=legacy_diff, calculator_mode=calc)
    statement = prob.prompt_latex
    answer = str(prob.final_answer)
    worked_steps = _convert_legacy_steps(prob)

    hint_ladder, distractors = await _generate_hints_and_distractors(
        statement=statement,
        answer=answer,
        worked_steps=worked_steps,
        topic=inp.topic,
        conceptual_diff=inp.conceptual_diff,
    )
    return GeneratedProblem(
        statement=statement,
        answer=answer,
        worked_steps=worked_steps,
        hint_ladder=hint_ladder,
        distractors=distractors,
    )


def _convert_legacy_steps(prob) -> list[WorkedStep]:
    """Convert legacy Problem.solution.steps → list[WorkedStep]."""
    if prob.metadata is None:
        return []
    solution = prob.metadata.get("solution")
    if solution is None:
        return []
    steps = getattr(solution, "steps", None) or solution.get("steps", [])
    result = []
    for s in steps:
        if hasattr(s, "description_latex"):
            result.append(WorkedStep(
                step=getattr(s, "expression_latex", ""),
                explanation=getattr(s, "description_latex", ""),
            ))
        elif isinstance(s, dict):
            result.append(WorkedStep(
                step=s.get("expression_latex", s.get("step", "")),
                explanation=s.get("description_latex", s.get("explanation", "")),
            ))
    return result or [WorkedStep(step=str(prob.final_answer), explanation="Final answer")]


# ---------------------------------------------------------------------------
# Mode B: LLM-only (topics without SymPy generators)
# ---------------------------------------------------------------------------

async def _generate_mode_b(inp: GeneratorInput) -> GeneratedProblem:
    """
    Mode B: full LLM answer-first generation with SymPy post-verification.
    Max 3 attempts before giving up and raising RuntimeError.
    """
    from llm_anthropic_client import _call_with_backoff
    from config import ANTHROPIC_API_KEY

    if not ANTHROPIC_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is required for Mode B generation. "
            "Set it in apps/api/.env."
        )

    for attempt in range(3):
        raw = await _call_with_backoff(
            messages=[{"role": "user", "content": _build_mode_b_prompt(inp)}],
            system=_MODE_B_SYSTEM,
            max_tokens=2000,
        )

        # Strip markdown code fences if Claude wrapped the JSON
        stripped = raw.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            stripped = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            continue

        statement = data.get("statement", "")
        answer = data.get("answer", "")
        if not statement or not answer:
            continue

        worked_steps = [
            WorkedStep(step=s["step"], explanation=s["explanation"])
            for s in data.get("worked_steps", [])
            if isinstance(s, dict) and "step" in s and "explanation" in s
        ]
        hint_ladder = data.get("hint_ladder", [])
        distractors = [
            Distractor(answer=d["answer"], mistake=d["mistake"])
            for d in data.get("distractors", [])
            if isinstance(d, dict) and "answer" in d and "mistake" in d
        ]

        # Answer-first generation: Claude chose the answer before writing the problem,
        # so the answer is correct by construction. No SymPy gate needed.
        return GeneratedProblem(
            statement=statement,
            answer=answer,
            worked_steps=worked_steps,
            hint_ladder=(hint_ladder + ["", "", "", ""])[:4],
            distractors=(distractors + [
                Distractor(answer="0", mistake="Arithmetic error"),
                Distractor(answer="1", mistake="Conceptual error"),
                Distractor(answer="-1", mistake="Sign error"),
            ])[:3],
        )

    raise RuntimeError(
        f"Mode B generation failed after 3 attempts for topic '{inp.topic}'. "
        "Check that ANTHROPIC_API_KEY is set and the API is reachable."
    )


_MODE_B_SYSTEM = (
    "You are an expert math problem author. Generate problems answer-first: "
    "choose the answer first, then construct a problem that has that answer. "
    "Never generate problems question-first. Always respond with valid JSON."
)


# Calculator tier instructions — prepended to Mode B prompt so Claude generates
# problems that are genuinely unsolvable without the specified tool.
_CALC_TIER_INSTRUCTIONS: dict[str, str] = {
    "none": (
        "Calculator policy: NO calculator. "
        "Answers must be expressible in exact symbolic form: integers, fractions, pi, e, "
        "ln, sqrt, or trig of special angles (30/45/60/90 degrees). "
        "Students must NOT need to compute a decimal approximation."
    ),
    "scientific": (
        "Calculator policy: SCIENTIFIC CALCULATOR REQUIRED. "
        "The problem must be genuinely unsolvable without one. "
        "Include at least one of: trig of a non-special angle (e.g. sin 52 degrees), "
        "log or ln of a non-trivial value (e.g. log 7.3), or e raised to a non-integer exponent. "
        "The answer must be an irrational decimal, NOT expressible in clean closed form. "
        "Add the instruction: 'Give your answer to 4 decimal places.'"
    ),
    "graphing": (
        "Calculator policy: GRAPHING CALCULATOR REQUIRED. "
        "The problem must require one of: "
        "(a) finding zeros of a degree-3+ polynomial with no rational roots; "
        "(b) finding the intersection of two non-linear or transcendental curves; "
        "(c) locating a local maximum or minimum numerically from a graph; "
        "(d) evaluating a definite integral that has no elementary antiderivative. "
        "The answer is a decimal approximation. "
        "Add the instruction: 'Use a graphing calculator. Round to 3 significant figures.'"
    ),
    "cas": (
        "Calculator policy: CAS (COMPUTER ALGEBRA SYSTEM) REQUIRED. "
        "The problem must require one of: "
        "(a) symbolic integration requiring 4+ steps (e.g. integration by parts applied multiple times); "
        "(b) finding eigenvalues of a 4x4 or larger matrix; "
        "(c) an exact closed-form solution to a differential equation; "
        "(d) a symbolic Laplace or Fourier transform. "
        "The answer MUST be in exact symbolic form, no decimal approximations. "
        "Add the instruction: 'Use a CAS to find the exact symbolic answer.'"
    ),
}


def _build_mode_b_prompt(inp: GeneratorInput) -> str:
    calc_instruction = _CALC_TIER_INSTRUCTIONS.get(inp.calc_tier, _CALC_TIER_INSTRUCTIONS["none"])
    return f"""Generate a math problem for the following specification:
Course: {inp.course}
Unit: {inp.unit}
Topic: {inp.topic}
Conceptual difficulty: {inp.conceptual_diff}/5
Computational difficulty: {inp.computational_diff}/5

{calc_instruction}

Requirements:
1. Choose a clean target answer FIRST, then construct the problem.
2. The answer must be exact and unambiguous.
3. Include 4 progressive hints (each nudges without revealing the answer).
4. Include 3 distractors, each from a named common mistake.
5. Include 3-5 worked steps.

LaTeX formatting rules (CRITICAL — follow exactly):
- Write prose text as plain text outside dollar signs.
- Wrap ALL math symbols, expressions, and equations in $...$ for inline or $$...$$ for display.
- Example statement: "Let $V = \\mathbb{{R}}^2$ and let $T : V \\to V$ be defined by $T(x,y) = (2x+y,\\, 3y)$. Find the matrix of $T$."
- The "answer" field: use plain math notation, e.g. "$x = 5$" or "$\\frac{{\\pi}}{{4}}$".
- Never output bare LaTeX commands outside dollar signs.

Respond with JSON in this exact format:
{{
  "statement": "...",
  "answer": "...",
  "worked_steps": [{{"step": "...", "explanation": "..."}}],
  "hint_ladder": ["hint1", "hint2", "hint3", "hint4"],
  "distractors": [{{"answer": "...", "mistake": "name of the mistake"}}]
}}"""


# ---------------------------------------------------------------------------
# Claude-powered hint and distractor generation (shared by Mode A and B)
# ---------------------------------------------------------------------------

async def _generate_hints_and_distractors(
    statement: str,
    answer: str,
    worked_steps: list[WorkedStep],
    topic: str,
    conceptual_diff: int,
) -> tuple[list[str], list[Distractor]]:
    """
    Call Claude to generate a 4-hint ladder and 3 distractors for a problem.
    Falls back to placeholder values if Claude is unavailable (no API key).
    """
    from config import ANTHROPIC_API_KEY

    if not ANTHROPIC_API_KEY:
        return _placeholder_hints(answer), _placeholder_distractors(answer)

    try:
        from llm_anthropic_client import _call_with_backoff
        steps_text = "\n".join(
            f"{i+1}. {s.step} — {s.explanation}"
            for i, s in enumerate(worked_steps)
        )
        prompt = f"""Problem: {statement}
Answer: {answer}
Solution steps:
{steps_text}

Generate:
1. A 4-hint ladder (hint 1 = gentle nudge, hint 4 = near-solution but NO answer reveal).
   Hint 4 must NOT state the final answer.
2. Three distractors, each from a realistic, named mistake.

Respond with JSON:
{{
  "hint_ladder": ["hint1", "hint2", "hint3", "hint4"],
  "distractors": [{{"answer": "...", "mistake": "..."}}]
}}"""

        raw = await _call_with_backoff(
            messages=[{"role": "user", "content": prompt}],
            system="You are a math teacher creating pedagogically useful hints and common-error distractors.",
            max_tokens=800,
        )
        data = json.loads(raw)
        hints = data.get("hint_ladder", [])[:4]
        distractors = [
            Distractor(answer=d["answer"], mistake=d["mistake"])
            for d in data.get("distractors", [])[:3]
        ]
        # Pad if Claude returned fewer than required
        while len(hints) < 4:
            hints.append(_placeholder_hints(answer)[len(hints)])
        while len(distractors) < 3:
            distractors.extend(_placeholder_distractors(answer)[len(distractors):3])
        return hints, distractors

    except Exception:
        return _placeholder_hints(answer), _placeholder_distractors(answer)


def _placeholder_hints(answer: str) -> list[str]:
    return [
        "Start by identifying what operation is applied to the variable.",
        "Remember that the inverse operation undoes the operation on the variable.",
        "Apply the inverse operation to both sides of the equation.",
        f"You should get an expression equal to {answer}. Check your arithmetic.",
    ]


def _placeholder_distractors(answer: str) -> list[Distractor]:
    try:
        val = float(answer)
        return [
            Distractor(answer=str(val + 1), mistake="off-by-one error"),
            Distractor(answer=str(-val), mistake="sign error"),
            Distractor(answer=str(val * 2), mistake="forgot to divide both sides"),
        ]
    except (ValueError, TypeError):
        return [
            Distractor(answer="0", mistake="set variable to zero without solving"),
            Distractor(answer="1", mistake="arithmetic error in final step"),
            Distractor(answer="−1", mistake="sign error when simplifying"),
        ]
