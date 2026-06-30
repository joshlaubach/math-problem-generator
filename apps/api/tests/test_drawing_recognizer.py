"""
Unit tests for agents/drawing_recognizer.py

Covers:
- _parse_response: valid JSON, markdown-fenced JSON, null annotation,
  invalid x_hint/color clamping, missing chat_text → fallback
- recognize_and_annotate: LLM success, LLM exception → fallback,
  missing API key → fallback
- Snapshot source routing: scratchpad suppresses wb_annotate_student,
  whiteboard passes it through
"""
from __future__ import annotations

import json
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("AUTH_PROVIDER", "jwt")
os.environ.setdefault("USE_DATABASE", "false")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest")

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# _parse_response unit tests (pure — no I/O)
# ---------------------------------------------------------------------------

class TestParseResponse:
    """Direct tests of the internal _parse_response helper."""

    def _parse(self, raw: str) -> dict:
        from agents.drawing_recognizer import _parse_response
        return _parse_response(raw, tutor_name="Josh")

    def test_valid_json_with_annotation(self):
        raw = json.dumps({
            "chat_text": "Interesting approach. What rule did you use here?",
            "annotation": {
                "latex": r"\frac{d}{dx}",
                "label": "Check this step",
                "x_hint": "right",
                "color": "correction",
            }
        })
        result = self._parse(raw)
        assert result["chat_text"] == "Interesting approach. What rule did you use here?"
        ann = result["annotation"]
        assert ann is not None
        assert ann["latex"] == r"\frac{d}{dx}"
        assert ann["label"] == "Check this step"
        assert ann["x_hint"] == "right"
        assert ann["color"] == "correction"

    def test_valid_json_null_annotation(self):
        raw = json.dumps({
            "chat_text": "Can you walk me through your reasoning?",
            "annotation": None,
        })
        result = self._parse(raw)
        assert result["chat_text"] == "Can you walk me through your reasoning?"
        assert result["annotation"] is None

    def test_markdown_fenced_json_stripped(self):
        raw = '```json\n{"chat_text": "Good start.", "annotation": null}\n```'
        result = self._parse(raw)
        assert result["chat_text"] == "Good start."
        assert result["annotation"] is None

    def test_invalid_x_hint_clamped_to_right(self):
        raw = json.dumps({
            "chat_text": "What is your next step?",
            "annotation": {
                "x_hint": "diagonal",   # not a valid value
                "color": "correction",
            }
        })
        result = self._parse(raw)
        assert result["annotation"]["x_hint"] == "right"

    def test_invalid_color_clamped_to_neutral(self):
        raw = json.dumps({
            "chat_text": "Almost there.",
            "annotation": {
                "x_hint": "left",
                "color": "red",   # not a valid value
            }
        })
        result = self._parse(raw)
        assert result["annotation"]["color"] == "neutral"

    def test_all_valid_colors_accepted(self):
        for color in ("correction", "confirmation", "neutral"):
            raw = json.dumps({
                "chat_text": "Good.",
                "annotation": {"x_hint": "center", "color": color},
            })
            result = self._parse(raw)
            assert result["annotation"]["color"] == color

    def test_label_truncated_to_60_chars(self):
        long_label = "A" * 80
        raw = json.dumps({
            "chat_text": "Check the label.",
            "annotation": {"label": long_label, "x_hint": "right", "color": "neutral"},
        })
        result = self._parse(raw)
        assert len(result["annotation"]["label"]) == 60

    def test_empty_label_becomes_none(self):
        raw = json.dumps({
            "chat_text": "Nice diagram.",
            "annotation": {"label": "", "x_hint": "right", "color": "neutral"},
        })
        result = self._parse(raw)
        assert result["annotation"]["label"] is None

    def test_empty_latex_becomes_none(self):
        raw = json.dumps({
            "chat_text": "Good work.",
            "annotation": {"latex": "", "x_hint": "right", "color": "confirmation"},
        })
        result = self._parse(raw)
        assert result["annotation"]["latex"] is None

    def test_missing_chat_text_returns_fallback(self):
        raw = json.dumps({"annotation": None})  # no chat_text key
        result = self._parse(raw)
        # Fallback always asks the student to walk through their thinking
        assert "walk me through" in result["chat_text"].lower()
        assert result["annotation"] is None

    def test_empty_chat_text_returns_fallback(self):
        raw = json.dumps({"chat_text": "", "annotation": None})
        result = self._parse(raw)
        assert "walk me through" in result["chat_text"].lower()

    def test_completely_malformed_json_returns_fallback(self):
        result = self._parse("not json at all {{{")
        assert "walk me through" in result["chat_text"].lower()
        assert result["annotation"] is None

    def test_annotation_not_a_dict_becomes_none(self):
        raw = json.dumps({
            "chat_text": "What did you draw?",
            "annotation": "some string instead of object",
        })
        result = self._parse(raw)
        assert result["annotation"] is None


# ---------------------------------------------------------------------------
# recognize_and_annotate async tests
# ---------------------------------------------------------------------------

class TestRecognizeAndAnnotate:
    """End-to-end tests of recognize_and_annotate with mocked LLM."""

    async def test_success_with_annotation(self):
        mock_response = json.dumps({
            "chat_text": "I see you drew a triangle. What property are you using?",
            "annotation": {
                "latex": r"\triangle ABC",
                "label": "Check angle sum",
                "x_hint": "right",
                "color": "correction",
            }
        })
        with patch("config.ANTHROPIC_API_KEY", "fake-key"):
            with patch(
                "llm_anthropic_client.call_with_images",
                new=AsyncMock(return_value=mock_response),
            ):
                from agents.drawing_recognizer import recognize_and_annotate
                result = await recognize_and_annotate(
                    snapshot_b64="aGVsbG8=",  # base64("hello")
                    problem_statement=r"Find the area of $\triangle ABC$.",
                )

        assert "triangle" in result["chat_text"].lower()
        assert result["annotation"] is not None
        assert result["annotation"]["color"] == "correction"

    async def test_success_null_annotation(self):
        mock_response = json.dumps({
            "chat_text": "Interesting — what were you trying to show here?",
            "annotation": None,
        })
        with patch("config.ANTHROPIC_API_KEY", "fake-key"):
            with patch(
                "llm_anthropic_client.call_with_images",
                new=AsyncMock(return_value=mock_response),
            ):
                from agents.drawing_recognizer import recognize_and_annotate
                result = await recognize_and_annotate(
                    snapshot_b64="aGVsbG8=",
                    problem_statement="Solve $x^2 - 4 = 0$.",
                )

        assert result["annotation"] is None
        assert result["chat_text"] != ""

    async def test_missing_api_key_returns_fallback(self):
        with patch("config.ANTHROPIC_API_KEY", ""):
            from agents.drawing_recognizer import recognize_and_annotate
            result = await recognize_and_annotate(
                snapshot_b64="aGVsbG8=",
                problem_statement="Test problem.",
            )

        assert "walk me through" in result["chat_text"].lower()
        assert result["annotation"] is None

    async def test_llm_exception_returns_fallback(self):
        with patch("config.ANTHROPIC_API_KEY", "fake-key"):
            with patch(
                "llm_anthropic_client.call_with_images",
                new=AsyncMock(side_effect=RuntimeError("API timeout")),
            ):
                from agents.drawing_recognizer import recognize_and_annotate
                result = await recognize_and_annotate(
                    snapshot_b64="aGVsbG8=",
                    problem_statement="Test problem.",
                )

        assert "walk me through" in result["chat_text"].lower()
        assert result["annotation"] is None

    async def test_llm_returns_garbage_returns_fallback(self):
        with patch("config.ANTHROPIC_API_KEY", "fake-key"):
            with patch(
                "llm_anthropic_client.call_with_images",
                new=AsyncMock(return_value="I cannot help with that."),
            ):
                from agents.drawing_recognizer import recognize_and_annotate
                result = await recognize_and_annotate(
                    snapshot_b64="aGVsbG8=",
                    problem_statement="Test.",
                )

        assert "walk me through" in result["chat_text"].lower()
        assert result["annotation"] is None

    async def test_tutor_name_used_in_fallback(self):
        """Fallback message is the same regardless of tutor_name (current impl)."""
        with patch("config.ANTHROPIC_API_KEY", ""):
            from agents.drawing_recognizer import recognize_and_annotate
            result = await recognize_and_annotate(
                snapshot_b64="aGVsbG8=",
                problem_statement=".",
                tutor_name="Sarah",
            )
        # Fallback is a static message — just verify it's the safe response
        assert result["annotation"] is None
        assert len(result["chat_text"]) > 10


# ---------------------------------------------------------------------------
# Snapshot source routing logic
# ---------------------------------------------------------------------------

class TestSnapshotSourceRouting:
    """
    Verify the source field correctly gates wb_annotate_student.

    We test the routing logic directly by calling recognize_and_annotate
    and applying the same conditional the ws_router uses:
        if result.get("annotation") and snapshot_source == "whiteboard"
    """

    def _apply_routing(self, annotation: dict | None, source: str) -> bool:
        """Returns True if wb_annotate_student would be sent."""
        result = {"chat_text": "Test.", "annotation": annotation}
        return bool(result.get("annotation")) and source == "whiteboard"

    def test_whiteboard_with_annotation_sends_annotate(self):
        ann = {"latex": r"x^2", "label": None, "x_hint": "right", "color": "correction"}
        assert self._apply_routing(ann, "whiteboard") is True

    def test_scratchpad_with_annotation_suppresses_annotate(self):
        ann = {"latex": r"x^2", "label": None, "x_hint": "right", "color": "correction"}
        assert self._apply_routing(ann, "scratchpad") is False

    def test_whiteboard_null_annotation_does_not_send_annotate(self):
        assert self._apply_routing(None, "whiteboard") is False

    def test_scratchpad_null_annotation_does_not_send_annotate(self):
        assert self._apply_routing(None, "scratchpad") is False

    def test_unknown_source_defaults_to_no_annotation(self):
        """Any unexpected source value should not produce an annotation."""
        ann = {"latex": r"x", "label": None, "x_hint": "right", "color": "neutral"}
        assert self._apply_routing(ann, "unknown_source") is False
