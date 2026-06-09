"""
Tests for agents/prompt_assembler.py

Covers:
- build_system_prompt() always includes CONSTITUTION + OUTPUT_CONSTRAINTS
- SOCRATIC output: never-reveal phrase, ends-with-? rule present
- deep=True injects deep guide; deep=False does not
- cache_control on static prefix, NOT on dynamic suffix
- Static prefix bytes are identical across roles (prerequisite for cache hit)
- DRAWING role returns valid JSON-schema instructions
- SUMMARY role returns per_topic_performance schema

Golden snapshots via syrupy (optional; tests degrade gracefully without it).
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_all_text(system) -> str:
    """Extract all text from a structured system prompt or plain string."""
    if isinstance(system, str):
        return system
    return "\n".join(block.get("text", "") for block in system if isinstance(block, dict))


def _get_static_prefix_text(system) -> str:
    """Return text of the first (cached) block only."""
    if isinstance(system, str):
        return system
    for block in system:
        if isinstance(block, dict) and "cache_control" in block:
            return block.get("text", "")
    return ""


def _has_cache_control_on_first_block(system) -> bool:
    if not isinstance(system, list):
        return False
    if not system:
        return False
    return "cache_control" in system[0]


def _blocks_with_cache_control(system) -> list:
    if not isinstance(system, list):
        return []
    return [b for b in system if isinstance(b, dict) and "cache_control" in b]


def _blocks_without_cache_control(system) -> list:
    if not isinstance(system, list):
        return []
    return [b for b in system if isinstance(b, dict) and "cache_control" not in b]


# ---------------------------------------------------------------------------
# Core invariants
# ---------------------------------------------------------------------------

class TestBuildSystemPromptInvariants:
    def test_constitution_always_present(self):
        from agents.prompt_assembler import build_system_prompt
        from agents.tutor_guide import CONSTITUTION
        for role in ("SOCRATIC", "LESSON", "OPENING", "DRAWING", "SUMMARY"):
            result = build_system_prompt(role=role)
            text = _get_all_text(result)
            # Check a distinctive phrase from CONSTITUTION
            assert "Never solve a problem completely" in text, (
                f"CONSTITUTION missing in role={role}"
            )

    def test_output_constraints_always_present(self):
        from agents.prompt_assembler import build_system_prompt
        for role in ("SOCRATIC", "LESSON", "DRAWING", "SUMMARY"):
            result = build_system_prompt(role=role)
            text = _get_all_text(result)
            assert "LaTeX" in text, f"OUTPUT_CONSTRAINTS missing in role={role}"
            assert "dollar signs" in text, f"OUTPUT_CONSTRAINTS missing in role={role}"

    def test_role_layer_present(self):
        from agents.prompt_assembler import build_system_prompt
        result = build_system_prompt(role="SOCRATIC")
        text = _get_all_text(result)
        assert "Socratic" in text

    def test_context_in_dynamic_suffix(self):
        from agents.prompt_assembler import build_system_prompt
        result = build_system_prompt(role="SOCRATIC", context="UNIQUE_CONTEXT_TOKEN_XYZ")
        text = _get_all_text(result)
        assert "UNIQUE_CONTEXT_TOKEN_XYZ" in text

    def test_snippet_injected_when_provided(self):
        from agents.prompt_assembler import build_system_prompt
        result = build_system_prompt(role="SOCRATIC", snippets=["anxiety"])
        text = _get_all_text(result)
        assert "Math Anxiety" in text or "anxiety" in text.lower()

    def test_snippet_not_injected_when_not_provided(self):
        from agents.prompt_assembler import build_system_prompt
        result = build_system_prompt(role="SOCRATIC", snippets=None)
        text = _get_all_text(result)
        # Should not have the anxiety playbook header
        assert "Playbook: Student Has Math Anxiety" not in text

    def test_unknown_role_degrades_gracefully(self):
        from agents.prompt_assembler import build_system_prompt
        result = build_system_prompt(role="NONEXISTENT_ROLE_XYZ")
        text = _get_all_text(result)
        # Should still have CONSTITUTION
        assert "Never solve a problem completely" in text

    def test_returns_list_when_cacheable_true(self):
        from agents.prompt_assembler import build_system_prompt
        result = build_system_prompt(role="SOCRATIC", cacheable=True)
        assert isinstance(result, list)

    def test_returns_str_when_cacheable_false(self):
        from agents.prompt_assembler import build_system_prompt
        result = build_system_prompt(role="SOCRATIC", cacheable=False)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Deep guide injection
# ---------------------------------------------------------------------------

class TestDeepGuideInjection:
    def test_deep_true_injects_guide(self):
        from agents.prompt_assembler import build_system_prompt
        result = build_system_prompt(role="SOCRATIC", deep=True, cacheable=False)
        # Guide text contains this distinctive header
        assert "The Complete Guide to AI Math Tutoring" in result or "Part One" in result

    def test_deep_false_does_not_inject_guide(self):
        from agents.prompt_assembler import build_system_prompt
        result = build_system_prompt(role="SOCRATIC", deep=False, cacheable=False)
        assert "The Complete Guide to AI Math Tutoring" not in result

    def test_deep_guide_gets_second_cache_breakpoint(self):
        from agents.prompt_assembler import build_system_prompt
        from agents.tutor_guide import get_deep_guide
        if not get_deep_guide():
            pytest.skip("Guide file not found")
        result = build_system_prompt(role="SOCRATIC", deep=True, cacheable=True)
        cached_blocks = _blocks_with_cache_control(result)
        # Should have at least 2 cached blocks: static prefix + deep guide
        assert len(cached_blocks) >= 2

    def test_without_deep_only_one_cache_breakpoint(self):
        from agents.prompt_assembler import build_system_prompt
        result = build_system_prompt(role="SOCRATIC", deep=False, cacheable=True)
        cached_blocks = _blocks_with_cache_control(result)
        assert len(cached_blocks) == 1


# ---------------------------------------------------------------------------
# Cache layout
# ---------------------------------------------------------------------------

class TestCacheLayout:
    def test_first_block_has_cache_control(self):
        from agents.prompt_assembler import build_system_prompt
        result = build_system_prompt(role="SOCRATIC", cacheable=True)
        assert _has_cache_control_on_first_block(result)

    def test_dynamic_suffix_block_has_no_cache_control(self):
        from agents.prompt_assembler import build_system_prompt
        result = build_system_prompt(role="SOCRATIC", context="my context", cacheable=True)
        # Last block should not have cache_control (it's the dynamic suffix)
        dynamic_blocks = _blocks_without_cache_control(result)
        assert dynamic_blocks, "Expected at least one uncached block for dynamic suffix"
        last_block = result[-1]
        assert "cache_control" not in last_block

    def test_static_prefix_identical_across_roles(self):
        """
        The static prefix bytes MUST be identical across call-sites — this is the
        prerequisite for a shared cache entry at Anthropic's end.
        """
        from agents.prompt_assembler import build_system_prompt
        roles = ["SOCRATIC", "LESSON", "DRAWING", "SUMMARY", "OPENING"]
        prefixes = []
        for role in roles:
            system = build_system_prompt(role=role, cacheable=True)
            if isinstance(system, list):
                first_cached = next(
                    (b.get("text", "") for b in system if "cache_control" in b), ""
                )
                prefixes.append(first_cached)

        assert len(set(prefixes)) == 1, (
            "Static prefix differs across roles — cache hits will be missed. "
            f"Distinct prefixes found: {len(set(prefixes))}"
        )

    def test_topic_guidance_in_dynamic_not_static(self):
        from agents.prompt_assembler import build_system_prompt
        from agents.tutor_guide import TOPIC_GUIDANCE
        guidance = TOPIC_GUIDANCE["algebra_1"]
        result = build_system_prompt(
            role="SOCRATIC", topic_guidance=guidance, cacheable=True
        )
        # Topic guidance should NOT appear in the first (cached) block
        static_text = _get_static_prefix_text(result)
        # Topic guidance key phrase that should only be in the dynamic suffix
        assert "Linear Equations" not in static_text, (
            "Topic guidance leaked into the static prefix — would break cache hits"
        )
        # But should appear in the full assembled prompt
        full_text = _get_all_text(result)
        assert "Linear Equations" in full_text


# ---------------------------------------------------------------------------
# Role-specific content checks
# ---------------------------------------------------------------------------

class TestRoleContent:
    def test_socratic_has_never_reveal_rule(self):
        from agents.prompt_assembler import build_system_prompt
        result = build_system_prompt(role="SOCRATIC")
        text = _get_all_text(result)
        assert "never reveal" in text.lower() or "never state" in text.lower() or \
               "never give the answer" in text.lower()

    def test_drawing_has_json_schema(self):
        from agents.prompt_assembler import build_system_prompt
        result = build_system_prompt(role="DRAWING")
        text = _get_all_text(result)
        assert '"chat_text"' in text
        assert '"annotation"' in text
        assert "x_hint" in text

    def test_summary_has_json_schema(self):
        from agents.prompt_assembler import build_system_prompt
        result = build_system_prompt(role="SUMMARY")
        text = _get_all_text(result)
        assert "per_topic_performance" in text
        assert "bullets" in text
        assert "practice_problems" in text

    def test_multiple_snippets_both_appear(self):
        from agents.prompt_assembler import build_system_prompt
        result = build_system_prompt(role="SOCRATIC", snippets=["anxiety", "frustration"])
        text = _get_all_text(result)
        assert "anxiety" in text.lower()
        assert "frustration" in text.lower() or "Frustrated" in text

    def test_topic_guidance_appears_in_text(self):
        from agents.prompt_assembler import build_system_prompt
        from agents.tutor_guide import TOPIC_GUIDANCE
        guidance = TOPIC_GUIDANCE["calculus"]
        result = build_system_prompt(role="SOCRATIC", topic_guidance=guidance, cacheable=False)
        assert "Calculus" in result


# ---------------------------------------------------------------------------
# Golden snapshots (optional — degrades if syrupy not installed)
# ---------------------------------------------------------------------------

try:
    import syrupy  # noqa: F401
    HAS_SYRUPY = True
except ImportError:
    HAS_SYRUPY = False


@pytest.mark.skipif(not HAS_SYRUPY, reason="syrupy not installed")
class TestGoldenSnapshots:
    def test_socratic_snapshot(self, snapshot):
        from agents.prompt_assembler import build_system_prompt
        result = build_system_prompt(role="SOCRATIC", cacheable=False)
        assert result == snapshot

    def test_lesson_snapshot(self, snapshot):
        from agents.prompt_assembler import build_system_prompt
        result = build_system_prompt(role="LESSON", cacheable=False)
        assert result == snapshot

    def test_drawing_snapshot(self, snapshot):
        from agents.prompt_assembler import build_system_prompt
        result = build_system_prompt(role="DRAWING", cacheable=False)
        assert result == snapshot

    def test_summary_snapshot(self, snapshot):
        from agents.prompt_assembler import build_system_prompt
        result = build_system_prompt(role="SUMMARY", cacheable=False)
        assert result == snapshot
