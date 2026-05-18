"""
Runtime concept taxonomy loader.

Loads apps/api/data/concept_taxonomy.json once at startup.
Provides helpers for the Socratic agent and misconception tracker.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

_DATA_FILE = Path(__file__).parent / "data" / "concept_taxonomy.json"

# Flat list of all concepts, keyed by id
_ALL_CONCEPTS: dict[str, dict] = {}

# By course
_BY_COURSE: dict[str, list[dict]] = {}


def _load() -> None:
    global _ALL_CONCEPTS, _BY_COURSE
    if not _DATA_FILE.exists():
        return
    data: dict[str, list[dict]] = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    _BY_COURSE = data
    for concepts in data.values():
        for c in concepts:
            _ALL_CONCEPTS[c["id"]] = c


_load()


def labels_for_course(course_id: str) -> list[str]:
    """Return all concept labels for a course (for injection into Socratic prompt)."""
    return [c["label"] for c in _BY_COURSE.get(course_id, [])]


def labels_for_topic(topic_id: str) -> list[str]:
    """Return concept labels relevant to a specific topic."""
    result = []
    for concepts in _BY_COURSE.values():
        for c in concepts:
            if c.get("topic_id") == topic_id:
                result.append(c["label"])
    return result


def concept_by_id(concept_id: str) -> Optional[dict]:
    return _ALL_CONCEPTS.get(concept_id)


def concept_by_label(label: str) -> Optional[dict]:
    """Find a concept by its normalised label (case-insensitive)."""
    label_lower = label.lower()
    for c in _ALL_CONCEPTS.values():
        if c["label"].lower() == label_lower:
            return c
    return None


def all_labels() -> list[str]:
    """All labels across all courses (deduped)."""
    seen: set[str] = set()
    result: list[str] = []
    for concepts in _BY_COURSE.values():
        for c in concepts:
            if c["label"] not in seen:
                seen.add(c["label"])
                result.append(c["label"])
    return result
