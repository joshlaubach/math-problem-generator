"""
Prompt assembler — single source of truth for building system prompts.

All six tutor call-sites route through build_system_prompt(), which assembles:

  Static, cacheable prefix (same bytes across all roles):
    CONSTITUTION + OUTPUT_CONSTRAINTS  [cache breakpoint 1]
    + DEEP_GUIDE                       [cache breakpoint 2, when deep=True]

  Dynamic suffix (uncached, varies per call-site):
    ROLE_LAYER + topic_guidance + context + snippets

Anthropic caches the static prefix so repeated turns in the same session
(and across sessions) share cached prompt tokens, reducing latency and cost.
ROLE must NOT be in the static prefix — it varies per call-site and would
create different bytes → cache misses across socratic/lesson/drawing etc.

When cacheable=True, returns a list of Anthropic content blocks with
cache_control attached to each static-prefix boundary.  When cacheable=False
(or for legacy callers that pass a plain string), returns a plain str.
"""
from __future__ import annotations

from typing import Optional

from agents.tutor_guide import (
    CONSTITUTION,
    OUTPUT_CONSTRAINTS,
    ROLE_LAYERS,
    SCENARIO_SNIPPETS,
    DEEP_GUIDE_HEADER,
    get_deep_guide,
)


def build_system_prompt(
    *,
    role: str,
    context: str = "",
    snippets: Optional[list[str]] = None,
    topic_guidance: Optional[str] = None,
    skills_block: Optional[str] = None,
    deep: bool = False,
    cacheable: bool = True,
) -> "str | list[dict]":
    """
    Assemble the system prompt for a tutor call.

    Args:
        role: Key into ROLE_LAYERS (e.g. "SOCRATIC", "LESSON", "DRAWING", "SUMMARY").
        context: Dynamic per-turn context (problem statement, session state summary, etc.).
                 Goes in the dynamic suffix — never cached.
        snippets: List of snippet keys from select_snippets(). Injected in the suffix.
        topic_guidance: Block from select_topic_guidance(). Injected in the suffix.
        deep: If True, the full guide is appended after the static prefix breakpoint.
        cacheable: If True, return a list[dict] of Anthropic content blocks with
                   cache_control on the static prefix boundary.  If False, return
                   a plain string (for callers that do not yet support structured system).

    Returns:
        str if cacheable=False, else list[dict] Anthropic content blocks.

    Cache layout (up to 3 breakpoints — max 4 allowed):
        Block 0: CONSTITUTION + OUTPUT_CONSTRAINTS       [cache_control]
        Block 1: DEEP_GUIDE (only when deep=True)        [cache_control]
        Block 2: skills_block (when skills matched)      [cache_control]
                 — bytes are deterministic per skill set (sorted by id),
                 so repeated turns on the same problem hit the cache
        Block 3: ROLE_LAYER + topic_guidance + context + snippets  (no cache — dynamic)
    """
    role_layer = ROLE_LAYERS.get(role, "")
    if not role_layer:
        # Graceful degradation: unknown role gets an empty role section
        role_layer = f"## Role: {role}\n"

    # Build static prefix (identical bytes across all roles — prerequisite for cache hit)
    static_prefix = CONSTITUTION + "\n" + OUTPUT_CONSTRAINTS

    # Build dynamic suffix
    suffix_parts: list[str] = [role_layer]
    if topic_guidance:
        suffix_parts.append(topic_guidance)
    if context:
        suffix_parts.append(f"## Session Context\n\n{context}")
    if snippets:
        injected = [SCENARIO_SNIPPETS[k] for k in snippets if k in SCENARIO_SNIPPETS]
        if injected:
            suffix_parts.append("## Active Playbook Snippets\n\n" + "\n".join(injected))

    dynamic_suffix = "\n".join(suffix_parts)

    if not cacheable:
        # Plain string path — backward compatible with all existing callers
        parts = [static_prefix]
        if deep:
            guide = get_deep_guide()
            if guide:
                parts.append(DEEP_GUIDE_HEADER + guide)
        if skills_block:
            parts.append(skills_block)
        parts.append(dynamic_suffix)
        return "\n\n".join(p for p in parts if p)

    # Structured content-block path with cache_control
    blocks: list[dict] = []

    # Block 0: static prefix — cache this across all roles and turns
    blocks.append({
        "type": "text",
        "text": static_prefix,
        "cache_control": {"type": "ephemeral"},
    })

    if deep:
        guide = get_deep_guide()
        if guide:
            # Block 1: deep guide — cache this within escalated stretches of a session
            blocks.append({
                "type": "text",
                "text": DEEP_GUIDE_HEADER + guide,
                "cache_control": {"type": "ephemeral"},
            })

    if skills_block:
        # Skills breakpoint: stable bytes per selected-skill set (Phase 2)
        blocks.append({
            "type": "text",
            "text": skills_block,
            "cache_control": {"type": "ephemeral"},
        })

    if dynamic_suffix.strip():
        # Final block: dynamic — never cache
        blocks.append({
            "type": "text",
            "text": dynamic_suffix,
        })

    return blocks
