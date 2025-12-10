"""
LLM integration interfaces and dummy implementation.

Defines clean protocols for LLM-powered features like word problem generation
and hint generation. The dummy implementation uses templates and does not call
any external services, making it suitable for testing.

Future implementations can provide Claude, GPT, or other vendor integrations
without changing the main codebase.
"""

from typing import Protocol
import random


class LLMClient(Protocol):
    """
    Protocol for LLM-powered features.

    Implementations can use Claude, GPT, Llama, or other models.
    The protocol ensures a consistent interface regardless of vendor.
    """

    async def generate_word_problem(
        self,
        equation_latex: str,
        solution_latex: str,
        reading_level: str,
        context_tags: list[str],
    ) -> str:
        """
        Generate a word problem from an equation.

        Args:
            equation_latex: The equation in LaTeX format
            solution_latex: The solution in LaTeX format (e.g., "x = 5")
            reading_level: Grade level (e.g., "grade_8", "high_school")
            context_tags: List of contexts (e.g., ["money", "distance"])

        Returns:
            A natural language word problem statement
        """
        ...

    async def generate_hint(
        self,
        problem_latex: str,
        current_step_latex: str | None = None,
        error_description: str | None = None,
    ) -> str:
        """
        Generate a hint for a student stuck on a problem.

        Args:
            problem_latex: The problem statement in LaTeX
            current_step_latex: Optional current step the student is at
            error_description: Optional description of what went wrong

        Returns:
            A helpful hint to guide the student
        """
        ...

    async def evaluate_student_work(
        self,
        problem_latex: str,
        student_work_latex: str,
        expected_solution_latex: str,
    ) -> dict:
        """
        Evaluate student work and provide feedback.

        Args:
            problem_latex: The original problem
            student_work_latex: What the student wrote
            expected_solution_latex: The correct solution

        Returns:
            Dict with keys:
                - "is_correct": bool
                - "feedback": str (explanation of what's right/wrong)
                - "next_step_hint": str (if incorrect, suggestion for next step)
        """
        ...


class DummyLLMClient:
    """
    Dummy LLM client using templates.

    Returns hard-coded template responses without calling external APIs.
    Useful for testing and offline development.
    """

    # Word problem templates by context
    _MONEY_TEMPLATES = [
        "Sarah has ${amount}. After {action}, she has ${result}. {Question}",
        "A store sells items for ${price} each. {Person} buys {count} items. {Question}",
        "The price increases from ${old} to ${new}. What is the {change}? {Question}",
    ]

    _DISTANCE_TEMPLATES = [
        "Car A travels {dist1} miles. Car B travels {dist2} miles. {Question}",
        "The distance from A to B is {dist} miles. {Question}",
        "A runner covers {dist} km in {time} hours. {Question}",
    ]

    _COOKING_TEMPLATES = [
        "A recipe calls for {amount1} cups of flour. If {action}, {Question}",
        "The recipe serves {servings} people. To serve {new_servings}, {Question}",
    ]

    async def generate_word_problem(
        self,
        equation_latex: str,
        solution_latex: str,
        reading_level: str,
        context_tags: list[str],
    ) -> str:
        """
        Generate a simple template-based word problem.

        Returns a string with placeholders that indicate what a real LLM would fill.
        """
        context = context_tags[0] if context_tags else "general"

        if context == "money":
            template = random.choice(self._MONEY_TEMPLATES)
            return f"[Word Problem - Money Context]\n{template}\n\nEquation: {equation_latex}\nSolution: {solution_latex}"

        elif context == "distance":
            template = random.choice(self._DISTANCE_TEMPLATES)
            return f"[Word Problem - Distance Context]\n{template}\n\nEquation: {equation_latex}\nSolution: {solution_latex}"

        elif context == "cooking":
            template = random.choice(self._COOKING_TEMPLATES)
            return f"[Word Problem - Cooking Context]\n{template}\n\nEquation: {equation_latex}\nSolution: {solution_latex}"

        else:
            return f"[Word Problem - General Context]\nA problem involves {equation_latex}. Find the solution. Answer: {solution_latex}"

    async def generate_hint(
        self,
        problem_latex: str,
        current_step_latex: str | None = None,
        error_description: str | None = None,
    ) -> str:
        """
        Generate a simple hint based on the problem.

        Returns a template-based hint indicating where a real LLM would be used.
        """
        if error_description:
            return f"[Hint for error: {error_description}]\nTry checking your arithmetic. Review the definition of the operation you're using."

        if current_step_latex:
            return f"[Hint for step: {current_step_latex}]\nYou're on the right track! What's the next operation?"

        return f"[Hint for problem: {problem_latex}]\nStart by identifying what you know and what you need to find."

    async def evaluate_student_work(
        self,
        problem_latex: str,
        student_work_latex: str,
        expected_solution_latex: str,
    ) -> dict:
        """
        Evaluate work using simple template-based logic.

        A real LLM would compare work semantically.
        """
        # Dummy logic: check if student work contains the right answer
        is_correct = expected_solution_latex.strip() in student_work_latex

        if is_correct:
            return {
                "is_correct": True,
                "feedback": "Great work! Your solution is correct.",
                "next_step_hint": "Try a harder problem or review related concepts.",
            }
        else:
            return {
                "is_correct": False,
                "feedback": f"Not quite. The correct solution is {expected_solution_latex}.",
                "next_step_hint": "Review the steps and try again.",
            }


# Async compatibility helpers for sync contexts
class SyncDummyLLMClient:
    """
    Synchronous wrapper around DummyLLMClient for use in sync functions.

    FastAPI can handle both sync and async endpoints, so this allows
    easy integration without requiring async everywhere.
    """

    def __init__(self):
        self._async_client = DummyLLMClient()

    def generate_word_problem(
        self,
        equation_latex: str,
        solution_latex: str,
        reading_level: str,
        context_tags: list[str],
    ) -> str:
        """Generate word problem (sync version)."""
        # In a real implementation, you might use asyncio.run() or similar
        # For testing, just return the async version's result directly
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self._async_client.generate_word_problem(
                equation_latex, solution_latex, reading_level, context_tags
            )
        )

    def generate_hint(
        self,
        problem_latex: str,
        current_step_latex: str | None = None,
        error_description: str | None = None,
    ) -> str:
        """Generate hint (sync version)."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self._async_client.generate_hint(
                problem_latex, current_step_latex, error_description
            )
        )

    def evaluate_student_work(
        self,
        problem_latex: str,
        student_work_latex: str,
        expected_solution_latex: str,
    ) -> dict:
        """Evaluate work (sync version)."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self._async_client.evaluate_student_work(
                problem_latex, student_work_latex, expected_solution_latex
            )
        )
