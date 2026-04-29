"""
Multi-agent debate coordinator.

Used for offline, high-stakes generation tasks ONLY:
  - problem_generation (rounds=2, default)
  - solution_explanation (rounds=1, real-time — only called when student gives up)
  - hint_ladder (rounds=2)

NEVER called during real-time student paths: answer checking, adaptive recommendations.

Protocol (per round):
  1. Instance A and B generate independently via asyncio.gather (parallel).
  2. Each instance critiques the other against a task-specific rubric and revises.
  3. A judge prompt selects the stronger output. Returns 'neither' if both fail.
  4. Caller retries from scratch on 'neither' (max 3 total attempts).

Cost guard: rounds > 3 raises ValueError to prevent runaway loops.
"""

from __future__ import annotations

import asyncio
import json
import time

from agents.schemas import DebateRequest, DebateResult

# Rubrics — task-specific criteria passed to the critique prompts
_RUBRICS: dict[str, list[str]] = {
    "problem_generation": [
        "Mathematical correctness: does the stated answer actually solve the problem?",
        "Pedagogical correctness: does the problem require only methods taught in or before this unit?",
        "Ambiguity: is the problem statement unambiguous with exactly one correct answer?",
        "Difficulty calibration: do conceptual and computational axes match the requested levels?",
        "Distractor quality: does each distractor correspond to a realistic, named mistake?",
        "Hint ladder quality: does each hint nudge without revealing? Is the progression smooth?",
    ],
    "solution_explanation": [
        "Accuracy: every step is mathematically correct.",
        "Misconception targeting: does it address the specific wrong answer the student gave?",
        "Clarity: would a student at this level understand it without other resources?",
        "Prerequisite connections: does it link back to the relevant prior concept?",
        "Tone: encouraging, not condescending.",
    ],
    "hint_ladder": [
        "No answer leakage in hints 1-3.",
        "Smooth difficulty progression across all 4 hints.",
        "Each hint is independently useful (not dependent on having read the previous hint).",
    ],
}


async def run(request: DebateRequest) -> DebateResult:
    """
    Run a multi-agent debate for the given task.

    Args:
        request: DebateRequest with task, context, and rounds.

    Returns:
        DebateResult with winner='A'|'B'|'neither' and the winning output.

    Raises:
        ValueError: if rounds > 3.
    """
    if request.rounds > 3:
        raise ValueError(f"rounds must be <= 3, got {request.rounds}")

    rubric = _RUBRICS.get(request.task, [])

    # Round 0: independent generation (both instances in parallel)
    output_a, output_b = await asyncio.gather(
        _generate_instance(request.task, request.context),
        _generate_instance(request.task, request.context),
    )

    # Rounds 1..N: critique and revise (both in parallel each round)
    for _round in range(request.rounds):
        critique_a, critique_b = await asyncio.gather(
            _critique(request.task, output_a, output_b, rubric),
            _critique(request.task, output_b, output_a, rubric),
        )
        output_a = critique_a.get("revised", output_a)
        output_b = critique_b.get("revised", output_b)

    # Final: judge selects winner
    winner_data = await _judge(request.task, output_a, output_b, rubric)
    winner = winner_data.get("winner", "neither")

    tokens = winner_data.get("tokens_used", 0)
    _log_debate(request.task, request.rounds, winner, winner_data.get("reason", ""), tokens)

    if winner == "A":
        return DebateResult(winner="A", output=output_a, reason=winner_data.get("reason", ""), tokens_used=tokens)
    if winner == "B":
        return DebateResult(winner="B", output=output_b, reason=winner_data.get("reason", ""), tokens_used=tokens)
    return DebateResult(
        winner="neither",
        output=None,
        reason=winner_data.get("reason", "Both outputs failed quality check"),
        tokens_used=tokens,
    )


async def _generate_instance(task: str, context: dict) -> dict:
    """Generate one output for the debate task."""
    if task == "problem_generation":
        from agents.generator import generate
        from agents.schemas import GeneratorInput
        inp = GeneratorInput(**context)
        prob = await generate(inp)
        return prob.model_dump()

    if task == "solution_explanation":
        from agents.solution_explainer import _generate_raw_explanation
        return await _generate_raw_explanation(context)

    if task == "hint_ladder":
        from agents.hint_scaffolder import _generate_raw_ladder
        return await _generate_raw_ladder(context)

    raise ValueError(f"Unknown debate task: {task}")


async def _critique(
    task: str,
    my_output: dict,
    other_output: dict,
    rubric: list[str],
) -> dict:
    """
    Ask Claude to critique other_output against the rubric, then revise my_output.
    Returns {"critique": str, "revised": dict}.
    """
    from llm_anthropic_client import _call_with_backoff

    rubric_text = "\n".join(f"- {r}" for r in rubric)
    prompt = f"""You are reviewing a math education output. Critique the following output
against these quality criteria, then revise the YOUR output accordingly.

CRITERIA:
{rubric_text}

OUTPUT TO CRITIQUE:
{json.dumps(other_output, indent=2)}

YOUR CURRENT OUTPUT (revise this based on what you learned from critiquing above):
{json.dumps(my_output, indent=2)}

Respond with JSON:
{{"critique": "...", "revised": {{...same structure as your current output...}}}}"""

    raw = await _call_with_backoff(
        messages=[{"role": "user", "content": prompt}],
        system="You are an expert math teacher reviewing educational content. Respond only with valid JSON.",
        max_tokens=2000,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"critique": "Parse error", "revised": my_output}


async def _judge(task: str, output_a: dict, output_b: dict, rubric: list[str]) -> dict:
    """
    Ask Claude to pick the winner between output_a and output_b.
    Returns {"winner": "A"|"B"|"neither", "reason": str, "tokens_used": int}.
    """
    from llm_anthropic_client import _call_with_backoff

    rubric_text = "\n".join(f"- {r}" for r in rubric)
    prompt = f"""You are judging two math education outputs. Pick the higher quality one.

QUALITY CRITERIA:
{rubric_text}

OUTPUT A:
{json.dumps(output_a, indent=2)}

OUTPUT B:
{json.dumps(output_b, indent=2)}

Respond with JSON:
{{"winner": "A" or "B" or "neither", "reason": "brief explanation"}}
Use "neither" only if BOTH outputs are seriously flawed and should be discarded."""

    raw = await _call_with_backoff(
        messages=[{"role": "user", "content": prompt}],
        system="You are an expert judge of math education content. Respond only with valid JSON.",
        max_tokens=300,
    )
    try:
        data = json.loads(raw)
        data.setdefault("tokens_used", 0)
        return data
    except json.JSONDecodeError:
        return {"winner": "A", "reason": "Judge parse error — defaulting to A", "tokens_used": 0}


def _log_debate(task: str, rounds: int, winner: str, reason: str, tokens: int) -> None:
    """Log every debate round as structured JSON for quality auditing."""
    import sys
    record = {
        "ts": time.time(),
        "task": task,
        "rounds": rounds,
        "winner": winner,
        "reason": reason,
        "tokens_used": tokens,
    }
    print(json.dumps(record), file=sys.stdout, flush=True)
