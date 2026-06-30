"""
Anthropic Claude LLM client implementing the LLMClient Protocol.

Uses claude-sonnet-4-6 by default (configured via ANTHROPIC_MODEL env var).
All API calls are wrapped with exponential backoff (1s / 2s / 4s, max 3 retries).

Phase 12: this client replaces llm_openai_client.py once Anthropic is fully stable.

Prompt caching: _call_with_backoff and call_with_images both accept a structured
`system` parameter (list[dict] content blocks with cache_control) in addition to
the legacy plain-string form.  The Anthropic API requires the beta header
"prompt-caching-2024-07-31" when structured system blocks with cache_control are used.
Plain-string callers are unaffected — they follow the existing path unchanged.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional, Union

import httpx

from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, ANTHROPIC_FALLBACK_MODEL, LLM_API_TIMEOUT, LLM_MAX_TOKENS

_logger = logging.getLogger("llm")

# Last successful call's output token count. Read by session orchestrator for budget tracking.
# Updated under GIL — safe for single-threaded asyncio use.
_last_output_tokens: int = 0


def _get_client():
    """Lazily create the Anthropic async client."""
    try:
        import anthropic
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is not set. Check your .env file.")
        return anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY, timeout=httpx.Timeout(LLM_API_TIMEOUT))
    except ImportError as e:
        raise ImportError(
            "anthropic package is not installed. Run: pip install anthropic"
        ) from e


def _uses_cache_control(system: Union[str, list, None]) -> bool:
    """Return True if system is a structured list containing cache_control blocks."""
    if not isinstance(system, list):
        return False
    return any(isinstance(b, dict) and "cache_control" in b for b in system)


async def call_with_images(
    text_prompt: str,
    images: list[dict],
    system: Union[str, list, None] = None,
    max_tokens: int = 2048,
    retries: int = 3,
) -> str:
    """
    Call Claude with image content blocks followed by a text prompt.

    Args:
        text_prompt: The instruction / question appended after the image(s).
        images: List of {"data": base64_str, "media_type": "image/jpeg"|"image/png"|...}.
        system: Optional system prompt — plain str or structured list[dict] with
                cache_control blocks (from build_system_prompt(cacheable=True)).
        max_tokens: Max tokens in the response.
        retries: Retry attempts (exponential backoff: 1s / 2s / 4s).

    Returns:
        The text content of the first response block.
    """
    client = _get_client()
    delays = [1, 2, 4]

    content: list[dict] = []
    for img in images:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": img["media_type"],
                "data": img["data"],
            },
        })
    content.append({"type": "text", "text": text_prompt})

    messages = [{"role": "user", "content": content}]
    last_exc: Optional[Exception] = None

    # Use cache-enabled beta header when structured system blocks are present
    use_cache = _uses_cache_control(system)

    for attempt in range(retries):
        try:
            kwargs: dict = {
                "model": ANTHROPIC_MODEL,
                "max_tokens": max_tokens,
                "messages": messages,
            }
            if system:
                kwargs["system"] = system
            if use_cache:
                kwargs["extra_headers"] = {"anthropic-beta": "prompt-caching-2024-07-31"}
            response = await asyncio.wait_for(
                client.messages.create(**kwargs),
                timeout=LLM_API_TIMEOUT,
            )
            return response.content[0].text  # type: ignore[index]
        except asyncio.TimeoutError:
            last_exc = RuntimeError(f"LLM call timed out after {LLM_API_TIMEOUT}s")
            if attempt < retries - 1:
                delay = delays[min(attempt, len(delays) - 1)]
                await asyncio.sleep(delay)
        except Exception as exc:
            last_exc = exc
            if attempt < retries - 1:
                delay = delays[min(attempt, len(delays) - 1)]
                await asyncio.sleep(delay)

    raise RuntimeError(
        f"Claude Vision API failed after {retries} retries. Last error: {last_exc}"
    ) from last_exc


async def _call_with_backoff(
    messages: list[dict],
    system: Union[str, list, None] = None,
    max_tokens: int = LLM_MAX_TOKENS,
    retries: int = 3,
) -> str:
    """
    Call the Anthropic API with exponential backoff.

    Supports both plain-string system prompts (legacy) and structured system
    content blocks with cache_control (from build_system_prompt(cacheable=True)).
    When structured blocks are detected, the prompt-caching beta header is added.

    Args:
        messages: List of {role, content} dicts.
        system: Optional system prompt — plain str or structured list[dict] with
                cache_control blocks (from build_system_prompt(cacheable=True)).
        max_tokens: Max tokens in the response.
        retries: Max retry attempts (default 3).

    Returns:
        The text content of the first response block.

    Raises:
        Exception: if all retries are exhausted.
    """
    client = _get_client()
    global _last_output_tokens
    delays = [1, 2, 4]

    # Use cache-enabled beta header when structured system blocks are present
    use_cache = _uses_cache_control(system)

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
            if use_cache:
                kwargs["extra_headers"] = {"anthropic-beta": "prompt-caching-2024-07-31"}

            _t0 = time.monotonic()
            response = await asyncio.wait_for(
                client.messages.create(**kwargs),
                timeout=LLM_API_TIMEOUT,
            )
            _duration_ms = int((time.monotonic() - _t0) * 1000)
            _last_output_tokens = getattr(response.usage, "output_tokens", 0)
            _logger.info(
                "llm_call",
                extra={
                    "model": ANTHROPIC_MODEL,
                    "input_tokens": getattr(response.usage, "input_tokens", 0),
                    "output_tokens": _last_output_tokens,
                    "duration_ms": _duration_ms,
                },
            )
            return response.content[0].text  # type: ignore[index]

        except asyncio.TimeoutError:
            last_exc = RuntimeError(f"LLM call timed out after {LLM_API_TIMEOUT}s")
            if attempt < retries - 1:
                delay = delays[min(attempt, len(delays) - 1)]
                await asyncio.sleep(delay)
        except Exception as exc:
            last_exc = exc
            if attempt < retries - 1:
                delay = delays[min(attempt, len(delays) - 1)]
                await asyncio.sleep(delay)

    # After primary model exhaustion, try fallback model once before giving up
    if ANTHROPIC_FALLBACK_MODEL and ANTHROPIC_FALLBACK_MODEL != ANTHROPIC_MODEL:
        try:
            _logger.warning("degraded_mode", extra={"fallback_model": ANTHROPIC_FALLBACK_MODEL})
            fallback_kwargs: dict = {
                "model": ANTHROPIC_FALLBACK_MODEL,
                "max_tokens": max_tokens,
                "messages": messages,
            }
            if system:
                fallback_kwargs["system"] = system
            response = await asyncio.wait_for(
                client.messages.create(**fallback_kwargs),
                timeout=LLM_API_TIMEOUT,
            )
            _last_output_tokens = getattr(response.usage, "output_tokens", 0)
            return response.content[0].text  # type: ignore[index]
        except Exception:
            pass

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
        problem_context: str,
    ) -> str:
        """Generate a pedagogically graded hint. problem_context includes the
        hint number instruction and full problem statement, built by the caller."""
        prompt = (
            f"{problem_context}\n\n"
            "Write the hint in 1-2 sentences. Do NOT reveal the final answer."
        )
        return await _call_with_backoff(
            messages=[{"role": "user", "content": prompt}],
            system="You are a patient math tutor providing progressively specific hints without giving away the final answer.",
            max_tokens=200,
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

    def generate_hint(self, problem_context: str) -> str:
        return self._run(self._async.generate_hint(problem_context))

    def evaluate_student_work(self, problem_latex, student_work_latex, expected_solution_latex):
        return self._run(self._async.evaluate_student_work(problem_latex, student_work_latex, expected_solution_latex))
