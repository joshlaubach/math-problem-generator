"""
Tutor engine — phase-aware brain for general tutor sessions (Phases 4-5).

Wraps the EDGE phase machinery, Socratic responder, and escalation logic.
Stateless per-call; session state is passed in by ws_router and mutated in place.

Key design:
- Guide / Enable phases → Socratic (never reveals answer)
- Explain / Demonstrate phases (lesson mode) → teaches the concept + worked example
- Auto-escalation after ESCALATION_THRESHOLD consecutive non-progress turns
- Exam mode detection after READINESS_THRESHOLD consecutive clean solves

Prompt assembly:
- All LLM calls route through agents.prompt_assembler.build_system_prompt()
- Snippet routing and deep-guide gating are computed here in generate_tutor_response
  and passed down to socratic.respond and _lesson_response
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

import re as _re

def _clean_topic_names(names: list[str]) -> list[str]:
    """Strip honors suffixes like '(H)' and '(H+)' from topic display names."""
    return [_re.sub(r'\s*\(H\+?\)\s*$', '', n).strip() for n in names]


def _naturalize(text: str) -> str:
    """Enforce OUTPUT_CONSTRAINTS the model sometimes ignores: no em-dashes."""
    return _re.sub(r'\s*—\s*', ', ', text)


async def get_opening_message(
    session_why: Optional[str],
    uploaded_problem_count: int,
    class_name: str,
    topic_names: list[str],
    tutor_name: str = "Josh",
    problem_statement: Optional[str] = None,
    is_returning: bool = False,
) -> str:
    """Generate a natural opening message via LLM, falling back to a simple string."""
    from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
    from agents.prompt_assembler import build_system_prompt

    clean_topics = _clean_topic_names(topic_names)

    if uploaded_problem_count > 0:
        context = f"The student uploaded {uploaded_problem_count} problem{'s' if uploaded_problem_count != 1 else ''}."
        if problem_statement:
            context += f" First problem: {problem_statement}"
    elif problem_statement:
        context = f"Problem statement: {problem_statement}"
    elif clean_topics:
        short = clean_topics[:2]
        context = f"Topics: {', '.join(short)}."
    else:
        context = f"Subject: {class_name or 'math'}."

    why_context = {
        "learn_concept": "They want to understand a new concept.",
        "homework":       "They are stuck on homework.",
        "test_prep":      "They have a test coming up.",
        "grade_improvement": "They want to improve their grade.",
        "get_ahead":      "They want to get ahead of the class.",
    }.get(session_why or "", "")

    if not ANTHROPIC_API_KEY:
        # Deterministic fallback — used in tests; must contain "problem" for uploads
        greeting = "Welcome back!" if is_returning else f"Hey, I'm {tutor_name}!"
        if uploaded_problem_count > 0:
            return (
                f"{greeting} I can see you uploaded "
                f"{uploaded_problem_count} problem{'s' if uploaded_problem_count != 1 else ''}. "
                "Which one are you most worried about, or should we start from the top?"
            )
        topic = clean_topics[0] if clean_topics else class_name or "math"
        if is_returning:
            return f"Welcome back! Ready to pick up {topic} where we left off?"
        return f"Hey, I'm {tutor_name}! Good to meet you. What are we working on in {topic} today?"

    returning_context = (
        " This is a returning student; greet them like someone you already know, "
        "do not introduce yourself."
        if is_returning else ""
    )
    session_context = f"Tutor name: {tutor_name}. {context} {why_context}{returning_context}".strip()
    system_prompt = build_system_prompt(
        role="OPENING",
        context=session_context,
        cacheable=True,
    )

    try:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        kwargs: dict = {
            "model": ANTHROPIC_MODEL,
            "max_tokens": 80,
            "messages": [{"role": "user", "content": "Generate the opening message now."}],
        }
        if isinstance(system_prompt, list):
            kwargs["system"] = system_prompt
            kwargs["extra_headers"] = {"anthropic-beta": "prompt-caching-2024-07-31"}
        else:
            kwargs["system"] = system_prompt
        msg = await client.messages.create(**kwargs)
        return _naturalize(msg.content[0].text.strip())
    except Exception:
        if is_returning:
            return "Welcome back! What are we working on today?"
        return f"Hey, I'm {tutor_name}! Good to meet you. What are we working on today?"


# ── Socratic / lesson responses ────────────────────────────────────────────────

# Rotating fallbacks for LLM outages — never the same canned line twice in a row
_SOCRATIC_FALLBACKS = [
    "Walk me through your last step, what were you thinking there?",
    "Tell me what you tried just now, where did it take you?",
    "Which part of this feels solid so far, and which part feels shaky?",
    "Take your best guess at the next step, what would you try?",
]


async def generate_tutor_response(
    session: Any,
    student_message: str,
    force_lesson: bool = False,
) -> tuple[str, bool]:
    """
    Generate the next tutor response.

    Computes snippet routing and deep-guide gating here, then passes results
    to socratic.respond (or _lesson_response) so all four gate conditions
    (consecutive_no_progress, anxiety, repeated wrong attempts, first session)
    are evaluated regardless of which path is taken.

    Returns:
        (response_text, entered_lesson_mode)
    """
    from agents.socratic import respond as socratic_respond
    from agents.tutor_guide import (
        select_snippets,
        should_inject_deep,
        select_topic_guidance,
    )

    problem: Optional[GeneratedProblem] = session.problem
    if problem is None:
        return (
            "Let me get a problem ready for you. What topic would you like to practice?",
            False,
        )

    # Compute routing signals before branching (needed by both paths)
    snippets = select_snippets(student_message, session)
    deep = should_inject_deep(session, snippets)
    topic_guidance = select_topic_guidance(session)

    should_teach = force_lesson or session.consecutive_no_progress >= ESCALATION_THRESHOLD

    if should_teach:
        session.consecutive_no_progress = 0
        response = await _lesson_response(
            session, student_message,
            snippets=snippets, topic_guidance=topic_guidance, deep=deep,
        )
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
            snippets=snippets,
            topic_guidance=topic_guidance,
            deep=deep,
        )
        reply = _naturalize(reply)
    except Exception:
        reply = _SOCRATIC_FALLBACKS[len(session.conversation) % len(_SOCRATIC_FALLBACKS)]

    return reply, False


async def _lesson_response(
    session: Any,
    student_message: str,
    snippets: Optional[list[str]] = None,
    topic_guidance: Optional[str] = None,
    deep: bool = False,
) -> str:
    """
    Generate a lesson-mode response: explain concept, show a worked example,
    then give a simpler fresh problem to try.
    """
    from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
    from agents.prompt_assembler import build_system_prompt

    problem: Optional[GeneratedProblem] = session.problem

    # Try to pull worked_example from the cached lesson (DB in prod, file in dev)
    worked_example_text = ""
    if session.topic_id:
        try:
            from agents.lesson_store import get_lesson
            lesson = get_lesson(session.topic_id)
            steps = (lesson or {}).get("worked_example", [])
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

    stmt = problem.statement if problem else "the current topic"

    # Recent turns let the model scope the lesson to the actual stuck point
    recent_turns = "\n".join(
        f"{t['role']}: {t['content']}" for t in session.conversation[-6:]
    )

    context = (
        f"You are {session.tutor_name}. "
        f"Student's problem (do NOT solve this one or reveal its answer): {stmt}\n"
        f"Course: {session.class_name}\n"
        + (f"Lesson worked example (use this as your parallel demonstration):\n{worked_example_text}\n"
           if worked_example_text else "")
        + (f"Recent conversation:\n{recent_turns}\n" if recent_turns else "")
        + f"Student said: {student_message}\n\n"
        "Teach the concept the student is stuck on, demonstrating on a parallel example "
        "with different numbers, never on the student's own problem. Then give a simpler "
        "practice problem. Never state or imply the answer to the student's problem."
    )

    system_prompt = build_system_prompt(
        role="LESSON",
        context=context,
        snippets=snippets,
        topic_guidance=topic_guidance,
        deep=deep,
        cacheable=True,
    )

    try:
        kwargs: dict = {
            "model": ANTHROPIC_MODEL,
            "max_tokens": 800,
            "messages": [{"role": "user", "content": "Generate the lesson response now."}],
        }
        if isinstance(system_prompt, list):
            kwargs["system"] = system_prompt
            kwargs["extra_headers"] = {"anthropic-beta": "prompt-caching-2024-07-31"}
        else:
            kwargs["system"] = system_prompt
        resp = await client.messages.create(**kwargs)
        return _naturalize(resp.content[0].text.strip())
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
    from agents.prompt_assembler import build_system_prompt

    problem: Optional[GeneratedProblem] = session.problem
    stmt = problem.statement if problem else "this concept"

    if not ANTHROPIC_API_KEY:
        return (
            "No problem, let's slow down. "
            f"Going back to basics on this one: {stmt}. "
            "Tell me what part feels unclear and we'll work through it together."
        )

    from anthropic import AsyncAnthropic
    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    context = (
        f"You are {session.tutor_name}. "
        f"Current problem: {stmt}\n"
        f"Course: {session.class_name}\n"
        "A math student said they are going too fast. "
        "Respond warmly, slow down the pace, and revisit the current concept "
        "with a simpler intermediate step. End with a question. Max 3 sentences."
    )

    system_prompt = build_system_prompt(
        role="PACING",
        context=context,
        cacheable=True,
    )

    try:
        kwargs: dict = {
            "model": ANTHROPIC_MODEL,
            "max_tokens": 250,
            "messages": [{"role": "user", "content": "Generate the pacing response now."}],
        }
        if isinstance(system_prompt, list):
            kwargs["system"] = system_prompt
            kwargs["extra_headers"] = {"anthropic-beta": "prompt-caching-2024-07-31"}
        else:
            kwargs["system"] = system_prompt
        resp = await client.messages.create(**kwargs)
        return _naturalize(resp.content[0].text.strip())
    except Exception:
        return (
            "Of course, let's back up. "
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
    from progress_store import seed_difficulty
    from problem_bank import fetch_unserved, save_generated

    problems: list[GeneratedProblem] = []

    async def _generate_and_bank(meta, topic_id: str, diff: int) -> Optional[GeneratedProblem]:
        """Mode B generation; persist the result so it's a one-time cost."""
        gen_input = GeneratorInput(
            topic=meta.topic_name,
            course=meta.course_name,
            unit=meta.unit_name,
            conceptual_diff=diff,
            computational_diff=diff,
            calc_tier="none",
        )
        p = await generate_problem(gen_input)
        try:
            p.problem_id = save_generated(
                p,
                topic_id=topic_id,
                course_id=getattr(meta, "course_id", "") or "",
                unit_id=getattr(meta, "unit_id", "") or "",
                conceptual_diff=diff,
                computational_diff=diff,
            )
        except Exception as exc:
            logger.warning("Bank save failed for %s: %s", topic_id, exc)
        return p

    # In-curriculum topics — bank-first (launch decision 2026-06-12): serve
    # unseen cached problems instantly, generate only the shortfall
    for topic_id in session.topic_ids[:6]:
        meta = TOPIC_REGISTRY.get(topic_id)
        if meta is None:
            continue
        # Returning students start where their stored mastery says, not at the
        # intake default (L1/7B difficulty seeding)
        intake_diff = max(1, min(5, round(session.difficulty * 5 / 6)))
        conceptual_diff = seed_difficulty(session.user_id, topic_id, intake_diff)

        banked = fetch_unserved(session.user_id, topic_id, conceptual_diff, limit=2)
        problems.extend(banked)

        shortfall_diffs = [conceptual_diff, min(5, conceptual_diff + 1)][len(banked):]
        for diff in shortfall_diffs:
            if len(problems) >= 4 and diff != conceptual_diff:
                break  # harder spare only while the queue is shallow
            try:
                p = await _generate_and_bank(meta, topic_id, diff)
                if p is not None:
                    problems.append(p)
            except Exception as exc:
                logger.warning("Problem gen failed for %s: %s", topic_id, exc)

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

def count_recent_clean_solves(session: Any) -> int:
    """
    Count consecutive clean solves from the end of session_summary.
    A clean solve mentions "solved"/"correct" with no mention of hints.
    """
    clean_count = 0
    for bullet in reversed(session.session_summary):
        bullet_str = str(bullet).lower()
        if ("solved" in bullet_str or "correct" in bullet_str) and "hint" not in bullet_str:
            clean_count += 1
        else:
            break  # require consecutive
    return clean_count


def check_exam_readiness(session: Any) -> bool:
    """
    Returns True if the student has shown consistent readiness for exam mode:
    solved the last READINESS_THRESHOLD problems with no hints and no wrong attempts.

    This is a heuristic based on session_summary + current problem state.
    """
    if session.current_index < READINESS_THRESHOLD:
        return False

    return count_recent_clean_solves(session) >= READINESS_THRESHOLD


async def get_exam_mode_proposal(session: Any) -> str:
    """
    Return the tutor message proposing to enter exam mode.
    """
    clean = count_recent_clean_solves(session) or READINESS_THRESHOLD
    return (
        f"You've been crushing these, {clean_count_desc(clean)} in a row with no help. "
        f"I think you're ready to be tested without any support. "
        "Want to try exam mode? I'll clear the board and give you problems without hints. "
        "Say yes when you're ready, or just keep going as normal."
    )


def clean_count_desc(n: int) -> str:
    return f"{n} problem{'s' if n != 1 else ''}"


async def get_exam_start_message(session: Any) -> str:
    """Return the message that plays when exam mode begins."""
    return (
        "Exam mode, let's see what you've got. "
        "Board cleared. No hints, no help. Just you and the problems. Good luck!"
    )
