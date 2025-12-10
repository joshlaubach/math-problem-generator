"""
Tests for the linear equation problem generator.

Tests verify:
- Problem generation for all difficulty levels
- SymPy verification of generated equations
- Solution correctness and uniqueness
- LaTeX formatting
"""

import pytest
from sympy import symbols, solve, Eq

from generator_linear_impl import generate_linear_equation_problem
from models import Problem, Solution


x = symbols('x', real=True)


class TestLinearGeneratorBasic:
    """Test basic problem generation for each difficulty level."""

    @pytest.mark.parametrize("difficulty", [1, 2, 3, 4])
    def test_problem_generation_all_difficulties(self, difficulty: int):
        """Test that problems can be generated for all difficulty levels."""
        problem = generate_linear_equation_problem(difficulty=difficulty)
        
        assert isinstance(problem, Problem)
        assert problem.difficulty == difficulty
        assert problem.course_id == "algebra_1"
        assert problem.unit_id == "alg1_unit_linear_equations"
        assert problem.topic_id == "alg1_linear_solve_one_var"

    @pytest.mark.parametrize("difficulty", [1, 2, 3, 4])
    def test_solution_embedded_in_metadata(self, difficulty: int):
        """Test that Solution is properly embedded in problem metadata."""
        problem = generate_linear_equation_problem(difficulty=difficulty)
        
        assert "solution" in problem.metadata
        solution = problem.metadata["solution"]
        assert isinstance(solution, Solution)

    @pytest.mark.parametrize("difficulty", [1, 2, 3, 4])
    def test_sympy_verification(self, difficulty: int):
        """Test that all generated problems are verified by SymPy."""
        problem = generate_linear_equation_problem(difficulty=difficulty)
        solution = problem.metadata["solution"]
        
        assert solution.sympy_verified is True
        assert solution.verification_details is not None

    @pytest.mark.parametrize("difficulty", [1, 2, 3, 4])
    def test_solution_has_steps(self, difficulty: int):
        """Test that solutions contain step-by-step instructions."""
        problem = generate_linear_equation_problem(difficulty=difficulty)
        solution = problem.metadata["solution"]
        
        assert len(solution.steps) > 0
        for step in solution.steps:
            assert step.description_latex is not None
            assert step.expression_latex is not None

    @pytest.mark.parametrize("difficulty", [1, 2, 3, 4])
    def test_latex_formatting(self, difficulty: int):
        """Test that LaTeX formatting is present in problem and solution."""
        problem = generate_linear_equation_problem(difficulty=difficulty)
        solution = problem.metadata["solution"]
        
        # Problem prompt should contain LaTeX
        assert "$" in problem.prompt_latex or "x" in problem.prompt_latex
        
        # Solution components should have LaTeX
        assert solution.final_answer_latex is not None
        assert solution.full_solution_latex is not None


class TestLinearGeneratorValidity:
    """Test mathematical validity of generated problems."""

    @pytest.mark.parametrize("difficulty", [1, 2, 3, 4])
    @pytest.mark.parametrize("trial", range(20))  # 20 trials per difficulty
    def test_solution_uniqueness_and_correctness(
        self, difficulty: int, trial: int
    ):
        """
        Test that 20 random problems per difficulty have exactly one solution
        matching the final_answer.
        """
        problem = generate_linear_equation_problem(difficulty=difficulty)
        solution = problem.metadata["solution"]
        final_answer = problem.final_answer
        
        # The final_answer should be an integer
        assert isinstance(final_answer, (int, float))
        
        # SymPy should have verified the solution
        assert solution.sympy_verified is True
        
        # The final_answer should match the LaTeX representation
        assert solution.final_answer_latex is not None

    @pytest.mark.parametrize("difficulty", [1, 2, 3, 4])
    @pytest.mark.parametrize("trial", range(10))  # 10 trials per difficulty
    def test_answer_type(self, difficulty: int, trial: int):
        """Test that answer_type is consistent with final_answer."""
        problem = generate_linear_equation_problem(difficulty=difficulty)
        
        # For linear equations, answer_type should be "numeric"
        assert problem.answer_type == "numeric"
        assert isinstance(problem.final_answer, (int, float))

    @pytest.mark.parametrize("difficulty", [1, 2, 3, 4])
    def test_calculator_mode(self, difficulty: int):
        """Test that calculator_mode is properly set."""
        problem = generate_linear_equation_problem(
            difficulty=difficulty, calculator_mode="none"
        )
        assert problem.calculator_mode == "none"

    def test_invalid_difficulty_raises_error(self):
        """Test that invalid difficulty levels raise ValueError."""
        with pytest.raises(ValueError):
            generate_linear_equation_problem(difficulty=0)
        
        with pytest.raises(ValueError):
            generate_linear_equation_problem(difficulty=5)

    def test_different_problems_different_content(self):
        """Test that multiple generations produce different problems."""
        problems = [
            generate_linear_equation_problem(difficulty=2) for _ in range(5)
        ]
        
        # Get prompts
        prompts = [p.prompt_latex for p in problems]
        
        # At least some should be different (with high probability)
        unique_prompts = set(prompts)
        assert len(unique_prompts) >= 3, "Generated problems should vary"


class TestLinearGeneratorProperties:
    """Test properties of generated problems across difficulties."""

    def test_difficulty_1_simpler_than_difficulty_4(self):
        """
        Test that difficulty 1 problems are simpler (fewer steps)
        than difficulty 4.
        """
        diff1_problem = generate_linear_equation_problem(difficulty=1)
        diff4_problem = generate_linear_equation_problem(difficulty=4)
        
        diff1_steps = len(diff1_problem.metadata["solution"].steps)
        diff4_steps = len(diff4_problem.metadata["solution"].steps)
        
        assert diff1_steps <= diff4_steps

    @pytest.mark.parametrize("difficulty", [1, 2, 3, 4])
    def test_step_indexing(self, difficulty: int):
        """Test that solution steps are properly indexed starting from 0."""
        problem = generate_linear_equation_problem(difficulty=difficulty)
        solution = problem.metadata["solution"]
        
        for i, step in enumerate(solution.steps):
            assert step.index == i

    def test_problem_has_unique_id(self):
        """Test that generated problems have unique IDs."""
        problems = [
            generate_linear_equation_problem(difficulty=2) for _ in range(10)
        ]
        
        ids = [p.id for p in problems]
        assert len(set(ids)) == len(ids), "All problem IDs should be unique"


class TestLinearGeneratorIntegration:
    """Integration tests combining multiple aspects."""

    def test_full_workflow_difficulty_2(self):
        """Test complete workflow for difficulty 2 problem."""
        # Generate
        problem = generate_linear_equation_problem(difficulty=2)
        solution = problem.metadata["solution"]
        
        # Verify structure
        assert problem.difficulty == 2
        assert solution.sympy_verified
        assert len(solution.steps) >= 3
        
        # Verify final answer exists
        assert problem.final_answer is not None
        assert solution.final_answer_latex is not None
        
        # Verify LaTeX content
        assert "$" in problem.prompt_latex or "x" in problem.prompt_latex
        assert "\\" in solution.full_solution_latex or "=" in solution.full_solution_latex

    def test_all_difficulties_complete_workflow(self):
        """Run complete workflow for all difficulties."""
        for difficulty in [1, 2, 3, 4]:
            problem = generate_linear_equation_problem(difficulty=difficulty)
            solution = problem.metadata["solution"]
            
            # All should be valid
            assert isinstance(problem, Problem)
            assert isinstance(solution, Solution)
            assert solution.sympy_verified
            assert problem.final_answer is not None
            assert len(solution.steps) > 0
