"""
Anthropic Claude LLM client implementing the LLMClient Protocol.

Uses claude-sonnet-4-6 by default (configured via ANTHROPIC_MODEL env var).
All API calls are wrapped with exponential backoff (1s / 2s / 4s, max 3 retries).

Phase 12: this client replaces llm_openai_client.py once Anthropic is fully stable.
"""

from __future__ import annotations

import asyncio
import time
from typing import Optional

from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, LLM_API_TIMEOUT, LLM_MAX_TOKENS


def _get_client():
    """Lazily create the Anthropic async client."""
    try:
        import anthropic
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is not set. Check your .env file.")
        return anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    except ImportError as e:
        raise ImportError(
            "anthropic package is not installed. Run: pip install anthropic"
        ) from e


async def _call_with_backoff(
    messages: list[dict],
    system: Optional[str] = None,
    max_tokens: int = LLM_MAX_TOKENS,
    retries: int = 3,
) -> str:
    """
    Call the Anthropic API with exponential backoff.

    Args:
        messages: List of {role, content} dicts.
        system: Optional system prompt.
        max_tokens: Max tokens in the response.
        retries: Max retry attempts (default 3).

    Returns:
        The text content of the first response block.

    Raises:
        Exception: if all retries are exhausted.
    """
    client = _get_client()
    delays = [1, 2, 4]

    last_exc: Optional[Exception] = None
    for attempt in range(retries):
        try:
            kwargs: dict = {
                "model": ANTHROPIC_MODEL,
                "max_tokens": max_tokens,
                "messages": messages,
            }
            if system:
                kwargs["system"] = system

            response = await client.messages.create(**kwargs)
            return response.content[0].text  # type: ignore[index]

        except Exception as exc:
            last_exc = exc
            if attempt < retries - 1:
                delay = delays[min(attempt, len(delays) - 1)]
                await asyncio.sleep(delay)

    raise RuntimeError(
        f"Anthropic API failed after {retries} retries. Last error: {last_exc}"
    ) from last_exc


class AnthropicLLMClient:
    """
    Async Anthropic Claude client satisfying the LLMClient Protocol.
    All methods use _call_with_backoff for resilience.
    Raises ValueError at construction time if ANTHROPIC_API_KEY is not set.
    """

    def __init__(self) -> None:
        if not ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. "
                "Add it to apps/api/.env to use the Anthropic client."
            )

    async def generate_word_problem(
        self,
        equation_latex: str,
        solution_latex: str,
        reading_level: str,
        context_tags: list[str],
    ) -> str:
        context_str = ", ".join(context_tags) if context_tags else "general"
        prompt = (
            f"Generate a concise real-world word problem at {reading_level} reading level "
            f"in the context of: {context_str}.\n\n"
            f"The equation is: {equation_latex}\n"
            f"The solution is: {solution_latex}\n\n"
            "Return ONLY the word problem statement. Do not include the equation or solution."
        )
        return await _call_with_backoff(
            messages=[{"role": "user", "content": prompt}],
            system="You are a math teacher creating engaging word problems for students.",
        )

    async def generate_hint(
        self,
        problem_latex: str,
        current_step_latex: Optional[str] = None,
        error_description: Optional[str] = None,
    ) -> str:
        context = ""
        if current_step_latex:
            context += f"\nStudent's current step: {current_step_latex}"
        if error_description:
            context += f"\nDescribed error: {error_description}"

        prompt = (
            f"Give a helpful hint for this math problem WITHOUT revealing the answer:\n\n"
            f"Problem: {problem_latex}{context}\n\n"
            "Return ONLY the hint, one sentence."
        )
        return await _call_with_backoff(
            messages=[{"role": "user", "content": prompt}],
            system="You are a patient math tutor providing hints without giving away answers.",
            max_tokens=150,
        )

    async def evaluate_student_work(
        self,
        problem_latex: str,
        student_work_latex: str,
        expected_solution_latex: str,
    ) -> dict:
        prompt = (
            f"Problem: {problem_latex}\n"
            f"Student work: {student_work_latex}\n"
            f"Expected solution: {expected_solution_latex}\n\n"
            "Evaluate the student's work. Return JSON with keys: "
            '"is_correct" (bool), "feedback" (str), "next_step_hint" (str).'
        )
        raw = await _call_with_backoff(
            messages=[{"role": "user", "content": prompt}],
            system="You are a math teacher evaluating student work. Respond with valid JSON only.",
            max_tokens=300,
        )
        import json
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {
                "is_correct": False,
                "feedback": raw,
                "next_step_hint": "Review your work and try again.",
            }


class SyncAnthropicLLMClient:
    """
    Synchronous wrapper around AnthropicLLMClient for sync FastAPI endpoints.
    Uses asyncio.run() to bridge sync/async contexts.
    """

    def __init__(self) -> None:
        self._async = AnthropicLLMClient()

    def _run(self, coro):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, coro)
                    return future.result()
            return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)

    def generate_word_problem(self, equation_latex, solution_latex, reading_level, context_tags):
        return self._run(self._async.generate_word_problem(equation_latex, solution_latex, reading_level, context_tags))

    def generate_hint(self, problem_latex, current_step_latex=None, error_description=None):
        return self._run(self._async.generate_hint(problem_latex, current_step_latex, error_description))

    def evaluate_student_work(self, problem_latex, student_work_latex, expected_solution_latex):
        return self._run(self._async.evaluate_student_work(problem_latex, student_work_latex, expected_solution_latex))
