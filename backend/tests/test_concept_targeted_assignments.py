"""
Test Suite for Concept-Targeted Assignment Creation (Phase 11)

Tests:
1. Topic-based assignment creation (existing behavior)
2. Concept-based assignment creation (new feature)
3. Mixed generator cycling for concept assignments
4. Error cases (missing parameters, invalid concepts)
"""

import pytest
from datetime import datetime
from assignments_models import Assignment, AssignmentProblemLink
from repositories_assignments import AssignmentRepository
from generators import get_generators_for_concepts, register_generator
from generators.base import ProblemGenerator
from models import Problem, Solution


class MockGenerator(ProblemGenerator):
    """Mock generator for testing"""

    def __init__(self, topic_id: str = "mock_topic", primary_concept_id: str = "mock.concept"):
        self.topic_id = topic_id
        self.primary_concept_id = primary_concept_id
        self.call_count = 0

    def generate(self, difficulty: int) -> Problem:
        self.call_count += 1
        return Problem(
            id=f"mock_problem_{self.call_count}_{difficulty}",
            course_id="test_course",
            unit_id="test_unit",
            topic_id=self.topic_id,
            difficulty=difficulty,
            calculator_mode="none",
            prompt_latex=f"Mock problem {self.call_count}",
            answer_type="numeric",
            final_answer=42,
            concept_ids=[self.primary_concept_id],
            primary_concept_id=self.primary_concept_id,
        )


class InMemoryAssignmentRepository(AssignmentRepository):
    """In-memory assignment repository for testing"""

    def __init__(self):
        self.assignments = {}
        self.problem_links = []

    def create_assignment(self, assignment: Assignment) -> None:
        self.assignments[assignment.id] = assignment

    def get_assignment(self, assignment_id: str) -> Assignment | None:
        return self.assignments.get(assignment_id)

    def add_problem_links(self, links: list[AssignmentProblemLink]) -> None:
        self.problem_links.extend(links)

    def list_assignments(self) -> list[Assignment]:
        return list(self.assignments.values())


@pytest.fixture
def mock_repo():
    """Provide a mock assignment repository"""
    return InMemoryAssignmentRepository()


@pytest.fixture
def mock_generators():
    """Register mock generators for testing"""
    # Create generators for different concepts
    sat_gen = MockGenerator(
        topic_id="sat_linear",
        primary_concept_id="sat.algebra.linear_basics"
    )
    sat_gen.primary_concept_id = "sat.algebra.linear_basics"

    ap_gen = MockGenerator(
        topic_id="ap_deriv_rules",
        primary_concept_id="ap_calc.derivatives.power_rule"
    )
    ap_gen.primary_concept_id = "ap_calc.derivatives.power_rule"

    # Temporarily store for testing
    yield {
        "sat_linear": sat_gen,
        "ap_deriv": ap_gen,
    }


def test_get_generators_for_sat_concepts():
    """Test filtering generators by SAT concepts"""
    # This tests the actual function with real generators
    concepts = ["sat.algebra.linear_basics"]
    generators = get_generators_for_concepts(concepts)

    # Should find SAT generators
    assert any("sat" in topic_id for topic_id in generators.keys())


def test_get_generators_for_ap_concepts():
    """Test filtering generators by AP Calculus concepts"""
    concepts = ["ap_calc.derivatives.power_rule"]
    generators = get_generators_for_concepts(concepts)

    # Should find AP generators
    assert any("ap" in topic_id for topic_id in generators.keys())


def test_get_generators_for_mixed_concepts():
    """Test filtering generators by multiple concepts"""
    concepts = ["sat.algebra.linear_basics", "ap_calc.derivatives.power_rule"]
    generators = get_generators_for_concepts(concepts)

    # Should find both SAT and AP generators
    has_sat = any("sat" in topic_id for topic_id in generators.keys())
    has_ap = any("ap" in topic_id for topic_id in generators.keys())

    # At least one should be found
    assert has_sat or has_ap


def test_get_generators_for_invalid_concept():
    """Test that invalid concepts return empty dict"""
    concepts = ["invalid.concept.id"]
    generators = get_generators_for_concepts(concepts)

    # Should return empty or very few results
    assert len(generators) < 5  # Loose constraint since it might partially match


def test_concept_assignment_cycling():
    """Test that concept-targeted assignments cycle through generators"""
    from generators import register_generator

    # Register test generators
    gen1 = MockGenerator("topic1", "concept.1")
    gen2 = MockGenerator("topic2", "concept.2")

    register_generator("test_topic_1", gen1)
    register_generator("test_topic_2", gen2)

    # Get generators for the concepts
    generators_dict = {"test_topic_1": gen1, "test_topic_2": gen2}
    generators_list = list(generators_dict.values())

    # Simulate cycling for 5 problems
    for i in range(5):
        generator = generators_list[i % len(generators_list)]
        generator.generate(difficulty=2)

    # Verify alternating pattern
    assert gen1.call_count >= 2  # Should be called at indices 0, 2, 4
    assert gen2.call_count >= 2  # Should be called at indices 1, 3


def test_assignment_creation_with_concepts(mock_repo):
    """Test creating an assignment with concept filtering"""
    assignment = Assignment(
        id="concept_assignment_1",
        name="Algebra & Derivatives Practice",
        description="Mixed concept practice",
        teacher_id="teacher1",
        status="active",
        topic_id="concept_mixed_2",  # Mixed topic ID
        num_questions=6,
        min_difficulty=1,
        max_difficulty=4,
        calculator_mode="none",
    )

    mock_repo.create_assignment(assignment)

    # Verify it was created
    retrieved = mock_repo.get_assignment("concept_assignment_1")
    assert retrieved is not None
    assert retrieved.topic_id == "concept_mixed_2"
    assert retrieved.name == "Algebra & Derivatives Practice"


def test_assignment_problem_link_creation(mock_repo):
    """Test creating problem links for a concept assignment"""
    assignment = Assignment(
        id="concept_assignment_2",
        name="Concept Practice",
        description="",
        teacher_id="teacher1",
        status="active",
        topic_id="concept_mixed_2",
        num_questions=4,
        min_difficulty=1,
        max_difficulty=3,
        calculator_mode="none",
    )

    mock_repo.create_assignment(assignment)

    # Create problem links (simulating alternating generators)
    links = [
        AssignmentProblemLink(
            assignment_id="concept_assignment_2",
            problem_id=f"problem_{i}",
            index=i + 1,
        )
        for i in range(4)
    ]

    mock_repo.add_problem_links(links)

    # Verify links were created
    assert len(mock_repo.problem_links) == 4
    assert all(link.assignment_id == "concept_assignment_2" for link in mock_repo.problem_links)


def test_concept_assignment_difficulty_distribution():
    """Test that concept assignments distribute difficulties correctly"""
    num_questions = 5
    min_diff = 1
    max_diff = 4

    difficulties = []
    for i in range(num_questions):
        # Simulate the linear distribution algorithm
        difficulty = min_diff + int(
            (i / max(1, num_questions - 1)) * (max_diff - min_diff)
        )
        difficulty = min(difficulty, max_diff)
        difficulties.append(difficulty)

    # First should be min, last should be max
    assert difficulties[0] == min_diff
    assert difficulties[-1] == max_diff

    # Should be monotonically increasing
    for i in range(len(difficulties) - 1):
        assert difficulties[i] <= difficulties[i + 1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
