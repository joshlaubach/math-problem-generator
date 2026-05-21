"""
Tutor engine — phase-aware brain for general tutor sessions (Phases 4-5).

Wraps the EDGE phase machinery, Socratic responder, and escalation logic.
Stateless per-call; session state is passed in by ws_router and mutated in place.

Key design:
- Guide / Enable phases → Socratic (never reveals answer)
- Explain / Demonstrate phases (lesson mode) → teaches the concept + worked example
- Auto-escalation after ESCALATION_THRESHOLD consecutive non-progress turns
- Exam mode detection after READINESS_THRESHOLD consecutive clean solves
"""
from __future__ import annotations

import logging
from typing import Optional, Any

from agents.schemas import GeneratedProblem

logger = logging.getLogger(__name__)

# ── Thresholds ─────────────────────────────────────────────────────────────────

# Consecutive non-progress turns before auto-escalating to lesson mode
ESCALATION_THRESHOLD = 2

# Consecutive hints-free, wrong-attempt-free solves before proposing exam mode
READINESS_THRESHOLD = 3


# ── Opening message ────────────────────────────────────────────────────────────

async def get_opening_message(
    session_why: Optional[str],
    uploaded_problem_count: int,
    class_name: str,
    topic_names: list[str],
    tutor_name: str = "Josh",
) -> str:
    """
    Generate the opening message based on intake form data.
    Falls back to deterministic strings if no API key is set.
    """
    topics_str = ", ".join(topic_names[:3]) if topic_names else class_name or "math"

    if uploaded_problem_count > 0:
        return (
            f"Hey, I'm {tutor_name}! I can see you uploaded "
            f"{uploaded_problem_count} problem{'s' if uploaded_problem_count != 1 else ''}. "
            "Which one are you most worried about, or should we start from the top?"
        )

    why_openers: dict[str, str] = {
        "learn_concept": (
            f"Hi! I'm {tutor_name}, your math tutor. You mentioned wanting to learn something "
            f"new — let's dive in. What aspect of {topics_str} would you like to tackle first?"
        ),
        "homework": (
            f"Hey, I'm {tutor_name}! Let's work through your assignment together. "
            f"What problem are you stuck on?"
        ),
        "test_prep": (
            f"Hi! I'm {tutor_name}. Let's get you ready for that test. "
            f"We'll work through {topics_str} — want to start with a problem "
            "or review the concepts first?"
        ),
        "grade_improvement": (
            f"Hey, I'm {tutor_name}! Let's turn things around. "
            f"We'll go through {topics_str} systematically. "
            "Want to start with the concept basics or jump straight into a problem?"
        ),
        "get_ahead": (
            f"Hi! I'm {tutor_name}. Getting ahead — I love it. "
            f"Let's preview {topics_str}. "
            "Quick concept overview first, or dive right into a problem?"
        ),
    }

    return why_openers.get(
        session_why or "",
        f"Hi! I'm {tutor_name}, your math tutor. "
        f"I see we're working on {topics_str} today. What would you like to start with?",
    )


# ── Socratic / lesson responses ────────────────────────────────────────────────

async def generate_tutor_response(
    session: Any,
    student_message: str,
    force_lesson: bool = False,
) -> tuple[str, bool]:
    """
    Generate the next tutor response.

    Returns:
        (response_text, entered_lesson_mode)
    """
    from agents.socratic import respond as socratic_respond

    problem: Optional[GeneratedProblem] = session.problem
    if problem is None:
        return (
            "Let me get a problem ready for you. What topic would you like to practice?",
            False,
        )

    should_teach = force_lesson or session.consecutive_no_progress >= ESCALATION_THRESHOLD

    if should_teach:
        session.consecutive_no_progress = 0
        response = await _lesson_response(session, student_message)
        return response, True

    # Socratic mode
    try:
        reply = await socratic_respond(
            problem_statement=problem.statement,
            conversation=session.conversation[:-1],  # exclude just-appended turn
            student_message=student_message,
            hint_ladder=problem.hint_ladder,
            hint_level=session.hint_level,
            wrong_attempts=session.attempts,
            tutor_name=session.tutor_name,
            session_summary=session.session_summary,
            topic_id=session.topic_id,
            history_briefing=session.history_briefing,
        )
    except Exception:
        reply = "Interesting approach! What's your reasoning for that step?"

    return reply, False


async def _lesson_response(session: Any, student_message: str) -> str:
    """
    Generate a lesson-mode response: explain concept, show a worked example,
    then give a simpler fresh problem to try.
    """
    from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, DATA_DIR
    import json as _json

    problem: Optional[GeneratedProblem] = session.problem

    # Try to pull worked_example from the cached lesson file
    worked_example_text = ""
    if session.topic_id:
        lesson_path = DATA_DIR / "topic_lessons" / f"{session.topic_id}.json"
        if lesson_path.exists():
            try:
                lesson = _json.loads(lesson_path.read_text())
                steps = lesson.get("worked_example", [])
                parts = []
                for i, step in enumerate(steps[:4], 1):
                    expr = step.get("expression_latex", "")
                    desc = step.get("description_latex", "")
                    if desc or expr:
                        sep = " — " if desc and expr else ""
                        parts.append(f"Step {i}: {desc}{sep}{expr}")
                worked_example_text = "\n".join(parts)
            except Exception:
                pass

    if not ANTHROPIC_API_KEY:
        stmt = problem.statement if problem else "this problem"
        return (
            f"Let me walk you through this step by step.\n\n"
            f"For: {stmt}\n\n"
            f"The key idea is to break it down carefully. "
            f"Now try applying this approach — what's your first step?"
        )

    from anthropic import AsyncAnthropic
    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    system = (
        f"You are {session.tutor_name}, a math tutor in lesson/explain mode. "
        "The student is struggling. Walk through the concept clearly, show a worked example, "
        "then end with: 'Try this: [simpler problem statement]'\n"
        "Keep it to 3-4 short paragraphs. Be warm and encouraging."
    )
    stmt = problem.statement if problem else "the current topic"
    user_content = (
        f"Student's problem: {stmt}\n"
        f"Course: {session.class_name}\n"
        + (f"Lesson worked example:\n{worked_example_text}\n\n" if worked_example_text else "")
        + f"Student said: {student_message}\n\n"
        "Explain the concept, show the approach, then give a simpler practice problem."
    )

    try:
        resp = await client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=600,
            system=system,
            messages=[{"role": "user", "content": user_content}],
        )
        return resp.content[0].text.strip()
    except Exception:
        stmt = problem.statement if problem else "the current topic"
        return (
            f"Let me break this down. "
            f"For '{stmt}', start by identifying what the problem is asking. "
            "What information do you have, and what are you solving for?"
        )


# ── Pacing signal ──────────────────────────────────────────────────────────────

async def handle_going_too_fast(session: Any) -> str:
    """
    Student signalled the pace is too fast. Revisit the current concept more slowly.
    Returns a tutor message to send.
    """
    from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL

    problem: Optional[GeneratedProblem] = session.problem
    stmt = problem.statement if problem else "this concept"

    if not ANTHROPIC_API_KEY:
        return (
            "No problem — let's slow down. "
            f"Going back to basics on this one: {stmt}. "
            "Tell me what part feels unclear and we'll work through it together."
        )

    from anthropic import AsyncAnthropic
    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    try:
        resp = await client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=250,
            messages=[{
                "role": "user",
                "content": (
                    f"A math student said 'going too fast'. "
                    f"Current problem: {stmt}\n"
                    f"Course: {session.class_name}\n"
                    f"Tutor name: {session.tutor_name}\n\n"
                    "Respond warmly, slow down the pace, and revisit the current concept "
                    "with a simpler intermediate step. End with a question. Max 3 sentences."
                ),
            }],
        )
        return resp.content[0].text.strip()
    except Exception:
        return (
            "Of course — let's back up. "
            "Walk me through what you've understood so far and we'll fill the gaps together."
        )


# ── Problem queue ──────────────────────────────────────────────────────────────

async def build_problem_queue(session: Any) -> list[GeneratedProblem]:
    """
    Generate the initial problem queue for the session.

    If uploaded_problems exist, the queue is empty (uploaded problems are used directly).
    Otherwise, generates up to 2 problems per selected topic.
    Freeform topics generate 1 problem each via Mode B (LLM-only).

    Returns a list of GeneratedProblem objects.
    """
    # Uploaded problems override the generated queue
    if session.uploaded_problems:
        return []

    from agents.generator import generate as generate_problem
    from agents.schemas import GeneratorInput
    from topic_registry import TOPIC_REGISTRY

    problems: list[GeneratedProblem] = []

    # In-curriculum topics
    for topic_id in session.topic_ids[:6]:
        meta = TOPIC_REGISTRY.get(topic_id)
        if meta is None:
            continue
        conceptual_diff = max(1, min(5, round(session.difficulty * 5 / 6)))
        gen_input = GeneratorInput(
            topic=meta.topic_name,
            course=meta.course_name,
            unit=meta.unit_name,
            conceptual_diff=conceptual_diff,
            computational_diff=conceptual_diff,
            calc_tier="none",
        )
        try:
            p = await generate_problem(gen_input)
            problems.append(p)
        except Exception as exc:
            logger.warning("Problem gen failed for %s: %s", topic_id, exc)

        # Second problem (harder) for queue depth
        if len(problems) < 4:
            try:
                gen2 = GeneratorInput(
                    topic=meta.topic_name,
                    course=meta.course_name,
                    unit=meta.unit_name,
                    conceptual_diff=min(5, conceptual_diff + 1),
                    computational_diff=min(5, conceptual_diff + 1),
                    calc_tier="none",
                )
                p2 = await generate_problem(gen2)
                problems.append(p2)
            except Exception:
                pass

    # Freeform topics (Mode B — LLM-only)
    for freeform in session.freeform_topics[:2]:
        try:
            gen_input = GeneratorInput(
                topic=freeform,
                course=session.class_name or "Mathematics",
                unit=session.notes or "General",
                conceptual_diff=max(1, min(5, round(session.difficulty * 5 / 6))),
                computational_diff=max(1, min(5, round(session.difficulty * 5 / 6))),
                calc_tier="none",
            )
            p = await generate_problem(gen_input)
            problems.append(p)
        except Exception as exc:
            logger.warning("Freeform problem gen failed for '%s': %s", freeform, exc)

    return problems


# ── Exam mode detection ────────────────────────────────────────────────────────

def check_exam_readiness(session: Any) -> bool:
    """
    Returns True if the student has shown consistent readiness for exam mode:
    solved the last READINESS_THRESHOLD problems with no hints and no wrong attempts.

    This is a heuristic based on session_summary + current problem state.
    """
    if session.current_index < READINESS_THRESHOLD:
        return False

    # Count clean solves from recent session_summary bullets
    clean_count = 0
    for bullet in reversed(session.session_summary[-READINESS_THRESHOLD:]):
        bullet_str = str(bullet).lower()
        # A clean solve has no mention of hints or multiple attempts
        if ("solved" in bullet_str or "correct" in bullet_str) and "hint" not in bullet_str:
            clean_count += 1
        else:
            break  # require consecutive

    return clean_count >= READINESS_THRESHOLD


async def get_exam_mode_proposal(session: Any) -> str:
    """
    Return the tutor message proposing to enter exam mode.
    """
    tutor = session.tutor_name or "Josh"
    return (
        f"You've been crushing these — {clean_count_desc(session.current_index)} solved cleanly. "
        f"I think you're ready to be tested without any support. "
        "Want to try **exam mode**? I'll clear the board and give you problems without hints. "
        "Say yes when you're ready, or just keep going as normal."
    )


def clean_count_desc(n: int) -> str:
    return f"{n} problem{'s' if n != 1 else ''}"


async def get_exam_start_message(session: Any) -> str:
    """Return the message that plays when exam mode begins."""
    return (
        "Exam mode — let's see what you've got. "
        "Board cleared. No hints, no help. Just you and the problems. Good luck!"
    )
