"""
Integration tests for concept API endpoints.

Tests validate:
- /generate endpoint includes concept fields
- /concepts endpoint lists all concepts
- /concepts/{concept_id} endpoint returns specific concept
- Concept data is correctly serialized in responses
"""

import pytest
from fastapi.testclient import TestClient
from api import app
from concepts import CONCEPTS


client = TestClient(app)


# ============================================================================
# Test /generate Endpoint with Concepts
# ============================================================================

def test_generate_problem_includes_concepts():
    """Test that /generate endpoint includes concept fields in response."""
    response = client.get(
        "/generate",
        params={"course": "algebra_1", "topic": "alg1_linear_solve_one_var", "difficulty": 2}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have concept fields
    assert "concept_ids" in data
    assert "primary_concept_id" in data
    
    # Should be populated
    assert isinstance(data["concept_ids"], list)
    assert len(data["concept_ids"]) > 0
    assert data["primary_concept_id"] is not None


def test_generate_problem_concept_ids_are_valid():
    """Test that generated problem concepts are valid."""
    response = client.get(
        "/generate",
        params={"course": "algebra_1", "topic": "alg1_linear_solve_one_var", "difficulty": 1}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # All concept IDs should be valid
    for concept_id in data["concept_ids"]:
        assert concept_id in CONCEPTS, f"Invalid concept ID: {concept_id}"
    
    # Primary concept should be in the list
    if data["primary_concept_id"]:
        assert data["primary_concept_id"] in data["concept_ids"]


def test_generate_different_difficulties_map_to_concepts():
    """Test that different difficulties map to different concepts."""
    concepts_by_difficulty = {}
    
    for difficulty in [1, 2, 3, 4]:
        response = client.get(
            "/generate",
            params={"course": "algebra_1", "topic": "alg1_linear_solve_one_var", "difficulty": difficulty}
        )
        
        assert response.status_code == 200
        data = response.json()
        concepts_by_difficulty[difficulty] = data["primary_concept_id"]
    
    # Different difficulties should (usually) map to different concepts
    # Note: we're using linear equations which have clear difficulty -> concept mapping
    assert concepts_by_difficulty[1] == "alg1.linear_eq.one_step_int"
    assert concepts_by_difficulty[2] == "alg1.linear_eq.two_step_int"


# ============================================================================
# Test /concepts Endpoint
# ============================================================================

def test_list_all_concepts():
    """Test GET /concepts lists all concepts."""
    response = client.get("/concepts")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have concepts and total
    assert "concepts" in data
    assert "total" in data
    
    # Should match CONCEPTS registry
    assert data["total"] == len(CONCEPTS)
    assert len(data["concepts"]) == len(CONCEPTS)


def test_list_concepts_has_required_fields():
    """Test that concept list items have all required fields."""
    response = client.get("/concepts")
    
    assert response.status_code == 200
    data = response.json()
    
    required_fields = [
        "id", "name", "course_id", "unit_id", "topic_id",
        "kind", "description", "prerequisites", "difficulty_min",
        "difficulty_max", "examples_latex", "tags"
    ]
    
    for concept in data["concepts"][:5]:  # Check first 5
        for field in required_fields:
            assert field in concept, f"Missing field: {field}"


def test_list_concepts_filter_by_course():
    """Test filtering concepts by course_id."""
    response = client.get("/concepts", params={"course_id": "algebra_1"})
    
    assert response.status_code == 200
    data = response.json()
    
    # Should only have algebra_1 concepts
    for concept in data["concepts"]:
        assert concept["course_id"] == "algebra_1"
    
    # Should have multiple units
    units = set(c["unit_id"] for c in data["concepts"])
    assert len(units) > 1


def test_list_concepts_filter_by_topic():
    """Test filtering concepts by topic_id."""
    response = client.get(
        "/concepts",
        params={"topic_id": "alg1_linear_solve_one_var"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should only have concepts from this topic
    for concept in data["concepts"]:
        assert concept["topic_id"] == "alg1_linear_solve_one_var"


def test_list_concepts_filter_by_unit():
    """Test filtering concepts by unit_id."""
    response = client.get(
        "/concepts",
        params={"unit_id": "alg1_unit_linear_equations"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should only have concepts from this unit
    for concept in data["concepts"]:
        assert concept["unit_id"] == "alg1_unit_linear_equations"


def test_list_concepts_multiple_filters():
    """Test that multiple filters can be combined."""
    response = client.get(
        "/concepts",
        params={
            "course_id": "algebra_1",
            "topic_id": "alg1_linear_solve_one_var"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should satisfy both filters
    for concept in data["concepts"]:
        assert concept["course_id"] == "algebra_1"
        assert concept["topic_id"] == "alg1_linear_solve_one_var"


# ============================================================================
# Test /concepts/{concept_id} Endpoint
# ============================================================================

def test_get_specific_concept():
    """Test GET /concepts/{concept_id} returns concept details."""
    concept_id = "alg1.linear_eq.one_step_int"
    response = client.get(f"/concepts/{concept_id}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["id"] == concept_id
    assert data["name"] is not None
    assert data["kind"] in ["skill", "definition", "strategy", "representation"]


def test_get_concept_with_prerequisites():
    """Test that prerequisites are returned correctly."""
    # Find a concept with prerequisites
    concept_with_prereqs = None
    for c in CONCEPTS.values():
        if c.prerequisites:
            concept_with_prereqs = c
            break
    
    if concept_with_prereqs:
        response = client.get(f"/concepts/{concept_with_prereqs.id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "prerequisites" in data
        assert len(data["prerequisites"]) > 0
        assert data["prerequisites"] == concept_with_prereqs.prerequisites


def test_get_concept_not_found():
    """Test 404 for nonexistent concept."""
    response = client.get("/concepts/nonexistent.concept.id")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_concept_difficulty_range():
    """Test that difficulty min/max are returned."""
    response = client.get("/concepts/alg1.linear_eq.one_step_int")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "difficulty_min" in data
    assert "difficulty_max" in data
    assert data["difficulty_min"] <= data["difficulty_max"]
    assert 1 <= data["difficulty_min"] <= 6
    assert 1 <= data["difficulty_max"] <= 6


# ============================================================================
# Test Concept Response Structure
# ============================================================================

def test_concept_response_serialization():
    """Test that Concept objects serialize correctly to JSON."""
    response = client.get("/concepts/alg1.linear_eq.one_step_int")
    
    assert response.status_code == 200
    data = response.json()
    
    # All fields should be JSON-serializable
    assert isinstance(data["id"], str)
    assert isinstance(data["name"], str)
    assert isinstance(data["prerequisites"], list)
    assert isinstance(data["examples_latex"], list)
    assert isinstance(data["tags"], list)


def test_concepts_list_response_structure():
    """Test that ConceptsListResponse serializes correctly."""
    response = client.get("/concepts?course_id=algebra_1")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have expected structure
    assert isinstance(data, dict)
    assert "concepts" in data
    assert "total" in data
    assert isinstance(data["concepts"], list)
    assert isinstance(data["total"], int)
    assert len(data["concepts"]) == data["total"]


# ============================================================================
# Test Integration with Generate Endpoint
# ============================================================================

def test_generate_concept_references_valid_concept():
    """Test that primary_concept_id from /generate exists in /concepts."""
    # Generate a problem
    gen_response = client.get(
        "/generate",
        params={"course": "algebra_1", "topic": "alg1_linear_solve_one_var", "difficulty": 2}
    )
    
    assert gen_response.status_code == 200
    problem = gen_response.json()
    
    # Get the concept
    if problem["primary_concept_id"]:
        concept_response = client.get(f"/concepts/{problem['primary_concept_id']}")
        assert concept_response.status_code == 200
        
        concept = concept_response.json()
        assert concept["id"] == problem["primary_concept_id"]
