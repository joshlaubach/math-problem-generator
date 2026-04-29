"""
OpenAI LLM client implementation for word problem and hint generation.

Provides a real LLM integration via OpenAI API while maintaining
the vendor-agnostic LLMClient Protocol interface.
"""

import asyncio
import json
from typing import Optional

from llm_interfaces import LLMClient
from config import OPENAI_API_KEY, LLM_MODEL_NAME, LLM_API_TIMEOUT, LLM_MAX_TOKENS


class OpenAILLMClient(LLMClient):
    """
    OpenAI-based LLM client for generating word problems and hints.
    
    Implements the LLMClient Protocol using OpenAI's Chat Completions API.
    Requires OPENAI_API_KEY to be set in configuration.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = LLM_MODEL_NAME):
        """
        Initialize the OpenAI LLM client.
        
        Args:
            api_key: OpenAI API key. If None, uses OPENAI_API_KEY from config.
            model: Model name (e.g., "gpt-4-turbo-preview")
            
        Raises:
            ValueError: If no API key is provided and OPENAI_API_KEY is not configured
        """
        self.api_key = api_key or OPENAI_API_KEY
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not provided. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.model = model
        self.timeout = LLM_API_TIMEOUT
        self.max_tokens = LLM_MAX_TOKENS
        
        # Lazy import to avoid dependency if not using OpenAI
        try:
            import openai
            openai.api_key = self.api_key
            self.client = openai.AsyncOpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError(
                "openai package not installed. Install with: pip install openai"
            )

    async def generate_word_problem(self, context: str) -> str:
        """
        Generate a word problem using OpenAI's GPT.
        
        Args:
            context: Context information for problem generation, should include:
                - Equation in LaTeX format
                - Solution
                - Reading level (optional)
                - Context tags (optional)
        
        Returns:
            A generated word problem as plain text
            
        Raises:
            Exception: If the OpenAI API call fails
        """
        prompt = self._build_word_problem_prompt(context)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that creates engaging math word problems "
                                   "for students. Problems should be clear, realistic, and solvable.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI API error during word problem generation: {e}")

    async def generate_hint(self, problem_context: str) -> str:
        """
        Generate a step-by-step hint using OpenAI's GPT.
        
        Args:
            problem_context: Context about the problem, current progress, and errors
        
        Returns:
            A helpful hint that guides without revealing the answer
            
        Raises:
            Exception: If the OpenAI API call fails
        """
        prompt = self._build_hint_prompt(problem_context)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful math tutor. Provide hints that guide students "
                                   "toward the next step without directly revealing the answer. "
                                   "Focus on explaining the concept or the strategy to try.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=300,
                timeout=self.timeout,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI API error during hint generation: {e}")

    async def evaluate_student_work(
        self, problem_latex: str, student_answer: str, correct_answer: str
    ) -> str:
        """
        Evaluate student's work and provide feedback.
        
        Args:
            problem_latex: The original problem in LaTeX
            student_answer: Student's submitted answer
            correct_answer: The correct answer
        
        Returns:
            Concise feedback on the student's work
            
        Raises:
            Exception: If the OpenAI API call fails
        """
        prompt = self._build_evaluation_prompt(problem_latex, student_answer, correct_answer)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful math tutor evaluating student work. "
                                   "Provide constructive feedback that is encouraging but honest.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=200,
                timeout=self.timeout,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI API error during evaluation: {e}")

    @staticmethod
    def _build_word_problem_prompt(context: str) -> str:
        """Build a prompt for word problem generation."""
        return (
            f"Create an engaging word problem that leads to the following equation:\n"
            f"\n{context}\n\n"
            f"Requirements:\n"
            f"- The problem should be realistic and age-appropriate\n"
            f"- It should clearly lead to the given equation\n"
            f"- Use specific numbers and realistic scenarios\n"
            f"- Make it interesting but not overly complicated\n"
            f"- Do NOT include the solution"
        )

    @staticmethod
    def _build_hint_prompt(problem_context: str) -> str:
        """Build a prompt for hint generation."""
        return (
            f"Provide a helpful hint for the following math problem:\n\n"
            f"{problem_context}\n\n"
            f"Guidelines for your hint:\n"
            f"- Guide toward the NEXT step, not the final answer\n"
            f"- Explain the strategy or concept to try\n"
            f"- Be encouraging and supportive\n"
            f"- Keep it concise (1-2 sentences)\n"
            f"- Do NOT directly reveal the answer"
        )

    @staticmethod
    def _build_evaluation_prompt(
        problem_latex: str, student_answer: str, correct_answer: str
    ) -> str:
        """Build a prompt for answer evaluation."""
        return (
            f"Evaluate the student's work on this math problem:\n\n"
            f"Problem: {problem_latex}\n"
            f"Student's answer: {student_answer}\n"
            f"Correct answer: {correct_answer}\n\n"
            f"Provide brief, constructive feedback (2-3 sentences) that:\n"
            f"- Is encouraging\n"
            f"- Identifies what went well or what needs adjustment\n"
            f"- Suggests the next step if incorrect"
        )


class SyncOpenAILLMClient:
    """
    Synchronous wrapper for OpenAILLMClient for use in sync contexts like FastAPI.
    
    Runs async methods in a new event loop, allowing async OpenAI calls
    to work in synchronous FastAPI endpoints.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = LLM_MODEL_NAME):
        """Initialize with an underlying OpenAILLMClient."""
        self.client = OpenAILLMClient(api_key=api_key, model=model)

    def generate_word_problem(self, context: str) -> str:
        """Synchronous wrapper for generate_word_problem."""
        return asyncio.run(self.client.generate_word_problem(context))

    def generate_hint(self, problem_context: str) -> str:
        """Synchronous wrapper for generate_hint."""
        return asyncio.run(self.client.generate_hint(problem_context))

    def evaluate_student_work(
        self, problem_latex: str, student_answer: str, correct_answer: str
    ) -> str:
        """Synchronous wrapper for evaluate_student_work."""
        return asyncio.run(
            self.client.evaluate_student_work(problem_latex, student_answer, correct_answer)
        )
