"""
Word problem mode for the problem generator.

Wraps existing equation generators to produce word problem versions
of the same underlying math, using natural language descriptions
instead of symbolic equations.

This module provides a non-breaking layer that:
- Preserves the exact underlying equation and solution
- Adds context/story around the problem
- Uses LLM capabilities optionally to generate natural language
"""

from dataclasses import dataclass, field

from models import Problem, Solution, CalculatorMode


@dataclass
class ProblemStyle:
    """Configuration for how a problem should be presented."""
    
    is_word_problem: bool = False
    reading_level: str = "grade_8"  # grade_8, high_school, college
    context_tags: list[str] = field(default_factory=list)  # e.g. ["money", "distance", "cooking"]


# Simple mapping of context tags to word problem scenarios
CONTEXT_TEMPLATES = {
    "money": {
        "grade_8": (
            "Sarah has {total} dollars. "
            "She buys {count} items at {unit_price} each. "
            "How much money does she have left?"
        ),
        "high_school": (
            "An investor buys {count} shares at {unit_price} per share. "
            "Their total investment is {total} dollars. "
            "Find the unit price."
        ),
    },
    "distance": {
        "grade_8": (
            "A car travels {distance1} miles at one speed, "
            "then {distance2} miles at another speed. "
            "The total time is {total_time} hours. "
            "Find the average speed."
        ),
    },
    "cooking": {
        "grade_8": (
            "A recipe calls for {ingredient1} cups of flour. "
            "You have {ingredient2} cups available. "
            "How much more flour do you need?"
        ),
    },
}


class WordProblemWrapper:
    """
    Wraps a Problem to add word problem context.

    Does NOT modify the underlying equation or solution;
    only wraps the prompt with natural language.
    """

    def __init__(
        self,
        problem: Problem,
        style: ProblemStyle | None = None
    ):
        """
        Initialize the wrapper.

        Args:
            problem: Original Problem with equation
            style: ProblemStyle configuration (optional)
        """
        self.problem = problem
        self.style = style or ProblemStyle()
        self._word_prompt = None

    @property
    def prompt_latex(self) -> str:
        """Return the original equation prompt (unchanged)."""
        return self.problem.prompt_latex

    @property
    def word_prompt(self) -> str:
        """
        Return a word problem version of the prompt.

        For now, this generates a simple template-based narrative.
        In production, this could use an LLM to generate more natural text.
        """
        if self._word_prompt is None:
            self._word_prompt = self._generate_word_problem()
        return self._word_prompt

    def _generate_word_problem(self) -> str:
        """
        Generate a simple word problem based on context tags.

        In a full implementation, this would:
        1. Extract parameters from the underlying equation
        2. Use an LLM to generate natural language
        3. Ensure the problem maps back to the same equation

        For now, return a simple template.
        """
        # Simple default word problem
        if self.style.context_tags:
            tag = self.style.context_tags[0]
            if tag in CONTEXT_TEMPLATES:
                template = CONTEXT_TEMPLATES[tag].get(
                    self.style.reading_level,
                    f"Solve the problem: {self.problem.prompt_latex}"
                )
                return template
        
        # Default: just use the equation
        return f"Solve: {self.problem.prompt_latex}"

    def to_problem_with_word_prompt(self) -> Problem:
        """
        Create a new Problem with the word problem prompt.

        Returns:
            A new Problem instance with word_problem_prompt in metadata
        """
        problem_copy = self.problem
        problem_copy.metadata["word_problem_prompt"] = self.word_prompt
        problem_copy.metadata["problem_style"] = self.style
        return problem_copy


def wrap_problem_as_word_problem(
    problem: Problem,
    reading_level: str = "grade_8",
    context_tags: list[str] | None = None
) -> Problem:
    """
    Convert an equation problem to a word problem.

    Args:
        problem: Original equation-based Problem
        reading_level: Reading level for the word problem
        context_tags: Context tags for scenario selection

    Returns:
        A Problem with additional word problem prompt in metadata
    """
    style = ProblemStyle(
        is_word_problem=True,
        reading_level=reading_level,
        context_tags=context_tags or []
    )
    
    wrapper = WordProblemWrapper(problem, style)
    return wrapper.to_problem_with_word_prompt()


def problem_supports_word_problem(problem: Problem) -> bool:
    """
    Check if a problem can be converted to word problem form.

    For now, all equation problems can be converted.
    Future implementations might have restrictions.

    Args:
        problem: The problem to check

    Returns:
        True if problem can have a word problem version
    """
    return problem.answer_type == "numeric"
