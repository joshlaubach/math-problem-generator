"""
RL Event Logger — append-only JSONL log for Socratic tutor sessions.

Reward formula (computed at session_end):
    correct  → max(0.0, 1.0 - 0.1 * hints_used)
    incorrect or timeout → 0.0

Bandit phase: log everything. No learning yet.
Next phases: contextual bandits (100 interactions), DQN (1 000), PPO (10 000).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

RL_LOG_PATH = Path("data/rl_events.jsonl")

EventType = Literal[
    "answer_attempt",
    "hint_request",
    "student_question",
    "correct",
    "session_end",
    "timeout",
    "calculator_send",
]


def _ensure_data_dir() -> None:
    RL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def log_event(
    session_id: str,
    user_id: str,
    topic_id: str,
    difficulty: int,
    event_type: EventType,
    payload: dict[str, Any],
    reward: Optional[float] = None,
) -> None:
    """Append one event record to data/rl_events.jsonl."""
    _ensure_data_dir()
    record = {
        "session_id": session_id,
        "user_id": user_id,
        "topic_id": topic_id,
        "difficulty": difficulty,
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
        "reward": reward,
    }
    with RL_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def compute_reward(is_correct: bool, hints_used: int) -> float:
    if not is_correct:
        return 0.0
    return max(0.0, 1.0 - 0.1 * hints_used)
