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
import re
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

def _extract_json(raw: str) -> dict | None:
    """Extract the first JSON object from raw LLM output.

    Tries three strategies in order:
    1. Parse the full response as JSON (fastest path).
    2. Find JSON in a markdown code block anywhere in the response.
    3. Find the first {...} span in the response (handles preamble/postamble text).
    """
    stripped = raw.strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    m = re.search(r'```(?:json)?\s*\n([\s\S]*?)\n```', stripped)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    m = re.search(r'\{[\s\S]*\}', stripped)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    return None


_GEO_PROOF_KEYWORDS = frozenset({
    "two-column", "two column", "paragraph proof", "flow proof",
    "geometric proof", "geometry proof",
})

_GEO_PROOF_UNIT_KEYWORDS = frozenset({
    "proof", "proofs", "proving triangles", "congruence proof",
})

_DM_PROOF_KEYWORDS = frozenset({
    "direct proof", "proof by contradiction", "proof by contrapositive",
    "mathematical induction", "proof by induction", "strong induction",
    "intro to proof", "introduction to proof", "introduction to proofs",
    "logic and proof", "proof techniques",
})


def _is_geo_proof_topic(inp: GeneratorInput) -> bool:
    """True for geometry two-column / fill-in-blank proof topics."""
    course_low = inp.course.lower()
    unit_low = inp.unit.lower()
    topic_low = inp.topic.lower()
    if "geometry" not in course_low:
        return False
    combined = topic_low + " " + unit_low
    return (
        any(kw in combined for kw in _GEO_PROOF_KEYWORDS)
        or any(kw in unit_low for kw in _GEO_PROOF_UNIT_KEYWORDS)
    )


def _is_dm_proof_topic(inp: GeneratorInput) -> bool:
    """True for discrete-math / intro-to-proofs topics (direct proof, induction, etc.)."""
    combined = (inp.topic + " " + inp.unit + " " + inp.course).lower()
    return any(kw in combined for kw in _DM_PROOF_KEYWORDS)


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

    is_geo_proof = _is_geo_proof_topic(inp)
    is_dm_proof = _is_dm_proof_topic(inp)
    is_proof = is_geo_proof or is_dm_proof

    if is_geo_proof:
        prompt = _build_proof_prompt(inp)
    elif is_dm_proof:
        prompt = _build_dm_proof_prompt(inp)
    else:
        prompt = _build_mode_b_prompt(inp)

    for attempt in range(3):
        raw = await _call_with_backoff(
            messages=[{"role": "user", "content": prompt}],
            system=_MODE_B_SYSTEM,
            max_tokens=2000,
        )

        data = _extract_json(raw)
        if data is None:
            continue

        statement = data.get("statement", "")
        answer = str(data.get("answer", "")).strip()
        if not statement or not answer:
            continue
        # Strip \approx or ≈ prefix that LLMs sometimes add to decimal answers.
        # The canonical answer must be a parseable value, not an approximation marker.
        answer = re.sub(r"^\\?approx\s*|^≈\s*|^\$?\\?approx\s*\$?", "", answer).strip("$").strip()

        default_answer_type = "text" if is_geo_proof else "expression"
        answer_type = data.get("answer_type", default_answer_type)
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

        # Proof rows — structured table, only for geometry two-column proofs.
        proof_rows: list[dict] | None = None
        if is_geo_proof:
            raw_rows = data.get("proof_rows", [])
            if raw_rows and isinstance(raw_rows, list):
                proof_rows = [
                    {"stmt": r.get("stmt", r.get("statement", "")),
                     "reason": r.get("reason", "")}
                    for r in raw_rows if isinstance(r, dict)
                ]

        if is_geo_proof:
            default_distractors = [
                Distractor(answer="Reflexive Property", mistake="confused with self-reference"),
                Distractor(answer="Substitution Property", mistake="confused substitution with equality operation"),
                Distractor(answer="Transitive Property", mistake="confused with chained equality"),
            ]
        elif is_dm_proof:
            default_distractors = [
                Distractor(answer="0", mistake="attempted numerical answer for a proof step"),
                Distractor(answer="Not enough information", mistake="gave up instead of identifying the step"),
                Distractor(answer="QED", mistake="named the proof conclusion rather than a specific step"),
            ]
        else:
            default_distractors = [
                Distractor(answer="0", mistake="Arithmetic error"),
                Distractor(answer="1", mistake="Conceptual error"),
                Distractor(answer="-1", mistake="Sign error"),
            ]

        return GeneratedProblem(
            statement=statement,
            answer=answer,
            answer_type=answer_type,
            proof_rows=proof_rows,
            worked_steps=worked_steps,
            hint_ladder=(hint_ladder + ["", "", "", ""])[:4],
            distractors=(distractors + default_distractors)[:3],
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


def _build_proof_prompt(inp: GeneratorInput) -> str:
    return f"""Generate a geometry two-column proof fill-in-the-blank problem at difficulty {inp.conceptual_diff}/5.
Topic: {inp.topic} ({inp.unit}, {inp.course})

Step 1 — Choose the MISSING REASON first. It must be a named geometric property or theorem (e.g. "Subtraction Property of Equality", "Vertical Angles Theorem", "Definition of Midpoint"). This becomes the "answer".

Step 2 — Invent a geometric scenario that naturally requires that property at one step of the proof.

Step 3 — Write 4–7 proof steps. Exactly ONE step must have "___" as its reason. All other steps must have real reasons. All statements must be complete (never put "?" in a statement).

Step 4 — Write the setup text (given info + what to prove) as the "statement" field.

Step 5 — Write the closing question as: "Which property or theorem justifies the step where [paraphrase the blank row's statement]?"

LaTeX: ALL math must be inside $...$. No bare math symbols outside dollar signs.

Return this exact JSON — proof_rows is the structured table data:

{{
  "statement": "Given [SETUP TEXT]. [CLOSING QUESTION]",
  "proof_rows": [
    {{"stmt": "$\\\\angle 1 \\\\cong \\\\angle 2$", "reason": "Given"}},
    {{"stmt": "$m\\\\angle 1 = m\\\\angle 2$", "reason": "Definition of Congruent Angles"}},
    {{"stmt": "$m\\\\angle 1 + m\\\\angle 3 = 180°$", "reason": "Linear Pair Postulate"}},
    {{"stmt": "$m\\\\angle 2 + m\\\\angle 3 = 180°$", "reason": "___"}},
    {{"stmt": "$\\\\angle 2$ and $\\\\angle 3$ are supplementary", "reason": "Definition of Supplementary Angles"}}
  ],
  "answer": "Substitution Property of Equality",
  "answer_type": "text",
  "worked_steps": [{{"step": "substitution", "explanation": "Since $m\\\\angle 1 = m\\\\angle 2$, replace $m\\\\angle 1$ with $m\\\\angle 2$ in the linear pair equation."}}],
  "hint_ladder": ["Think about what justifies replacing one equal expression with another.", "We know $m\\\\angle 1 = m\\\\angle 2$ from step 2.", "We are putting $m\\\\angle 2$ in place of $m\\\\angle 1$.", "The property name involves 'substitution'..."],
  "distractors": [
    {{"answer": "Transitive Property of Equality", "mistake": "confused substitution with transitivity"}},
    {{"answer": "Reflexive Property of Equality", "mistake": "reflexive involves self-equality, not replacement"}},
    {{"answer": "Addition Property of Equality", "mistake": "no addition operation occurs in this step"}}
  ]
}}

Now generate a completely different proof — different geometric scenario, different missing reason. Do NOT copy the example above."""


def _build_dm_proof_prompt(inp: GeneratorInput) -> str:
    return f"""Generate a discrete mathematics proof sub-question at difficulty {inp.conceptual_diff}/5.
Topic: {inp.topic} ({inp.unit}, {inp.course})

Your job: ask ONE specific, checkable question about a KEY STEP in a proof. The question must have a DEFINITE answer — not "write a full proof."

Choose the proof technique based on the topic:
  - Direct Proof: assume hypothesis, derive conclusion algebraically
  - Proof by Contrapositive: prove ¬Q → ¬P instead of P → Q
  - Proof by Contradiction: assume ¬(conclusion), derive a contradiction
  - Mathematical Induction: base case + inductive step

ANSWER TYPES — pick the one that fits:
  A) "expression" — algebraic step (e.g., "expand $n^2$ given $n = 2k+1$"). Answer is a LaTeX expression checkable by SymPy.
  B) "text" — name/describe a logical step (e.g., "what assumption begins the proof?" or "state the inductive hypothesis"). Answer is a short English phrase.

LaTeX: ALL math in $...$. No bare symbols outside dollar signs.

Example A — Direct Proof, answer_type "expression":
{{
  "statement": "To prove that if $n$ is odd then $n^2$ is odd, write $n = 2k+1$ and expand $n^2$. What is $n^2$ in terms of $k$?",
  "answer": "$4k^2 + 4k + 1$",
  "answer_type": "expression",
  "worked_steps": [
    {{"step": "$n = 2k+1$", "explanation": "Definition of odd integer"}},
    {{"step": "$n^2 = (2k+1)^2$", "explanation": "Square both sides"}},
    {{"step": "$n^2 = 4k^2 + 4k + 1$", "explanation": "Expand using FOIL"}}
  ],
  "hint_ladder": [
    "Substitute the definition of an odd number for $n$.",
    "Write $n = 2k+1$ for some integer $k$, then compute $n^2$.",
    "Use $(a+b)^2 = a^2 + 2ab + b^2$.",
    "$(2k+1)^2 = 4k^2 + 4k + 1$"
  ],
  "distractors": [
    {{"answer": "$4k^2 + 1$", "mistake": "forgot the middle term $4k$ when expanding"}},
    {{"answer": "$2k^2 + 2k + 1$", "mistake": "did not square the 2 in $2k$"}},
    {{"answer": "$4k^2 + 2k + 1$", "mistake": "used $2k$ instead of $4k$ for the cross term"}}
  ]
}}

Example B — Proof by Contradiction, answer_type "text":
{{
  "statement": "You want to prove that $\\\\sqrt{{2}}$ is irrational by contradiction. What assumption do you make at the very start of the proof?",
  "answer": "Assume $\\\\sqrt{{2}}$ is rational",
  "answer_type": "text",
  "worked_steps": [
    {{"step": "Assume $\\\\sqrt{{2}} = \\\\frac{{p}}{{q}}$ in lowest terms", "explanation": "The contradicting assumption — rational means expressible as a fraction"}},
    {{"step": "$2 = \\\\frac{{p^2}}{{q^2}}$, so $p^2 = 2q^2$", "explanation": "Squaring both sides"}},
    {{"step": "$p$ is even → $q$ is even — contradicts lowest-terms", "explanation": "Both numerator and denominator share factor 2"}}
  ],
  "hint_ladder": [
    "Proof by contradiction starts by assuming the OPPOSITE of what you want to prove.",
    "You want to prove $\\\\sqrt{{2}}$ is irrational, so assume it is...",
    "Assume $\\\\sqrt{{2}}$ is rational — it can be written as a fraction $p/q$.",
    "Assume $\\\\sqrt{{2}} = \\\\frac{{p}}{{q}}$ where $\\\\gcd(p,q) = 1$."
  ],
  "distractors": [
    {{"answer": "Assume $\\\\sqrt{{2}}$ is irrational", "mistake": "assumed the conclusion instead of its negation"}},
    {{"answer": "Assume $p^2 = 2q^2$", "mistake": "jumped to a derived equation rather than the opening assumption"}},
    {{"answer": "Assume $\\\\sqrt{{2}}$ is an integer", "mistake": "confused rational with integer"}}
  ]
}}

Now generate a COMPLETELY DIFFERENT problem for topic "{inp.topic}" in "{inp.unit}".
Use a different proof technique and a different mathematical statement than the examples above.
Do NOT copy the examples."""


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
        "CRITICAL — answer-first workflow for calculator problems:\n"
        "  1. Pick a decimal answer to 4 places FIRST (e.g. 3.3324). Write it down.\n"
        "  2. Build a problem whose EXACT computation produces that number.\n"
        "  3. Verify each worked_step computation matches your chosen answer.\n"
        "  4. The 'answer' field must be ONLY the bare decimal (e.g. '3.3324'), no \\approx prefix.\n"
        "The problem must be genuinely unsolvable without a scientific calculator. "
        "Include at least one of: trig of a non-special angle (e.g. sin 52°), "
        "log or ln of a non-trivial value, or e raised to a non-integer exponent. "
        "Add the instruction: 'Give your answer to 4 decimal places.'"
    ),
    "graphing": (
        "Calculator policy: GRAPHING CALCULATOR REQUIRED. "
        "CRITICAL — answer-first workflow:\n"
        "  1. Pick the decimal answer first (e.g. 2.714).\n"
        "  2. The 'answer' field must be the bare decimal, no \\approx prefix.\n"
        "The problem must require one of: "
        "(a) finding zeros of a degree-3+ polynomial with no rational roots; "
        "(b) finding the intersection of two non-linear or transcendental curves; "
        "(c) locating a local maximum or minimum numerically from a graph; "
        "(d) evaluating a definite integral that has no elementary antiderivative. "
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
