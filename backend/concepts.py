"""
Concept model and registry for organizing algebra curriculum as a DAG.

A Concept represents an atomic learning objective or skill that can be tagged
on problems. Concepts form a directed acyclic graph (DAG) via prerequisites.

Example:
    alg1.linear_eq.one_step_int -> alg1.linear_eq.two_step_int -> alg1.linear_eq.both_sides

This enables:
  - Tracking student mastery at the concept level (not just topic)
  - Recommending problems by prerequisite graph
  - Sequencing curriculum based on mastery
  - Detailed learning path recommendations
"""

from dataclasses import dataclass, field, replace
from typing import Literal, Optional

# Type definitions
ConceptKind = Literal["skill", "definition", "strategy", "representation"]
"""Kind of learning objective a concept represents."""


@dataclass(frozen=True)
class Concept:
    """
    Atomic learning objective in curriculum DAG.

    Attributes:
        id: Unique stable identifier. Format: "course.unit.concept"
           Examples: "alg1.linear_eq.one_step_int", "pre.int.add_same_sign"
        name: Human-readable name for UI/reports
        course_id: Owning course (e.g., "alg1")
        unit_id: Owning unit from taxonomy (e.g., "alg1_unit_linear_equations")
        topic_id: Owning topic from taxonomy (e.g., "alg1_linear_solve_one_var")
        kind: Category of learning objective
        description: What students will understand after mastering this concept
        prerequisites: List of concept IDs that should be mastered first
        difficulty_min: Minimum difficulty level (1–6) where this concept appears
        difficulty_max: Maximum difficulty level (1–6) where this concept appears
        examples_latex: Example expressions or problems in LaTeX notation
        tags: Searchable tags for filtering (e.g., ["algebra", "equations", "visual"])
    """
    id: str
    name: str
    course_id: str
    unit_id: str
    topic_id: str
    kind: ConceptKind
    description: str
    prerequisites: list[str] = field(default_factory=list)
    difficulty_min: int = 1
    difficulty_max: int = 6
    examples_latex: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    version: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate concept structure at creation."""
        if not isinstance(self.difficulty_min, int) or not (1 <= self.difficulty_min <= 6):
            raise ValueError(f"difficulty_min must be 1–6, got {self.difficulty_min}")
        if not isinstance(self.difficulty_max, int) or not (1 <= self.difficulty_max <= 6):
            raise ValueError(f"difficulty_max must be 1–6, got {self.difficulty_max}")
        if self.difficulty_min > self.difficulty_max:
            raise ValueError(
                f"difficulty_min ({self.difficulty_min}) > difficulty_max ({self.difficulty_max})"
            )


# Global concept registry
CONCEPTS: dict[str, Concept] = {}
DEFAULT_CONCEPT_VERSION = "v1"


def register_concept(concept: Concept) -> None:
    """
    Register a concept in the global registry.

    Args:
        concept: Concept instance to register

    Raises:
        ValueError: If concept ID already registered
    """
    if concept.id in CONCEPTS:
        raise ValueError(f"Concept '{concept.id}' already registered")

    # Normalize common course_id aliases so filtering works across datasets
    course_alias_map = {
        "alg1": "algebra_1",
        "algebra1": "algebra_1",
    }
    normalized_course_id = course_alias_map.get(concept.course_id, concept.course_id)
    if normalized_course_id != concept.course_id:
        concept = replace(concept, course_id=normalized_course_id)

    if concept.version is None:
        concept = replace(concept, version=DEFAULT_CONCEPT_VERSION)

    CONCEPTS[concept.id] = concept


def get_concept(concept_id: str) -> Concept:
    """
    Retrieve a concept by ID.

    Args:
        concept_id: Concept identifier

    Returns:
        Concept instance

    Raises:
        KeyError: If concept not found
    """
    if concept_id not in CONCEPTS:
        raise KeyError(f"Concept '{concept_id}' not found in registry")
    return CONCEPTS[concept_id]


def get_concepts_for_topic(topic_id: str) -> list[Concept]:
    """
    Get all concepts assigned to a specific topic.

    Args:
        topic_id: Topic identifier from taxonomy

    Returns:
        List of Concept instances for that topic, sorted by concept ID
    """
    return sorted(
        [c for c in CONCEPTS.values() if c.topic_id == topic_id],
        key=lambda c: c.id,
    )


def get_concepts_for_course(course_id: str) -> list[Concept]:
    """
    Get all concepts in a course.

    Args:
        course_id: Course identifier (e.g., "alg1")

    Returns:
        List of Concept instances for that course, sorted by concept ID
    """
    return sorted(
        [c for c in CONCEPTS.values() if c.course_id == course_id],
        key=lambda c: c.id,
    )


def validate_concept_graph() -> list[str]:
    """
    Validate the concept DAG for consistency and correctness.

    Checks:
      - All prerequisite references exist
      - No duplicate concept IDs (enforced by register_concept)
      - No cycles in the prerequisite graph (DAG property)
      - Difficulty ranges are sensible (1–6)

    Returns:
        List of error messages (empty list = graph is valid)

    Raises:
        ValueError: If graph is invalid (allows caller to handle or crash)
    """
    errors = []

    # Check 1: All prerequisites exist
    for concept in CONCEPTS.values():
        for prereq_id in concept.prerequisites:
            if prereq_id not in CONCEPTS:
                errors.append(
                    f"Concept '{concept.id}' references non-existent prerequisite '{prereq_id}'"
                )

    # Check 2: No cycles via DFS (simple version: not a full toposort)
    def has_cycle(concept_id: str, visited: set[str], rec_stack: set[str]) -> bool:
        """DFS to detect cycles in prerequisite graph."""
        visited.add(concept_id)
        rec_stack.add(concept_id)

        concept = CONCEPTS[concept_id]
        for prereq_id in concept.prerequisites:
            if prereq_id not in CONCEPTS:
                continue  # Already reported above
            if prereq_id not in visited:
                if has_cycle(prereq_id, visited, rec_stack):
                    return True
            elif prereq_id in rec_stack:
                return True

        rec_stack.remove(concept_id)
        return False

    visited: set[str] = set()
    for concept_id in CONCEPTS.keys():
        if concept_id not in visited:
            if has_cycle(concept_id, visited, set()):
                errors.append(f"Cycle detected in concept graph involving '{concept_id}'")
                break  # Report one cycle error

    if errors:
        raise ValueError("\n".join(errors))

    return errors


def get_prerequisites_recursive(concept_id: str) -> set[str]:
    """
    Get all transitive prerequisites for a concept (closure).

    Args:
        concept_id: Concept identifier

    Returns:
        Set of all prerequisite concept IDs (including transitive)
    """
    visited = set()
    to_visit = [concept_id]

    while to_visit:
        cid = to_visit.pop()
        if cid in visited:
            continue
        visited.add(cid)

        concept = CONCEPTS.get(cid)
        if concept:
            to_visit.extend(concept.prerequisites)

    visited.discard(concept_id)  # Don't include self
    return visited


def get_dependents_recursive(concept_id: str) -> set[str]:
    """
    Get all concepts that depend on this one (transitively).

    Args:
        concept_id: Concept identifier

    Returns:
        Set of concept IDs that have this as a prerequisite (direct or transitive)
    """
    dependents = set()
    for concept in CONCEPTS.values():
        if concept_id in get_prerequisites_recursive(concept.id):
            dependents.add(concept.id)
    return dependents


# Bootstrap concept registry on import
try:
    import alg1_concepts  # noqa: F401
except Exception:
    # Safe fallback: leave registry empty if modules unavailable
    pass
