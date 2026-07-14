"""
Phase 2 skills-discovery tests: routing by problem type, context-budget caps,
fallback behavior, and cache-stable rendering.
"""

from __future__ import annotations

from types import SimpleNamespace

from skills import SKILLS, select_skills, skills_block
from skills.registry import MAX_SKILLS, TOKEN_BUDGET


def _session(topic_id="alg1_linear_two_step"):
    return SimpleNamespace(topic_id=topic_id, topic_ids=[topic_id])


def test_derivative_question_loads_calculus_skills():
    s = _session("calc1_derivatives_power_rule")
    picked = select_skills(
        s,
        "how do I differentiate this?",
        "Find the derivative of $f(x) = \\sin(3x^2)$.",
    )
    ids = [p.id for p in picked]
    assert "derivative_rules" in ids or "chain_rule" in ids
    assert len(picked) <= MAX_SKILLS


def test_cap_at_two_skills():
    s = _session("calc1_derivatives")
    # A statement that trips derivative, chain, integration, and trig probes
    picked = select_skills(
        s,
        "derivative and integral of sin?",
        "Differentiate $\\sin(x^2)$ then integrate the result. Use the chain rule.",
    )
    assert len(picked) <= MAX_SKILLS
    assert sum(p.token_cost for p in picked) <= TOKEN_BUDGET


def test_family_alone_does_not_load():
    """A calculus session with no keyword evidence stays on coarse guidance."""
    s = _session("calc1_limits_intro")
    picked = select_skills(s, "hi", "Evaluate the limit as x approaches 2 of x+1.")
    assert all(p.id != "factoring_quadratics" for p in picked)
    # No skill demands to load off family membership by itself
    for p in picked:
        assert p.pattern.search("Evaluate the limit as x approaches 2 of x+1.") or \
               p.pattern.search("hi")


def test_freeform_session_no_topic_still_matches_on_problem():
    s = SimpleNamespace(topic_id=None, topic_ids=[])
    picked = select_skills(
        s, "", "Factor the quadratic $x^2 + 5x + 6$ and find its roots."
    )
    assert any(p.id == "factoring_quadratics" for p in picked)


def test_message_only_keyword_too_weak():
    """One keyword in chat, nothing in the problem, wrong family → no load."""
    s = _session("geo_angles_intro")
    picked = select_skills(s, "is this like a derivative?", "Find the missing angle.")
    assert all(p.id != "derivative_rules" for p in picked)


def test_selection_is_deterministic():
    s = _session("calc1_derivatives")
    args = ("chain rule?", "Differentiate $\\cos(5x)$ using the chain rule.")
    a = [p.id for p in select_skills(s, *args)]
    b = [p.id for p in select_skills(s, *args)]
    assert a == b


def test_rendered_block_bytes_are_stable():
    """Same selection (any order) → identical bytes (prompt-cache safety)."""
    two = [SKILLS[0], SKILLS[1]]
    assert skills_block(two) == skills_block(list(reversed(two)))
    assert skills_block([]) is None


def test_all_skill_blocks_within_budget():
    for s in SKILLS:
        assert s.token_cost < TOKEN_BUDGET, s.id
        assert s.prompt_block.startswith("### Skill: ")


def test_prompt_assembler_inserts_skills_breakpoint():
    from agents.prompt_assembler import build_system_prompt

    block = skills_block([SKILLS[0]])
    out = build_system_prompt(role="SOCRATIC", context="ctx", skills_block=block,
                              cacheable=True)
    assert isinstance(out, list)
    skill_blocks = [b for b in out if "## Loaded Skills" in b.get("text", "")]
    assert len(skill_blocks) == 1
    assert skill_blocks[0].get("cache_control") == {"type": "ephemeral"}

    # Plain-string path includes it too
    out_str = build_system_prompt(role="SOCRATIC", context="ctx", skills_block=block,
                                  cacheable=False)
    assert "## Loaded Skills" in out_str
