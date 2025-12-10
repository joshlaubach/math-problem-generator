"""
Topic registry integrating taxonomy.py into the unified topic metadata system.
This module manages a global registry of all courses, units, and topics.
"""

from dataclasses import dataclass
from typing import Dict, List

from taxonomy import (
    get_prealgebra_course,
    get_algebra1_course,
    get_algebra2_course,
    get_geometry_course,
    get_precalculus_course,
    get_calculus1_course,
    get_calculus2_course,
    get_calculus3_course,
    get_probstat_course,
    get_linearalgebra_course,
    get_diffeq_course,
    get_proofs_course,
    get_sat_course,
    get_ap_calc_ab_course,
    get_ap_calc_bc_course,
    get_ap_stats_course,
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


def register_unit(course_id: str, unit_id: str, unit_name: str) -> None:
    """Register a unit within a course."""
    if course_id not in COURSE_REGISTRY:
        register_course(course_id, course_id)
    
    COURSE_REGISTRY[course_id]["units"][unit_id] = {
        "unit_id": unit_id,
        "unit_name": unit_name,
        "topics": {},
    }


def register_topic(
    course_id: str,
    unit_id: str,
    topic_id: str,
    topic_name: str,
    description: str = "",
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
    )
    
    TOPIC_REGISTRY[topic_id] = topic_meta
    COURSE_REGISTRY[course_id]["units"][unit_id]["topics"][topic_id] = topic_meta


def list_topics() -> list[TopicMetadata]:
    """Return all TopicMetadata sorted by (course_name, unit_name, topic_name)."""
    return sorted(
        TOPIC_REGISTRY.values(),
        key=lambda t: (t.course_name, t.unit_name, t.topic_name),
    )


def initialize_topic_registry() -> None:
    """
    Load all courses from taxonomy and populate the global registry.
    Registers all courses, units, and topics.
    """
    # Get all course builder functions
    course_builders = [
        get_prealgebra_course,
        get_algebra1_course,
        get_algebra2_course,
        get_geometry_course,
        get_precalculus_course,
        get_calculus1_course,
        get_calculus2_course,
        get_calculus3_course,
        get_probstat_course,
        get_linearalgebra_course,
        get_diffeq_course,
        get_proofs_course,
        get_sat_course,
        get_ap_calc_ab_course,
        get_ap_calc_bc_course,
        get_ap_stats_course,
    ]
    
    # Build all courses from taxonomy
    for course_builder in course_builders:
        course = course_builder()
        
        # Register the course
        register_course(course.id, course.name)
        
        # Register all units and topics within this course
        for unit in course.units:
            register_unit(course.id, unit.id, unit.name)
            
            for topic in unit.topics:
                register_topic(
                    course_id=course.id,
                    unit_id=unit.id,
                    topic_id=topic.id,
                    topic_name=topic.name,
                )
                
                # Set prerequisites if available
                if topic_id := TOPIC_REGISTRY.get(topic.id):
                    if hasattr(topic, 'prerequisites') and topic.prerequisites:
                        topic_id.prerequisites = topic.prerequisites
    
    # Validate registry
    _validate_registry()


def _validate_registry() -> None:
    """
    Validate the registry for consistency.
    Checks for duplicates and prints summary statistics.
    """
    total_topics = len(TOPIC_REGISTRY)
    total_courses = len(COURSE_REGISTRY)
    total_units = sum(len(c["units"]) for c in COURSE_REGISTRY.values())
    
    # Check for duplicates
    seen_ids = set()
    for topic_id in TOPIC_REGISTRY.keys():
        if topic_id in seen_ids:
            raise ValueError(f"Duplicate topic_id detected: {topic_id}")
        seen_ids.add(topic_id)
    
    print(f"✓ Topic Registry Initialized:")
    print(f"  - {total_courses} courses")
    print(f"  - {total_units} units")
    print(f"  - {total_topics} topics")


# Initialize the registry on module import
initialize_topic_registry()
