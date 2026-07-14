"""
Phase 3 MCP-registry tests: routing, graceful fallback, circuit breaker,
and the no-more-trust verifier contract. External calls are mocked — the
flow must never depend on a live Wolfram/GeoGebra endpoint.
"""

from __future__ import annotations

import pytest

import mcp_registry
from mcp_registry import (
    Backend,
    BREAKER_THRESHOLD,
    _parse_equality_verdict,
    maybe_render_scene,
    wolfram_is_equal,
)


@pytest.fixture(autouse=True)
def _fresh_registry(monkeypatch):
    monkeypatch.delenv("WOLFRAM_APP_ID", raising=False)
    monkeypatch.delenv("WOLFRAM_MCP_URL", raising=False)
    monkeypatch.delenv("GEOGEBRA_MCP_URL", raising=False)
    mcp_registry.reset_registry()
    yield
    mcp_registry.reset_registry()


# ── Verdict parsing (strict — ambiguity must be None) ────────────────────────

@pytest.mark.parametrize("text,expected", [
    ("Yes, they are equal.", True),
    ("yes", True),
    ("The two expressions are equal", True),
    ("No, these are not equal.", False),
    ("no", False),
    ("The expressions are not equivalent", False),
    ("", None),
    ("It depends on the domain of x", None),
])
def test_parse_equality_verdict(text, expected):
    assert _parse_equality_verdict(text) is expected


# ── Unconfigured → None, flow keeps local behavior ───────────────────────────

@pytest.mark.asyncio
async def test_wolfram_unconfigured_returns_none():
    assert await wolfram_is_equal("1/2", "0.5") is None


@pytest.mark.asyncio
async def test_geogebra_unconfigured_falls_back():
    scene = [{"kind": "point", "x": i, "y": i} for i in range(10)]
    assert await maybe_render_scene(scene) is None


@pytest.mark.asyncio
async def test_simple_scene_never_routes_to_geogebra(monkeypatch):
    """Below the complexity threshold, Mafs wins even with a healthy backend."""
    monkeypatch.setenv("GEOGEBRA_MCP_URL", "http://localhost:9999/mcp")
    mcp_registry.reset_registry()
    b = mcp_registry.get_backend("geogebra")
    b.record_success()
    called = []

    async def fake_call(*a, **k):
        called.append(1)

    monkeypatch.setattr(mcp_registry, "_mcp_call", fake_call)
    scene = [{"kind": "point", "x": 0, "y": 0}] * 3
    assert await maybe_render_scene(scene) is None
    assert called == []


# ── Circuit breaker ───────────────────────────────────────────────────────────

def test_breaker_opens_after_threshold():
    b = Backend(name="x", kind="rest", capabilities=frozenset({"verify"}),
                url="http://x", configured=True)
    assert b.available()
    for _ in range(BREAKER_THRESHOLD):
        b.record_failure("boom")
    assert not b.available()
    b.record_success()
    assert b.available()


@pytest.mark.asyncio
async def test_wolfram_rest_failure_trips_breaker_then_none(monkeypatch):
    monkeypatch.setenv("WOLFRAM_APP_ID", "TESTID")
    mcp_registry.reset_registry()

    class FailClient:
        def __init__(self, *a, **k): ...
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, *a, **k):
            raise RuntimeError("network down")

    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", FailClient)

    for _ in range(BREAKER_THRESHOLD):
        assert await wolfram_is_equal("a", "b") is None
    assert not mcp_registry.get_backend("wolfram").available()
    # Breaker open → short-circuits without touching the network
    assert await wolfram_is_equal("a", "b") is None


@pytest.mark.asyncio
async def test_wolfram_rest_yes_verdict(monkeypatch):
    monkeypatch.setenv("WOLFRAM_APP_ID", "TESTID")
    mcp_registry.reset_registry()

    class OkResp:
        status_code = 200
        text = "Yes, (1/2) and (0.5) are equal."

    class OkClient:
        def __init__(self, *a, **k): ...
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, *a, **k): return OkResp()

    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", OkClient)
    assert await wolfram_is_equal("1/2", "0.5") is True
    assert mcp_registry.get_backend("wolfram").healthy is True


# ── Answer checker integration: Wolfram consulted only on parse failure ──────

@pytest.mark.asyncio
async def test_answer_checker_uses_wolfram_on_parse_failure(monkeypatch):
    from agents import answer_checker

    async def fake_equal(a, b):
        return True

    monkeypatch.setattr(mcp_registry, "wolfram_is_equal", fake_equal)
    r = await answer_checker.check(r"\begin{matrix}1\\2\end{matrix}", "unparseable~~")
    assert r.correct is True
    assert "Wolfram" in (r.partial_credit_reason or "")


@pytest.mark.asyncio
async def test_answer_checker_parse_failure_without_wolfram(monkeypatch):
    from agents import answer_checker

    async def fake_none(a, b):
        return None

    monkeypatch.setattr(mcp_registry, "wolfram_is_equal", fake_none)
    r = await answer_checker.check(r"\begin{matrix}1\\2\end{matrix}", "unparseable~~")
    assert r.correct is False
    assert "parse" in (r.partial_credit_reason or "").lower()


# ── Verifier: trust-on-parse-failure is dead ─────────────────────────────────

@pytest.mark.asyncio
async def test_verifier_no_longer_trusts_unparseable(monkeypatch):
    from agents import verifier

    async def fake_none(expr):
        return None

    monkeypatch.setattr(mcp_registry, "wolfram_expression_valid", fake_none)
    result = await verifier.verify("Solve something", "@@@not-math@@@", "numeric")
    assert result.verified is False
    assert "regenerate" in result.reason


@pytest.mark.asyncio
async def test_verifier_accepts_wolfram_validated(monkeypatch):
    from agents import verifier

    async def fake_yes(expr):
        return True

    monkeypatch.setattr(mcp_registry, "wolfram_expression_valid", fake_yes)
    result = await verifier.verify("Compute", "@@@not-math@@@", "numeric")
    assert result.verified is True
    assert "Wolfram" in result.reason
