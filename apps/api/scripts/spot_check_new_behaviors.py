"""One-off spot check: returning-student opener + voice repair protocol."""
from __future__ import annotations

import asyncio
import io
import json
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from audit_scenarios import PROBLEM, make_session, run_turn  # noqa: E402
from agents.tutor_engine import get_opening_message  # noqa: E402


async def main():
    out = {}

    # Returning student opener — must not re-introduce the tutor
    out["returning_opener"] = await get_opening_message(
        session_why="test_prep",
        uploaded_problem_count=0,
        class_name="Algebra 2",
        topic_names=["Systems of Equations"],
        tutor_name="Josh",
        problem_statement=PROBLEM.statement,
        is_returning=True,
    )

    # Repair protocol — student asks to repeat after a complex spoken expression
    s = make_session(conversation=[
        {"role": "tutor", "content": "Can you set up the augmented matrix for this system?"},
        {"role": "student", "content": "how do I eliminate x?"},
        {"role": "tutor", "content": "Replace row 2 with row 2 minus $\\tfrac{1}{2}$ times row 1, so the new row 2 is $[0, -\\tfrac{5}{2}, -\\tfrac{5}{2}]$. What does that give you for $y$?"},
    ])
    out["repair_level_1"] = await run_turn(s, "wait, what did you say?")

    # Second repeat request — should escalate to a piece-by-piece walk
    s.conversation.append({"role": "tutor", "content": out["repair_level_1"]["tutor_reply"]})
    out["repair_level_2"] = await run_turn(s, "sorry, say that again?")

    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
