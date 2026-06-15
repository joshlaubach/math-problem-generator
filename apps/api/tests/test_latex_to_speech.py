"""Tests for the LaTeX → spoken-English converter."""
import pytest

from agents.latex_to_speech import (
    SpeechConversionError,
    _SYSTEM_TEXT,
    _build_prompt,
    latex_to_speech,
)


@pytest.mark.asyncio
async def test_no_math_bypasses_llm():
    """Text without $ signs should be returned immediately without any LLM call."""
    text = "Great work! Let me show you the next step."
    result = await latex_to_speech(text)
    assert result == text


@pytest.mark.asyncio
async def test_conversion_failure_raises(monkeypatch):
    """When the LLM is unavailable the converter must raise, never emit
    regex-stripped token salad (the old fallback leaked raw LaTeX to TTS)."""
    import llm_anthropic_client

    async def raise_always(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(llm_anthropic_client, "_call_with_backoff", raise_always)

    with pytest.raises(SpeechConversionError):
        await latex_to_speech("Solve $x^2 = 4$.")


@pytest.mark.asyncio
async def test_empty_llm_output_raises(monkeypatch):
    """An empty rewrite is a failure — silence is handled by the caller, not
    by synthesizing nothing."""
    import llm_anthropic_client

    async def return_empty(*args, **kwargs):
        return "   "

    monkeypatch.setattr(llm_anthropic_client, "_call_with_backoff", return_empty)

    with pytest.raises(SpeechConversionError):
        await latex_to_speech("Solve $x^2 = 4$.")


@pytest.mark.asyncio
async def test_llm_output_passed_through(monkeypatch):
    """Successful conversions are stripped and returned as-is."""
    import llm_anthropic_client

    async def fake_convert(*args, **kwargs):
        return "  Solve x squared equals 4.  "

    monkeypatch.setattr(llm_anthropic_client, "_call_with_backoff", fake_convert)

    result = await latex_to_speech("Solve $x^2 = 4$.")
    assert result == "Solve x squared equals 4."


def test_build_prompt_contains_text():
    text = "Take $\\sqrt{x}$ of both sides."
    prompt = _build_prompt(text)
    assert text in prompt
    assert "say it aloud" in prompt


class TestSystemPromptRules:
    """The system prompt must encode the voice translation guide's core rules
    (these were the audit's failure cases — keep them pinned)."""

    def test_never_speak_token_rules_present(self):
        assert "dollar sign" in _SYSTEM_TEXT
        assert "backslash" in _SYSTEM_TEXT
        assert "underbrace" in _SYSTEM_TEXT.lower()

    def test_vertical_bar_disambiguation_present(self):
        assert "the modulus of z" in _SYSTEM_TEXT
        assert "the determinant of A" in _SYSTEM_TEXT
        assert "a divides b" in _SYSTEM_TEXT
        assert "such that" in _SYSTEM_TEXT

    def test_derivative_superscript_rule_present(self):
        assert "the nth derivative of f of x" in _SYSTEM_TEXT

    def test_matrix_inverse_rule_present(self):
        assert "inverse" in _SYSTEM_TEXT
        assert "X transpose X" in _SYSTEM_TEXT

    def test_distribution_naming_present(self):
        assert "standard normal" in _SYSTEM_TEXT

    def test_quantity_grouping_rule_present(self):
        assert "the quantity" in _SYSTEM_TEXT
        assert "open parenthesis" in _SYSTEM_TEXT  # as a prohibition

    def test_partial_vs_d_rule_present(self):
        assert "Never abbreviate a partial" in _SYSTEM_TEXT

    def test_no_invented_symbols_rule_present(self):
        assert "never invent symbols" in _SYSTEM_TEXT.lower()

    def test_jacobian_rule_present(self):
        assert "Jacobian" in _SYSTEM_TEXT

    def test_prosody_rules_present(self):
        assert "before every differential" in _SYSTEM_TEXT
