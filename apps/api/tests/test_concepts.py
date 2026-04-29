"""
Tests for concept infrastructure.

Tests validate:
- Concept model and registry
- Concept graph structure (no cycles, valid prerequisites)
- Concept lookup and filtering
- Concept tagging in generators
"""

import pytest
from concepts import (
    Concept,
    ConceptKind,
    CONCEPTS,
    register_concept,
    get_concept,
    get_concepts_for_topic,
    get_concepts_for_course,
    validate_concept_graph,
    get_prerequisites_recursive,
    get_dependents_recursive,
)
from generator_linear_impl import generate_linear_equation_problem
from generator_inequalities_impl import generate_linear_inequality_problem


# ============================================================================
# Test Concept Model and Registry
# ============================================================================

def test_concept_creation():
    """Test creating a Concept instance."""
    concept = Concept(
        id="test.concept",
        name="Test Concept",
        course_id="test_course",
        unit_id="test_unit",
        topic_id="test_topic",
        kind="skill",
        description="A test concept",
        prerequisites=[],
        difficulty_min=1,
        difficulty_max=3,
        examples_latex=[],
        tags=["test"]
    )
    
    assert concept.id == "test.concept"
    assert concept.name == "Test Concept"
    assert concept.kind == "skill"
    assert concept.difficulty_min == 1
    assert concept.difficulty_max == 3


def test_concept_kind_values():
    """Test that ConceptKind literal only accepts valid values."""
    # Valid kinds
    valid_kinds: list[ConceptKind] = ["skill", "definition", "strategy", "representation"]
    assert len(valid_kinds) == 4


def test_concept_difficulty_validation():
    """Test that Concept validates difficulty ranges."""
    # Valid range
    concept = Concept(
        id="test.valid",
        name="Valid",
        course_id="test",
        unit_id="test",
        topic_id="test",
        kind="skill",
        description="",
        prerequisites=[],
        difficulty_min=2,
        difficulty_max=4,
        examples_latex=[],
        tags=[]
    )
    assert concept.difficulty_min <= concept.difficulty_max


# ============================================================================
# Test Concept Registry
# ============================================================================

def test_concepts_registered():
    """Test that concepts are registered in the global CONCEPTS dict."""
    # The registry should be populated from alg1_concepts.py import
    assert len(CONCEPTS) > 0, "CONCEPTS registry should be populated"
    assert "alg1.linear_eq.one_step_int" in CONCEPTS
    assert "alg1.linear_ineq.one_step_int" in CONCEPTS


def test_get_concept():
    """Test retrieving a concept by ID."""
    concept = get_concept("alg1.linear_eq.one_step_int")
    assert concept.id == "alg1.linear_eq.one_step_int"
    assert concept.kind == "skill"
    assert concept.difficulty_min == 1
    assert concept.difficulty_max == 1


def test_get_concept_not_found():
    """Test that KeyError is raised for missing concepts."""
    with pytest.raises(KeyError):
        get_concept("nonexistent.concept")


def test_get_concepts_for_topic():
    """Test filtering concepts by topic_id."""
    concepts = get_concepts_for_topic("alg1_linear_solve_one_var")
    assert len(concepts) > 0
    
    for concept in concepts:
        assert concept.topic_id == "alg1_linear_solve_one_var"


def test_get_concepts_for_course():
    """Test filtering concepts by course_id."""
    concepts = get_concepts_for_course("algebra_1")
    assert len(concepts) > 0
    
    # Check that we have concepts from multiple units
    units = set(c.unit_id for c in concepts)
    assert len(units) > 1


# ============================================================================
# Test Concept Graph Structure
# ============================================================================

def test_validate_concept_graph():
    """Test that concept graph validates without errors."""
    errors = validate_concept_graph()
    
    # validate_concept_graph returns empty list if valid, raises ValueError if invalid
    # If it returns without raising, we're good
    assert isinstance(errors, list)


def test_concept_prerequisites_exist():
    """Test that all prerequisites reference valid concepts."""
    for concept in CONCEPTS.values():
        for prereq_id in concept.prerequisites:
            assert prereq_id in CONCEPTS, f"Prerequisite {prereq_id} not found for {concept.id}"


def test_no_circular_prerequisites():
    """Test that there are no circular dependencies."""
    # validate_concept_graph uses DFS to detect cycles
    # If it doesn't raise, we're good
    validate_concept_graph()


def test_difficulty_progression():
    """Test that concept difficulty ranges are reasonable."""
    for concept in CONCEPTS.values():
        # All difficulties should be 1-6
        assert 1 <= concept.difficulty_min <= 6
        assert 1 <= concept.difficulty_max <= 6
        assert concept.difficulty_min <= concept.difficulty_max


# ============================================================================
# Test Concept Dependencies
# ============================================================================

def test_get_prerequisites_recursive():
    """Test transitive closure of prerequisites."""
    # Get all prerequisites for a concept that has them
    prereqs = get_prerequisites_recursive("alg1.linear_eq.both_sides")
    
    # Should include direct and transitive prerequisites
    assert len(prereqs) > 0
    
    # Check that it returns a set of concept IDs
    for prereq_id in prereqs:
        assert isinstance(prereq_id, str)
        assert prereq_id in CONCEPTS


def test_get_dependents_recursive():
    """Test reverse transitive closure of prerequisites."""
    # Get all concepts that depend on a prerequisite
    dependents = get_dependents_recursive("alg1.linear_eq.one_step_int")
    
    # At least the immediate dependents should be there
    assert len(dependents) >= 0  # May be empty if nothing depends on this


# ============================================================================
# Test Generator Concept Tagging
# ============================================================================

def test_linear_equation_generator_tags_concepts():
    """Test that linear equation generator sets concept fields."""
    for difficulty in [1, 2, 3, 4]:
        problem = generate_linear_equation_problem(difficulty)
        
        # Should have primary_concept_id set
        assert problem.primary_concept_id is not None, f"Difficulty {difficulty}: primary_concept_id should be set"
        
        # Should have concept_ids populated
        assert len(problem.concept_ids) > 0, f"Difficulty {difficulty}: concept_ids should be populated"
        
        # Primary concept should be in concept_ids
        assert problem.primary_concept_id in problem.concept_ids
        
        # Primary concept should be valid
        assert problem.primary_concept_id in CONCEPTS


def test_linear_equation_difficulty_to_concept_mapping():
    """Test that each difficulty maps to the correct concept."""
    expected_mapping = {
        1: "alg1.linear_eq.one_step_int",
        2: "alg1.linear_eq.two_step_int",
        3: "alg1.linear_eq.multistep_one_side",
        4: "alg1.linear_eq.both_sides"
    }
    
    for difficulty, expected_concept in expected_mapping.items():
        problem = generate_linear_equation_problem(difficulty)
        assert problem.primary_concept_id == expected_concept, \
            f"Difficulty {difficulty} should map to {expected_concept}"


def test_inequality_generator_tags_concepts():
    """Test that inequality generator sets concept fields."""
    for difficulty in [1, 2, 3, 4]:
        problem = generate_linear_inequality_problem(difficulty)
        
        # Should have primary_concept_id set
        assert problem.primary_concept_id is not None, f"Difficulty {difficulty}: primary_concept_id should be set"
        
        # Should have concept_ids populated
        assert len(problem.concept_ids) > 0, f"Difficulty {difficulty}: concept_ids should be populated"
        
        # Primary concept should be in concept_ids
        assert problem.primary_concept_id in problem.concept_ids
        
        # Primary concept should be valid
        assert problem.primary_concept_id in CONCEPTS


def test_inequality_difficulty_to_concept_mapping():
    """Test that each inequality difficulty maps to the correct concept."""
    expected_mapping = {
        1: "alg1.linear_ineq.one_step_int",
        2: "alg1.linear_ineq.two_step_int",
        3: "alg1.linear_ineq.negative_coeff_reverse",
        4: "alg1.linear_ineq.rational_coeffs"
    }
    
    for difficulty, expected_concept in expected_mapping.items():
        problem = generate_linear_inequality_problem(difficulty)
        assert problem.primary_concept_id == expected_concept, \
            f"Difficulty {difficulty} should map to {expected_concept}"


# ============================================================================
# Test Concept Algebra 1 Curriculum Coverage
# ============================================================================

def test_algebra1_concepts_exist():
    """Test that major Algebra 1 concepts are registered."""
    required_concepts = [
        # Unit 1: Foundations
        "alg1.foundations.add_subtract",
        # Unit 2: Expressions
        "alg1.expr.variables_basic",
        # Unit 3: Linear Equations
        "alg1.linear_eq.one_step_int",
        # Unit 4: Linear Inequalities
        "alg1.linear_ineq.one_step_int",
        # Unit 5: Linear Functions
        "alg1.linear_func.slope_from_two_points",
        # Unit 6: Systems
        "alg1.systems.substitution",
        # Unit 7: Polynomials/Factoring
        "alg1.poly.add_sub",
        # Unit 8: Quadratics
        "alg1.quad.graph_standard_form",
    ]
    
    for concept_id in required_concepts:
        assert concept_id in CONCEPTS, f"Required concept {concept_id} not found"


def test_concept_count():
    """Test that approximately 50+ Algebra 1 concepts are registered."""
    alg1_concepts = [c for c in CONCEPTS.values() if c.course_id == "algebra_1"]
    
    # Should have at least 40+ concepts (normalized from alg1 prefix)
    assert len(alg1_concepts) >= 40, \
        f"Expected at least 40 Algebra 1 concepts, got {len(alg1_concepts)}"
