"""
Tests for problem storage (JSON persistence).
"""

import json
import tempfile
from pathlib import Path

import pytest

from generator_linear_impl import generate_linear_equation_problem
from storage import (
    problem_to_dict,
    dict_to_problem,
    save_problem,
    load_problems,
    save_problems_batch,
    clear_problems_file,
)


class TestStorageSerialization:
    """Test conversion between Problem objects and dictionaries."""

    def test_problem_to_dict(self):
        """Test that a Problem can be converted to a dictionary."""
        problem = generate_linear_equation_problem(difficulty=2)
        problem_dict = problem_to_dict(problem)
        
        assert isinstance(problem_dict, dict)
        assert problem_dict["id"] == problem.id
        assert problem_dict["difficulty"] == 2
        assert "solution" in problem_dict
        assert problem_dict["solution"]["sympy_verified"] is True

    def test_dict_to_problem(self):
        """Test that a dictionary can be reconstructed to a Problem."""
        original = generate_linear_equation_problem(difficulty=2)
        problem_dict = problem_to_dict(original)
        reconstructed = dict_to_problem(problem_dict)
        
        assert reconstructed.id == original.id
        assert reconstructed.difficulty == original.difficulty
        assert reconstructed.course_id == original.course_id
        assert "solution" in reconstructed.metadata

    def test_roundtrip_conversion(self):
        """Test that Problem → dict → Problem preserves key information."""
        original = generate_linear_equation_problem(difficulty=3)
        problem_dict = problem_to_dict(original)
        reconstructed = dict_to_problem(problem_dict)
        
        # Key fields should match
        assert reconstructed.id == original.id
        assert reconstructed.difficulty == original.difficulty
        assert reconstructed.prompt_latex == original.prompt_latex
        
        # Solution should be reconstructed
        sol = reconstructed.metadata["solution"]
        assert sol.sympy_verified is True
        assert len(sol.steps) > 0


class TestStoragePersistence:
    """Test saving and loading problems from files."""

    def test_save_and_load_single_problem(self):
        """Test saving and loading a single problem."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "problems.jsonl"
            
            # Generate and save
            problem = generate_linear_equation_problem(difficulty=2)
            save_problem(problem, filepath)
            
            # Verify file was created
            assert filepath.exists()
            
            # Load and verify
            loaded = load_problems(filepath)
            assert len(loaded) == 1
            assert loaded[0].id == problem.id

    def test_save_multiple_problems(self):
        """Test saving and loading multiple problems."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "problems.jsonl"
            
            # Save 5 problems
            problems = [
                generate_linear_equation_problem(difficulty=d)
                for d in [1, 2, 3, 4, 2]
            ]
            save_problems_batch(problems, filepath)
            
            # Load all
            loaded = load_problems(filepath)
            assert len(loaded) == 5

    def test_append_to_existing_file(self):
        """Test that saving appends to existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "problems.jsonl"
            
            # Save first problem
            problem1 = generate_linear_equation_problem(difficulty=1)
            save_problem(problem1, filepath)
            
            # Save second problem
            problem2 = generate_linear_equation_problem(difficulty=2)
            save_problem(problem2, filepath)
            
            # Load both
            loaded = load_problems(filepath)
            assert len(loaded) == 2
            assert loaded[0].id == problem1.id
            assert loaded[1].id == problem2.id

    def test_clear_problems_file(self):
        """Test clearing a problems file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "problems.jsonl"
            
            # Save some problems
            problem = generate_linear_equation_problem(difficulty=2)
            save_problem(problem, filepath)
            assert filepath.exists()
            
            # Clear the file
            clear_problems_file(filepath)
            
            # After clear, file should be deleted
            assert not filepath.exists()

    def test_load_nonexistent_file_raises_error(self):
        """Test that loading from nonexistent file raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "nonexistent.jsonl"
            
            with pytest.raises(FileNotFoundError):
                load_problems(filepath)

    def test_solution_preserved_in_roundtrip(self):
        """Test that solution details are preserved when saving/loading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "problems.jsonl"
            
            # Save problem with solution
            problem = generate_linear_equation_problem(difficulty=2)
            original_solution = problem.metadata["solution"]
            save_problem(problem, filepath)
            
            # Load and verify solution
            loaded = load_problems(filepath)
            loaded_solution = loaded[0].metadata["solution"]
            
            assert loaded_solution.sympy_verified == original_solution.sympy_verified
            assert loaded_solution.final_answer_latex == original_solution.final_answer_latex
            assert len(loaded_solution.steps) == len(original_solution.steps)
