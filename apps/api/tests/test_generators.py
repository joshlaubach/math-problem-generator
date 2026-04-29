"""
Tests for the generator registry and abstraction.
"""

import pytest

from generators import (
    get_generator_for_topic,
    list_registered_topics,
    register_generator,
)
from generators.base import ProblemGenerator
from models import Problem, CalculatorMode


class TestGeneratorRegistry:
    """Test the generator registration and lookup system."""

    def test_linear_generator_registered(self):
        """Test that LinearEquationGenerator is registered."""
        topics = list_registered_topics()
        assert "alg1_linear_solve_one_var" in topics

    def test_get_generator_for_linear_topic(self):
        """Test retrieving the linear equation generator."""
        generator = get_generator_for_topic("alg1_linear_solve_one_var")
        
        assert generator is not None
        assert isinstance(generator, ProblemGenerator)
        assert generator.topic_id == "alg1_linear_solve_one_var"

    def test_get_nonexistent_generator_raises_error(self):
        """Test that getting nonexistent generator raises error."""
        with pytest.raises(KeyError):
            get_generator_for_topic("nonexistent_topic")

    def test_generator_has_correct_ids(self):
        """Test that registered generator has correct course/unit/topic IDs."""
        generator = get_generator_for_topic("alg1_linear_solve_one_var")
        
        assert generator.course_id == "algebra_1"
        assert generator.unit_id == "alg1_unit_linear_equations"
        assert generator.topic_id == "alg1_linear_solve_one_var"

    def test_generator_generate_method(self):
        """Test that generator's generate() method works."""
        generator = get_generator_for_topic("alg1_linear_solve_one_var")
        problem = generator.generate(difficulty=2)
        
        assert isinstance(problem, Problem)
        assert problem.difficulty == 2


class TestGeneratorAbstraction:
    """Test the ProblemGenerator abstraction."""

    def test_generator_generates_valid_problems(self):
        """Test that a registered generator produces valid problems."""
        generator = get_generator_for_topic("alg1_linear_solve_one_var")
        
        for difficulty in [1, 2, 3, 4]:
            problem = generator.generate(difficulty=difficulty)
            
            assert isinstance(problem, Problem)
            assert problem.difficulty == difficulty
            assert "solution" in problem.metadata
            assert problem.metadata["solution"].sympy_verified is True

    def test_generator_supports_calculator_modes(self):
        """Test that generator supports different calculator modes."""
        generator = get_generator_for_topic("alg1_linear_solve_one_var")
        
        for mode in ["none", "scientific", "graphing"]:
            problem = generator.generate(difficulty=2, calculator_mode=mode)
            assert problem.calculator_mode == mode

    def test_generator_invalid_difficulty_raises_error(self):
        """Test that generator raises error for invalid difficulty."""
        generator = get_generator_for_topic("alg1_linear_solve_one_var")
        
        with pytest.raises(ValueError):
            generator.generate(difficulty=0)
        
        with pytest.raises(ValueError):
            generator.generate(difficulty=5)
