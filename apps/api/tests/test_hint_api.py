"""
Tests for the /hint API endpoint and LLM integration.

Tests that the hint endpoint works correctly with both
DummyLLMClient and configured LLM providers.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from api import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


class TestHintAPI:
    """Tests for POST /hint endpoint."""

    def test_hint_endpoint_exists(self, client):
        """Test that the /hint endpoint is available."""
        response = client.post(
            "/hint",
            json={
                "problem_id": "test_prob_1",
                "problem_latex": "x + 5 = 10",
            },
        )
        assert response.status_code == 200

    def test_hint_response_structure(self, client):
        """Test that hint response has required fields."""
        response = client.post(
            "/hint",
            json={
                "problem_id": "test_prob_1",
                "problem_latex": "x + 5 = 10",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "problem_id" in data
        assert "hint" in data
        assert "hint_type" in data

    def test_hint_with_current_step(self, client):
        """Test hint generation with current step information."""
        response = client.post(
            "/hint",
            json={
                "problem_id": "test_prob_1",
                "problem_latex": "x + 5 = 10",
                "current_step_latex": "x = ?",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "hint" in data
        assert len(data["hint"]) > 0

    def test_hint_with_error_description(self, client):
        """Test hint generation with error information."""
        response = client.post(
            "/hint",
            json={
                "problem_id": "test_prob_1",
                "problem_latex": "x + 5 = 10",
                "error_description": "Student got x = 15",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "hint" in data

    def test_hint_with_context_tags(self, client):
        """Test hint generation with context tags."""
        response = client.post(
            "/hint",
            json={
                "problem_id": "test_prob_1",
                "problem_latex": "x + 5 = 10",
                "context_tags": "basic,two-step",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "hint" in data

    def test_hint_problem_id_preservation(self, client):
        """Test that problem_id is preserved in response."""
        problem_id = "unique_prob_12345"
        response = client.post(
            "/hint",
            json={
                "problem_id": problem_id,
                "problem_latex": "2x = 10",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["problem_id"] == problem_id

    def test_hint_minimal_request(self, client):
        """Test hint generation with minimal required fields."""
        response = client.post(
            "/hint",
            json={
                "problem_id": "test_prob_1",
                "problem_latex": "x = 5",
            },
        )
        assert response.status_code == 200
        assert response.json()["hint"]


class TestLLMFactory:
    """Tests for LLM client factory functions."""

    def test_get_llm_client_returns_dummy_by_default(self):
        """Test that DummyLLMClient is returned by default."""
        from llm_factory import get_llm_client
        from llm_interfaces import DummyLLMClient
        
        client = get_llm_client()
        assert isinstance(client, DummyLLMClient)

    def test_get_sync_llm_client_returns_sync_dummy_by_default(self):
        """Test that SyncDummyLLMClient is returned by default."""
        from llm_factory import get_sync_llm_client
        from llm_interfaces import SyncDummyLLMClient
        
        client = get_sync_llm_client()
        assert isinstance(client, SyncDummyLLMClient)

    def test_cached_llm_client(self):
        """Test that cached LLM client returns same instance."""
        from llm_factory import get_cached_llm_client
        
        client1 = get_cached_llm_client()
        client2 = get_cached_llm_client()
        assert client1 is client2

    def test_reset_llm_clients(self):
        """Test that reset_llm_clients clears cache."""
        from llm_factory import get_cached_llm_client, reset_llm_clients
        
        client1 = get_cached_llm_client()
        reset_llm_clients()
        client2 = get_cached_llm_client()
        assert client1 is not client2


class TestRepositoryFactory:
    """Tests for repository factory functions."""

    def test_create_jsonl_repositories_by_default(self):
        """Test that JSONL repositories are created by default."""
        from repo_factory import create_problem_repository, create_attempt_repository
        from repositories import JSONLProblemRepository, JSONLAttemptRepository
        
        # USE_DATABASE should be False by default
        prob_repo = create_problem_repository()
        att_repo = create_attempt_repository()
        
        assert isinstance(prob_repo, JSONLProblemRepository)
        assert isinstance(att_repo, JSONLAttemptRepository)

    def test_cached_repositories(self):
        """Test that cached repositories return same instance."""
        from repo_factory import get_problem_repository, get_attempt_repository
        
        prob1 = get_problem_repository()
        prob2 = get_problem_repository()
        assert prob1 is prob2
        
        att1 = get_attempt_repository()
        att2 = get_attempt_repository()
        assert att1 is att2

    def test_reset_repositories(self):
        """Test that reset_repositories clears cache."""
        from repo_factory import get_problem_repository, reset_repositories
        
        repo1 = get_problem_repository()
        reset_repositories()
        repo2 = get_problem_repository()
        assert repo1 is not repo2


class TestDummyLLMHints:
    """Tests for hint generation with DummyLLMClient."""

    @pytest.mark.asyncio
    async def test_dummy_generate_hint(self):
        """Test that DummyLLMClient generates hints."""
        from llm_interfaces import DummyLLMClient
        
        client = DummyLLMClient()
        hint = await client.generate_hint("problem: x + 5 = 10")
        assert hint
        assert isinstance(hint, str)
        assert len(hint) > 0

    @pytest.mark.asyncio
    async def test_dummy_generates_different_hints(self):
        """Test that DummyLLMClient can generate different hints with different inputs."""
        from llm_interfaces import DummyLLMClient
        
        client = DummyLLMClient()
        # Different inputs should produce different hints
        hint1 = await client.generate_hint("problem: x + 5 = 10")
        hint2 = await client.generate_hint("problem: x + 5 = 10", error_description="arithmetic error")
        hint3 = await client.generate_hint("problem: x + 5 = 10", current_step_latex="x = 5")
        
        hints = {hint1, hint2, hint3}
        # Should have variety based on different inputs
        assert len(hints) == 3

    @pytest.mark.asyncio
    async def test_dummy_generate_word_problem(self):
        """Test that DummyLLMClient generates word problems."""
        from llm_interfaces import DummyLLMClient
        
        client = DummyLLMClient()
        problem = await client.generate_word_problem(
            equation_latex="x + 5 = 10",
            solution_latex="x = 5",
            reading_level="grade_8",
            context_tags=["algebra"]
        )
        assert problem
        assert isinstance(problem, str)

    @pytest.mark.asyncio
    async def test_dummy_evaluate_student_work(self):
        """Test that DummyLLMClient evaluates student work."""
        from llm_interfaces import DummyLLMClient
        
        client = DummyLLMClient()
        feedback = await client.evaluate_student_work(
            problem_latex="x + 5 = 10",
            student_work_latex="x = 5",
            expected_solution_latex="x = 5"
        )
        assert feedback
        assert isinstance(feedback, dict)
