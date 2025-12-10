"""
Tests for word problem mode.
"""

import pytest

from generator_linear_impl import generate_linear_equation_problem
from word_problem import (
    ProblemStyle,
    WordProblemWrapper,
    wrap_problem_as_word_problem,
    problem_supports_word_problem,
)


class TestProblemStyle:
    """Test the ProblemStyle configuration dataclass."""

    def test_default_style(self):
        """Test creating a default ProblemStyle."""
        style = ProblemStyle()
        
        assert style.is_word_problem is False
        assert style.reading_level == "grade_8"
        assert style.context_tags == []

    def test_custom_style(self):
        """Test creating a custom ProblemStyle."""
        style = ProblemStyle(
            is_word_problem=True,
            reading_level="high_school",
            context_tags=["money", "distance"]
        )
        
        assert style.is_word_problem is True
        assert style.reading_level == "high_school"
        assert style.context_tags == ["money", "distance"]


class TestWordProblemWrapper:
    """Test the WordProblemWrapper class."""

    def test_wrap_problem(self):
        """Test wrapping an equation problem."""
        problem = generate_linear_equation_problem(difficulty=2)
        wrapper = WordProblemWrapper(problem)
        
        assert wrapper.problem is problem
        assert wrapper.style.is_word_problem is False

    def test_word_prompt_generated(self):
        """Test that word prompt can be generated."""
        problem = generate_linear_equation_problem(difficulty=2)
        wrapper = WordProblemWrapper(problem)
        
        word_prompt = wrapper.word_prompt
        assert word_prompt is not None
        assert len(word_prompt) > 0

    def test_original_prompt_unchanged(self):
        """Test that original prompt remains unchanged."""
        problem = generate_linear_equation_problem(difficulty=2)
        original_prompt = problem.prompt_latex
        
        wrapper = WordProblemWrapper(problem)
        _ = wrapper.word_prompt
        
        assert wrapper.prompt_latex == original_prompt

    def test_to_problem_with_word_prompt(self):
        """Test converting wrapper to problem with word prompt."""
        problem = generate_linear_equation_problem(difficulty=2)
        wrapper = WordProblemWrapper(problem)
        
        modified = wrapper.to_problem_with_word_prompt()
        assert "word_problem_prompt" in modified.metadata
        assert "problem_style" in modified.metadata


class TestWordProblemConversion:
    """Test the wrap_problem_as_word_problem function."""

    def test_wrap_as_word_problem(self):
        """Test converting a problem to word problem form."""
        problem = generate_linear_equation_problem(difficulty=2)
        word_problem = wrap_problem_as_word_problem(problem)
        
        assert "word_problem_prompt" in word_problem.metadata
        assert word_problem.metadata["problem_style"].is_word_problem is True

    def test_wrap_with_reading_level(self):
        """Test wrapping with specific reading level."""
        problem = generate_linear_equation_problem(difficulty=2)
        word_problem = wrap_problem_as_word_problem(
            problem,
            reading_level="high_school"
        )
        
        style = word_problem.metadata["problem_style"]
        assert style.reading_level == "high_school"

    def test_wrap_with_context_tags(self):
        """Test wrapping with context tags."""
        problem = generate_linear_equation_problem(difficulty=2)
        word_problem = wrap_problem_as_word_problem(
            problem,
            context_tags=["money", "distance"]
        )
        
        style = word_problem.metadata["problem_style"]
        assert "money" in style.context_tags
        assert "distance" in style.context_tags

    def test_wrap_preserves_solution(self):
        """Test that wrapping preserves the original solution."""
        problem = generate_linear_equation_problem(difficulty=2)
        original_solution = problem.metadata["solution"]
        
        word_problem = wrap_problem_as_word_problem(problem)
        wrapped_solution = word_problem.metadata["solution"]
        
        assert wrapped_solution.final_answer_latex == original_solution.final_answer_latex
        assert wrapped_solution.sympy_verified == original_solution.sympy_verified


class TestProblemWordProblemSupport:
    """Test checking if problems support word problem mode."""

    def test_numeric_answer_supports_word_problem(self):
        """Test that numeric answer problems support word problem mode."""
        problem = generate_linear_equation_problem(difficulty=2)
        assert problem_supports_word_problem(problem) is True

    def test_expression_answer_support(self):
        """Test expression answer type (even if not generated yet)."""
        problem = generate_linear_equation_problem(difficulty=2)
        # For now, all are numeric, but test the abstraction
        assert problem_supports_word_problem(problem) is True
