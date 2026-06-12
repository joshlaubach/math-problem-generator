"""Live tutoring-quality audit: drives the real tutor engine through 6 scenarios.

Run from apps/api:  python scripts/audit_scenarios.py
Writes results to scripts/audit_scenario_results.json
"""
from __future__ import annotations

import asyncio
import json
import sys
import pathlib
from types import SimpleNamespace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from agents.schemas import GeneratedProblem, WorkedStep, Distractor  # noqa: E402
from agents.tutor_engine import generate_tutor_response, get_opening_message  # noqa: E402
from agents.tutor_guide import select_snippets, should_inject_deep  # noqa: E402

PROBLEM = GeneratedProblem(
    statement=(
        "Solve the system using an augmented matrix: $2x + 3y = 7$ and $x - y = 1$."
    ),
    answer="$x = 2, y = 1$",
    worked_steps=[
        WorkedStep(step="Write the augmented matrix $[A \\mid b]$",
                   explanation="Each equation's coefficients form one row: $[2, 3 \\mid 7]$ and $[1, -1 \\mid 1]$."),
        WorkedStep(step="Row reduce", explanation="$R_2 \\to R_2 - \\tfrac{1}{2}R_1$ gives $-\\tfrac{5}{2}y = -\\tfrac{5}{2}$."),
        WorkedStep(step="Back substitute", explanation="$y = 1$, then $x = 1 + y = 2$."),
    ],
    hint_ladder=[
        "What goes in each row of the augmented matrix?",
        "Each equation becomes one row: coefficients of x, then y, then the constant.",
        "Eliminate x from row 2 by subtracting half of row 1.",
        "After elimination you get $-\\tfrac{5}{2}y = -\\tfrac{5}{2}$. Solve for y, then back-substitute.",
    ],
    distractors=[
        Distractor(answer="$x = 1, y = 2$", mistake="swapped solution values"),
        Distractor(answer="$x = 5, y = -1$", mistake="sign error in elimination"),
        Distractor(answer="$x = 2, y = -1$", mistake="dropped negative when back-substituting"),
    ],
)


def make_session(**overrides):
    s = SimpleNamespace(
        problem=PROBLEM,
        conversation=[],
        attempts=[],
        hint_level=0,
        tutor_name="Josh",
        session_summary=[],
        topic_id="alg2_systems_matrices",
        topic_ids=["alg2_systems_matrices"],
        history_briefing="",
        consecutive_no_progress=0,
        class_name="Algebra 2",
        is_first_ever_session=False,
        current_index=0,
        exam_mode=False,
    )
    for k, v in overrides.items():
        setattr(s, k, v)
    return s


async def run_turn(session, student_message, force_lesson=False):
    """Mirror ws_router: append student turn, then call the engine."""
    session.conversation.append({"role": "student", "content": student_message})
    snippets = select_snippets(student_message, session)
    deep = should_inject_deep(session, snippets)
    reply, entered_lesson = await generate_tutor_response(
        session, student_message, force_lesson=force_lesson
    )
    return {
        "student_message": student_message,
        "snippets_fired": snippets,
        "deep_guide_injected": deep,
        "entered_lesson_mode": entered_lesson,
        "tutor_reply": reply,
    }


async def main():
    results = {}

    # ── Scenario A: visible-problem opener ────────────────────────────────────
    results["A_visible_problem_opener"] = {
        "opening_message": await get_opening_message(
            session_why="homework",
            uploaded_problem_count=0,
            class_name="Algebra 2",
            topic_names=["Systems of Equations (H)"],
            tutor_name="Josh",
            problem_statement=PROBLEM.statement,
        )
    }

    # ── Scenario B: "Yes, I can" trap ─────────────────────────────────────────
    sb = make_session(conversation=[
        {"role": "tutor", "content": "So you've got a system of two equations to solve with matrices. What's your instinct on where to start?"},
        {"role": "student", "content": "I think I need a matrix?"},
        {"role": "tutor", "content": "Right, that's the tool here. Can you set up the augmented matrix for this system?"},
    ])
    results["B_yes_i_can"] = await run_turn(sb, "Yes, I can.")

    # ── Scenario C: wrong answer (rows/columns swapped) ───────────────────────
    sc = make_session(conversation=[
        {"role": "tutor", "content": "Can you set up the augmented matrix for this system?"},
    ])
    results["C_wrong_answer"] = await run_turn(
        sc,
        "I set up the coefficient matrix as $\\begin{pmatrix} 2 & 1 \\\\ 3 & -1 \\end{pmatrix}$",
    )

    # ── Scenario D: voice-transcript message with partial approach ────────────
    sd = make_session(conversation=[
        {"role": "tutor", "content": "So you've got a system of two equations. What's your instinct on where to start?"},
    ])
    results["D_voice_partial_approach"] = await run_turn(
        sd,
        "ok so um i think i can multiply the second equation by 2 and then subtract it from the first one to get rid of the x terms",
    )

    # ── Scenario E: lesson-mode escalation after repeated failure ─────────────
    se = make_session(
        consecutive_no_progress=2,
        attempts=["x = 1, y = 2", "x = 5, y = -1"],
        conversation=[
            {"role": "tutor", "content": "Which row operation eliminates x from the second row?"},
            {"role": "student", "content": "x = 1, y = 2?"},
            {"role": "tutor", "content": "Not quite. Walk me through how you got that, what did you do to row 2?"},
            {"role": "student", "content": "ok then x = 5, y = -1"},
            {"role": "tutor", "content": "I see where you're going, but something flipped a sign. What is $-\\tfrac{1}{2}$ times row 1?"},
        ],
    )
    results["E_lesson_escalation"] = await run_turn(se, "I still don't get it, I'm lost")

    # ── Scenario F: confidence signal after correct work ──────────────────────
    sf = make_session(conversation=[
        {"role": "tutor", "content": "Can you set up the augmented matrix for this system?"},
        {"role": "student", "content": "$[[2, 3, 7], [1, -1, 1]]$"},
        {"role": "tutor", "content": "That's it. Now reduce it, what do you get for $y$?"},
        {"role": "student", "content": "y = 1"},
        {"role": "tutor", "content": "Correct. Subtracting half of row 1 from row 2 gives $-\\tfrac{5}{2}y = -\\tfrac{5}{2}$, so $y = 1$ and then $x = 2$."},
    ])
    results["F_got_it"] = await run_turn(sf, "got it")

    out = pathlib.Path(__file__).parent / "audit_scenario_results.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    asyncio.run(main())
