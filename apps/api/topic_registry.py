"""
Topic registry integrating taxonomy.py into the unified topic metadata system.
This module manages a global registry of all courses, units, and topics.
"""

from dataclasses import dataclass
from typing import Dict, List

from taxonomy import (
    UNIT_CALC_DEFAULTS,
    get_prealgebra_course,
    get_algebra1_course,
    get_algebra2_course,
    get_geometry_course,
    get_precalculus_course,
    get_calculus1_course,
    get_calculus2_course,
    get_calculus3_course,
    get_diffeq_course,
    get_linearalgebra_course,
    get_discrete_math_course,
    get_proofs_course,
    get_contest_math_course,
    get_intro_prob_stats_course,
    get_probability_course,
    get_mathematical_statistics_course,
)


@dataclass
class TopicMetadata:
    """Metadata for a single topic."""
    topic_id: str
    topic_name: str
    unit_id: str
    unit_name: str
    course_id: str
    course_name: str
    prerequisites: List[str]
    calculator_mode: str = "none"
    is_honors: bool = False


# Global registries
TOPIC_REGISTRY: Dict[str, TopicMetadata] = {}
COURSE_REGISTRY: Dict[str, Dict] = {}


def register_course(course_id: str, course_name: str) -> None:
    """Register a course in the registry."""
    COURSE_REGISTRY[course_id] = {
        "course_id": course_id,
        "course_name": course_name,
        "units": {},
    }


def register_unit(course_id: str, unit_id: str, unit_name: str, is_honors: bool = False) -> None:
    """Register a unit within a course."""
    if course_id not in COURSE_REGISTRY:
        register_course(course_id, course_id)

    COURSE_REGISTRY[course_id]["units"][unit_id] = {
        "unit_id": unit_id,
        "unit_name": unit_name,
        "is_honors": is_honors,
        "topics": {},
    }


def register_topic(
    course_id: str,
    unit_id: str,
    topic_id: str,
    topic_name: str,
    description: str = "",
    calculator_mode: str = "none",
    is_honors: bool = False,
) -> None:
    """Register a topic within a unit."""
    if course_id not in COURSE_REGISTRY:
        raise ValueError(f"Course {course_id} not registered")
    if unit_id not in COURSE_REGISTRY[course_id]["units"]:
        raise ValueError(f"Unit {unit_id} not registered in course {course_id}")

    if topic_id in TOPIC_REGISTRY:
        raise ValueError(f"Topic {topic_id} already registered")

    course_name = COURSE_REGISTRY[course_id]["course_name"]
    unit_name = COURSE_REGISTRY[course_id]["units"][unit_id]["unit_name"]

    topic_meta = TopicMetadata(
        topic_id=topic_id,
        topic_name=topic_name,
        unit_id=unit_id,
        unit_name=unit_name,
        course_id=course_id,
        course_name=course_name,
        prerequisites=[],
        calculator_mode=calculator_mode,
        is_honors=is_honors,
    )

    TOPIC_REGISTRY[topic_id] = topic_meta
    COURSE_REGISTRY[course_id]["units"][unit_id]["topics"][topic_id] = topic_meta


def list_topics() -> list[TopicMetadata]:
    """Return all TopicMetadata sorted by curriculum sequence order."""
    return sorted(
        TOPIC_REGISTRY.values(),
        key=lambda t: (t.course_id, t.unit_id, t.topic_id),
    )


def initialize_topic_registry() -> None:
    """
    Load all courses from taxonomy and populate the global registry.
    Registers all courses, units, and topics.
    """
    course_builders = [
        get_prealgebra_course,
        get_algebra1_course,
        get_geometry_course,
        get_algebra2_course,
        get_precalculus_course,
        get_calculus1_course,
        get_calculus2_course,
        get_calculus3_course,
        get_diffeq_course,
        get_linearalgebra_course,
        get_discrete_math_course,
        get_proofs_course,
        get_contest_math_course,
        get_intro_prob_stats_course,
        get_probability_course,
        get_mathematical_statistics_course,
    ]

    for course_builder in course_builders:
        course = course_builder()

        register_course(course.id, course.name)

        for unit in course.units:
            # Detect honors status from "(H)" suffix or explicit field
            is_honors_unit = getattr(unit, 'is_honors', False) or "(H)" in unit.name
            # Look up calculator mode for this unit
            unit_calc = UNIT_CALC_DEFAULTS.get(unit.id, "none")

            register_unit(course.id, unit.id, unit.name, is_honors=is_honors_unit)

            for topic in unit.topics:
                register_topic(
                    course_id=course.id,
                    unit_id=unit.id,
                    topic_id=topic.id,
                    topic_name=topic.name,
                    calculator_mode=unit_calc,
                    is_honors=is_honors_unit,
                )

                if topic_meta := TOPIC_REGISTRY.get(topic.id):
                    if hasattr(topic, 'prerequisites') and topic.prerequisites:
                        topic_meta.prerequisites = topic.prerequisites

    _validate_registry()


def _validate_registry() -> None:
    total_topics = len(TOPIC_REGISTRY)
    total_courses = len(COURSE_REGISTRY)
    total_units = sum(len(c["units"]) for c in COURSE_REGISTRY.values())

    seen_ids = set()
    for topic_id in TOPIC_REGISTRY.keys():
        if topic_id in seen_ids:
            raise ValueError(f"Duplicate topic_id detected: {topic_id}")
        seen_ids.add(topic_id)

    print(f"[OK] Topic Registry Initialized:")
    print(f"  - {total_courses} courses")
    print(f"  - {total_units} units")
    print(f"  - {total_topics} topics")


# Initialize the registry on module import
initialize_topic_registry()
