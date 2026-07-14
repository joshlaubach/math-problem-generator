"""
Skills registry — probe the problem/topic/message and load only the expertise
blocks that match (Phase 2: skills discovery).

This generalizes the coarse per-course TOPIC_GUIDANCE routing in
agents/tutor_guide.py into finer-grained, individually-triggered skills:
a derivatives question loads derivative_rules (and maybe chain_rule), not the
whole calculus block. Rules:

  - At most MAX_SKILLS load per turn, bounded by TOKEN_BUDGET total — the
    context must not bloat (the constitution + snippets already ride along).
  - Selection is deterministic (scores, then id order) and the rendered block
    sorts by skill id, so the bytes are cache-stable for prompt caching.
  - When any skill matches, it REPLACES the coarse topic guidance for that
    turn (no double-loading of overlapping content).

Curriculum-as-code: skills live here as Python data, same as taxonomy.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

# Course-family prefixes → family keys (mirrors tutor_guide._COURSE_FAMILY_MAP)
_FAMILY_PREFIXES: dict[str, str] = {
    "arith": "arithmetic",
    "fraction": "arithmetic",
    "prealg": "arithmetic",
    "alg1": "algebra_1",
    "algebra_1": "algebra_1",
    "linear": "algebra_1",
    "alg2": "algebra_2",
    "algebra_2": "algebra_2",
    "precalc": "algebra_2",
    "pre_calc": "algebra_2",
    "geo": "geometry",
    "geometry": "geometry",
    "proof": "geometry",
    "calc": "calculus",
    "calculus": "calculus",
    "ap_calc": "calculus",
    "apcalc": "calculus",
    "diffeq": "calculus",
    "linalg": "linear_algebra",
    "stat": "statistics",
    "statistics": "statistics",
    "prob": "statistics",
    "sat": "algebra_1",
}


def _family_for_topic(topic_id: str) -> Optional[str]:
    t = (topic_id or "").lower()
    for prefix, fam in _FAMILY_PREFIXES.items():
        if t.startswith(prefix):
            return fam
    return None


@dataclass(frozen=True)
class Skill:
    id: str
    name: str
    families: frozenset  # course families where this skill is plausible
    pattern: "re.Pattern"  # keyword probe against problem statement + message
    prompt_block: str
    token_cost: int = field(default=0)

    def __post_init__(self):
        object.__setattr__(self, "token_cost", max(1, len(self.prompt_block) // 4))


def _skill(id_: str, name: str, families: set, keywords: str, block: str) -> Skill:
    return Skill(
        id=id_, name=name, families=frozenset(families),
        pattern=re.compile(keywords, re.IGNORECASE),
        prompt_block=f"### Skill: {name}\n\n{block.strip()}",
    )


SKILLS: list[Skill] = [
    _skill(
        "derivative_rules", "Derivative Rules",
        {"calculus"},
        r"\bderiv|d/dx|\bdifferentiat|f'\(|\brate of change\b|\btangent line\b",
        """
Power rule: $\\frac{d}{dx}x^n = nx^{n-1}$. Product: $(fg)' = f'g + fg'$.
Quotient: low-d-high minus high-d-low, over low squared. Common student errors:
forgetting the product rule and differentiating factor-by-factor; treating a
constant base like a variable ($\\frac{d}{dx}2^x \\neq x\\cdot2^{x-1}$ — it is
$2^x\\ln 2$). Diagnostic: ask what KIND of function each factor is before any
rule is named. Anchor derivatives as instantaneous rate of change (speedometer
analogy) before symbol-pushing.
""",
    ),
    _skill(
        "chain_rule", "Chain Rule",
        {"calculus"},
        r"\bchain rule\b|composite|\bsin\(.*x.*\)|\bcos\(|\be\^\{?\(|\(.*x.*\)\^\d|\bnested\b",
        """
Trigger question: "Is this a function of $x$, or a function of SOMETHING that
is a function of $x$?" If the latter, chain rule. Structure the work as
outer-then-inner: name $u = g(x)$ explicitly, differentiate the outer with
respect to $u$, multiply by $u'$. The dominant error is dropping the inner
derivative ($\\frac{d}{dx}\\sin(5x) = \\cos(5x)$ instead of $5\\cos(5x)$) —
when it appears, have the student re-identify the inner function aloud before
recomputing. Never accept "I multiplied by the inside" without them naming it.
""",
    ),
    _skill(
        "integration_techniques", "Integration Techniques",
        {"calculus"},
        r"\bintegra|antideriv|\\int|\barea under\b|\bu-sub|by parts\b",
        """
Route by form: recognizable antiderivative → direct; composite with the inner
derivative present (up to a constant) → u-substitution; product of unrelated
types (poly·exp, poly·trig, log·poly) → parts with LIATE. u-sub discipline:
the student must rewrite EVERYTHING in $u$ (including $dx$) before
integrating — mixed-variable integrands are the top error. Indefinite
integrals require $+C$ every time; ask "definite or indefinite?" whenever a
number vs. function confusion appears. Anchor integration as accumulation
(odometer from a speedometer).
""",
    ),
    _skill(
        "factoring_quadratics", "Factoring Quadratics",
        {"algebra_1", "algebra_2"},
        r"\bfactor|quadratic|x\^2|x\*\*2|\broots?\b|\bzeroes\b|\bzeros\b",
        """
For $x^2+bx+c$: an organized SEARCH, not a guess — list factor pairs of $c$,
test which sums to $b$. For $a\\neq1$: one method consistently (AC method).
Discriminant check $b^2-4ac$: perfect square ⇔ factors over the integers —
use it when a student insists "it doesn't factor." Sign errors dominate:
when $c>0$ both binomial signs match $b$; when $c<0$ they differ. Keep
"factoring an expression" and "solving an equation" verbally distinct; the
zero-product property is the bridge and deserves its own sentence.
""",
    ),
    _skill(
        "linear_equations", "Linear Equations",
        {"algebra_1", "arithmetic"},
        r"solve for|\blinear\b|\bequation\b.*x|2x|3x|\bbalance\b|\bisolate\b",
        """
One principle: do the same thing to the whole of both sides. The classic slip
is applying an operation to one term only ($2x+4=10$, divide by 2 →
$x+4=5$): make division explicit as $\\frac{2x+4}{2}$ so the parentheses
force full application. "Moving" a term is shorthand for an inverse operation
— until that is automatic, require the explicit inverse-operation line.
Balance-scale and box-with-a-number analogies land well here. Check by
substitution is non-negotiable after solving.
""",
    ),
    _skill(
        "geometry_proofs", "Geometry Proofs",
        {"geometry"},
        r"\bproo?f|\bprove\b|\btwo.column\b|\bcongruen|\bsimilar\b|\btheorem\b",
        """
Reframe first: a proof is a logical argument where every step has a reason
(given, definition, or theorem) — not an exercise in naming theorems. For a
lost student, use fill-in-the-blank scaffolds: steps given, student supplies
reasons (or the reverse) — separating "finding the path" from "naming the
steps." Teach working from both ends until they meet. Police circular
reasoning ("you assumed what you're proving") and unjustified "obvious" steps
by asking "why is that true?" at each line.
""",
    ),
    _skill(
        "probability_rules", "Probability Rules",
        {"statistics"},
        r"\bprobabilit|P\(|\bdice\b|\bcoin\b|\bcards?\b|\bindependen|\bmutually exclusive\b",
        """
Before any rule: what is the sample space? Addition rule needs mutual
exclusivity checked; multiplication needs independence checked — the dominant
error is applying either without the check. "Or" ⇒ add (minus overlap);
"and" ⇒ multiply (conditioning if dependent). With-vs-without replacement
changes everything; ask which one the problem states. For conditional
probability, restate $P(A\\mid B)$ in words ("of the times B happens, how
often A?") before formulas.
""",
    ),
    _skill(
        "matrix_operations", "Matrix Operations",
        {"linear_algebra", "algebra_2"},
        r"\bmatri|\baugmented\b|\brow.reduc|\bdetermin|\beigen|\bvector space\b|\bdot product\b",
        """
Dimensions first, always: an $m\\times n$ times $n\\times p$ gives
$m\\times p$ — have the student verify compatibility before multiplying.
Row-by-column discipline for products; entry $(i,j)$ = row $i$ dotted with
column $j$. Row reduction: name each elementary operation explicitly
($R_2 \\to R_2 - \\tfrac12 R_1$) — sign errors in the multiplier are the top
slip. Matrix multiplication is not commutative; when a student swaps factors,
make them test a small numeric example rather than telling them.
""",
    ),
    _skill(
        "trig_identities", "Trig Identities & Equations",
        {"algebra_2", "calculus", "geometry"},
        r"\bsin\b|\bcos\b|\btan\b|\bidentit|\bunit circle\b|\bradian|\btrig",
        """
Everything routes through the unit circle: $\\sin$ is the $y$-coordinate,
$\\cos$ the $x$. Pythagorean identity $\\sin^2\\theta+\\cos^2\\theta=1$ is
the parent of the other two (divide by $\\cos^2$ or $\\sin^2$ — derive, don't
memorize). Solving trig equations: isolate the trig function first, find the
reference angle, then enumerate ALL solutions in the interval — dropping the
second quadrant solution is the dominant error. Degrees vs radians: check the
mode/units before anything else when answers are "close but wrong."
""",
    ),
    _skill(
        "statistics_inference", "Statistical Inference",
        {"statistics"},
        r"\bp.value\b|hypothesis|confidence interval|\bsample\b|\bnull\b|\bz.score\b|\bt.test\b|standard deviation",
        """
Descriptive vs inferential is the load-bearing distinction — describing THIS
data vs concluding about a population from a sample. A p-value is the
probability of data this extreme IF the null were true; it is not the
probability the null is true, and $p<0.05$ does not mean "important."
Confidence intervals: the confidence is in the PROCEDURE, not any single
interval. Correlation ≠ causation gets a counterexample first, every time.
Check sampling assumptions (random? independent? n large enough?) before any
formula is allowed on the board.
""",
    ),
]

_BY_ID = {s.id: s for s in SKILLS}

MAX_SKILLS = 2
TOKEN_BUDGET = 1200


def select_skills(
    session: Any,
    student_message: str,
    problem_statement: str = "",
) -> list[Skill]:
    """
    Score every skill against the session's course family and a keyword probe
    of the problem + message; return the top matches (≤MAX_SKILLS, within
    TOKEN_BUDGET). Deterministic: (score desc, id asc).
    """
    topic_id = getattr(session, "topic_id", None) or (
        (getattr(session, "topic_ids", None) or [""])[0]
    )
    family = _family_for_topic(topic_id or "")
    probe_problem = problem_statement or ""
    probe_message = student_message or ""

    scored: list[tuple[int, str, Skill]] = []
    for skill in SKILLS:
        score = 0
        if family is not None and family in skill.families:
            score += 2
        problem_hit = bool(skill.pattern.search(probe_problem))
        message_hit = bool(skill.pattern.search(probe_message))
        if problem_hit:
            score += 2
        if message_hit:
            score += 1
        # Keyword evidence is required — family alone stays on the coarse
        # TOPIC_GUIDANCE path. A problem-keyword hit alone is enough (freeform
        # sessions have no topic_id); a message-only hit is too weak by itself.
        if (problem_hit or message_hit) and score >= 2:
            scored.append((score, skill.id, skill))

    scored.sort(key=lambda t: (-t[0], t[1]))

    picked: list[Skill] = []
    budget = TOKEN_BUDGET
    for _score, _id, skill in scored:
        if len(picked) >= MAX_SKILLS:
            break
        if skill.token_cost > budget:
            continue
        picked.append(skill)
        budget -= skill.token_cost
    return picked


def skills_block(selected: list[Skill]) -> Optional[str]:
    """Render selected skills as a deterministic prompt block (sorted by id
    so identical selections produce identical bytes — prompt-cache safe)."""
    if not selected:
        return None
    parts = [s.prompt_block for s in sorted(selected, key=lambda s: s.id)]
    return "## Loaded Skills\n\n" + "\n\n".join(parts)
