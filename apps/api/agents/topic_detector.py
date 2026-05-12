"""
Topic detector agent — identifies the math topic from a free-form student message.

Called during discovery mode when a student starts a session without selecting a topic.
Returns a structured result with the identified topic, mode, and confidence.
"""
from __future__ import annotations

import json
from typing import Optional

from agents.schemas import GeneratorInput


DETECTION_SYSTEM_PROMPT = """\
You are helping identify what math topic a student needs help with.

Given the student's message and the available topic list, identify:
1. The most likely topic from the list (use topic_id exactly as given)
2. The session mode: "concept" (learning new material), "homework" (help with a specific problem), or "practice" (wants to practice problems)
3. Your confidence from 0.0 to 1.0

Return ONLY valid JSON in this exact format (no markdown, no explanation):
{
  "topic_id": "the-exact-topic-id-or-null",
  "topic_name": "Human-readable topic name",
  "mode": "concept|homework|practice",
  "confidence": 0.85,
  "confirmation_message": "It sounds like you're working on [topic]. Is that right?"
}

If you cannot identify a topic with confidence >= 0.5, set topic_id to null and confidence below 0.5.
Keep confirmation_message conversational and brief (1 sentence ending with a question mark).
"""


async def detect_topic(
    student_message: str,
    conversation_history: list[dict],
    topic_registry: dict,
) -> dict:
    """
    Detect the math topic from the student's opening message.

    Returns a dict with keys: topic_id, topic_name, mode, confidence, confirmation_message.
    topic_id is None if detection fails.
    """
    from anthropic import AsyncAnthropic
    from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL

    if not ANTHROPIC_API_KEY:
        return _fallback_result()

    # Build a compact topic list for the prompt (topic_id → name)
    topic_lines = "\n".join(
        f"  {tid}: {meta.topic_name} ({meta.course_name})"
        for tid, meta in list(topic_registry.items())[:200]  # cap at 200 for token budget
    )

    conversation_text = ""
    for msg in conversation_history[-4:]:  # last 4 turns
        role = "Student" if msg.get("role") == "student" else "Tutor"
        conversation_text += f"{role}: {msg.get('content', '')}\n"
    conversation_text += f"Student: {student_message}"

    user_message = f"""Available topics:
{topic_lines}

Conversation:
{conversation_text}

Identify the topic."""

    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    try:
        response = await client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=300,
            system=DETECTION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        text = response.content[0].text.strip()
        result = json.loads(text)

        # Validate required fields
        result.setdefault("confidence", 0.0)
        result.setdefault("topic_id", None)
        result.setdefault("mode", "practice")
        result.setdefault("confirmation_message", "Is that what you're working on?")
        result.setdefault("topic_name", "")

        # Validate topic_id actually exists in registry
        if result["topic_id"] and result["topic_id"] not in topic_registry:
            result["topic_id"] = None
            result["confidence"] = 0.0

        return result
    except Exception:
        return _fallback_result()


def build_picklist(topic_registry: dict, query: str, max_items: int = 6) -> list[dict]:
    """
    Return a short list of candidate topics when detection confidence is low.
    Simple substring match on topic name.
    """
    query_lower = query.lower()
    matches = []
    for tid, meta in topic_registry.items():
        if query_lower in meta.topic_name.lower() or query_lower in meta.course_name.lower():
            matches.append({
                "topic_id": tid,
                "topic_name": meta.topic_name,
                "course_name": meta.course_name,
            })
        if len(matches) >= max_items:
            break
    return matches


def _fallback_result() -> dict:
    return {
        "topic_id": None,
        "topic_name": "",
        "mode": "practice",
        "confidence": 0.0,
        "confirmation_message": "I'm not sure what topic you're working on. Could you give me more details?",
    }
