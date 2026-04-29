# ADR-002: Claude Model Selection

**Date:** 2026-04-29  
**Status:** Accepted

## Context

The platform spec mandates `claude-sonnet-4-20250514` for all AI agents. This is an older model identifier that predates the Claude 4.x family (Opus 4.7, Sonnet 4.6, Haiku 4.5). Using a retired or non-existent model string would cause all agent calls to fail.

## Decision

Use `claude-sonnet-4-6` as the default model for all agents.

The model is configured via the `ANTHROPIC_MODEL` environment variable (default: `claude-sonnet-4-6`), allowing override without code changes:

```bash
# .env
ANTHROPIC_MODEL=claude-sonnet-4-6
```

All agents read from `settings.ANTHROPIC_MODEL` via the Anthropic client factory.

## Consequences

- Any agent can be switched to a different Claude model by changing the env var
- The pre-generation scripts and offline agents use the same var, so a single config change affects all call sites
- If Anthropic releases a newer Sonnet model, updating one env var upgrades all agents
- Deviation from the literal spec string `claude-sonnet-4-20250514` is intentional and recorded here
