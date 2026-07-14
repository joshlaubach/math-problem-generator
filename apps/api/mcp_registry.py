"""
MCP backend registry — verification and visualization routing (Phase 3).

Backends:
  sympy    — in-process CAS. Always first: no network hop can beat it.
  wolfram  — verification fallback for expressions SymPy cannot parse.
             Speaks MCP when WOLFRAM_MCP_URL is set, else Wolfram|Alpha's
             LLM API over REST when WOLFRAM_APP_ID is set.
  geogebra — visualization backend for complex constructions, MCP only
             (GEOGEBRA_MCP_URL). No official server exists today, so the
             DESIGNED default is: unconfigured → every scene renders on the
             local Mafs path. The flow never breaks without it.

Rules:
  - Hard time budget per external call (2.5s verify / 4s render) — these run
    on answer_submit/generation, never inside the STT→LLM→TTS turn path.
  - Circuit breaker: 3 consecutive failures opens a backend for 60s.
  - Every public function degrades to None; callers keep their local behavior.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

VERIFY_TIMEOUT_S = 2.5
RENDER_TIMEOUT_S = 4.0
PROBE_TIMEOUT_S = 3.0
BREAKER_THRESHOLD = 3
BREAKER_OPEN_S = 60.0


@dataclass
class Backend:
    name: str
    kind: str                     # "inprocess" | "mcp" | "rest"
    capabilities: frozenset
    url: Optional[str] = None
    configured: bool = False
    healthy: Optional[bool] = None   # None = never probed
    tools: list = field(default_factory=list)
    last_error: Optional[str] = None
    _failures: int = 0
    _open_until: float = 0.0

    def available(self) -> bool:
        if not self.configured:
            return False
        if time.monotonic() < self._open_until:
            return False
        return self.healthy is not False or self._failures < BREAKER_THRESHOLD

    def record_success(self) -> None:
        self._failures = 0
        self._open_until = 0.0
        self.healthy = True
        self.last_error = None

    def record_failure(self, err: str) -> None:
        self._failures += 1
        self.last_error = err[:300]
        if self._failures >= BREAKER_THRESHOLD:
            self.healthy = False
            self._open_until = time.monotonic() + BREAKER_OPEN_S
            logger.warning("MCP backend %s circuit OPEN for %ss (%s)",
                           self.name, BREAKER_OPEN_S, err[:120])


def _build_registry() -> dict[str, Backend]:
    wolfram_mcp = os.getenv("WOLFRAM_MCP_URL", "").strip()
    wolfram_appid = os.getenv("WOLFRAM_APP_ID", "").strip()
    geogebra_mcp = os.getenv("GEOGEBRA_MCP_URL", "").strip()
    return {
        "sympy": Backend(
            name="sympy", kind="inprocess", capabilities=frozenset({"verify"}),
            configured=True, healthy=True,
        ),
        "wolfram": Backend(
            name="wolfram",
            kind="mcp" if wolfram_mcp else "rest",
            capabilities=frozenset({"verify"}),
            url=wolfram_mcp or ("https://www.wolframalpha.com/api/v1/llm-api"
                                if wolfram_appid else None),
            configured=bool(wolfram_mcp or wolfram_appid),
        ),
        "geogebra": Backend(
            name="geogebra", kind="mcp", capabilities=frozenset({"visualize"}),
            url=geogebra_mcp or None,
            configured=bool(geogebra_mcp),
        ),
    }


_REGISTRY: dict[str, Backend] = _build_registry()


def reset_registry() -> None:
    """Re-read env config (tests / config reload)."""
    global _REGISTRY
    _REGISTRY = _build_registry()


def get_backend(name: str) -> Optional[Backend]:
    return _REGISTRY.get(name)


def status() -> dict:
    return {
        name: {
            "kind": b.kind,
            "configured": b.configured,
            "healthy": b.healthy,
            "available": b.available(),
            "capabilities": sorted(b.capabilities),
            "tools": [t for t in b.tools][:20],
            "last_error": b.last_error,
        }
        for name, b in _REGISTRY.items()
    }


# ── MCP client plumbing (import-guarded; absence = backend unavailable) ──────

async def _mcp_call(url: str, tool: Optional[str], args: Optional[dict],
                    timeout: float) -> Any:
    """Open an MCP session; list tools (tool=None) or call one. Raises on error."""
    from mcp import ClientSession  # type: ignore
    from mcp.client.streamable_http import streamablehttp_client  # type: ignore

    async def _run():
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                if tool is None:
                    listed = await session.list_tools()
                    return [t.name for t in listed.tools]
                return await session.call_tool(tool, args or {})

    return await asyncio.wait_for(_run(), timeout=timeout)


async def probe_all() -> dict:
    """Startup health probe for every configured remote backend (best-effort)."""
    for b in _REGISTRY.values():
        if not b.configured or b.kind == "inprocess":
            continue
        if b.kind == "mcp" and b.url:
            try:
                b.tools = await _mcp_call(b.url, None, None, PROBE_TIMEOUT_S)
                b.record_success()
                logger.info("MCP backend %s healthy (%d tools)", b.name, len(b.tools))
            except Exception as exc:
                b.record_failure(f"probe: {exc}")
        elif b.kind == "rest":
            # REST Wolfram has no cheap health endpoint; mark reachable-until-
            # proven-otherwise and let the breaker manage it.
            b.healthy = True
    return status()


# ── Verification: Wolfram fallback ────────────────────────────────────────────

_YES_RE = re.compile(
    r"^\s*(yes|true)\b|\bare\s+equal\b|\bis\s+equal\b|(?<!not )(?<!not\s)\bequivalent\b",
    re.I,
)
_NO_RE = re.compile(r"^\s*(no|false)\b|\bnot\s+equal\b|\bnot\s+equivalent\b|\bunequal\b", re.I)


def _parse_equality_verdict(text: str) -> Optional[bool]:
    """Strict yes/no extraction — anything ambiguous is None (no guessing)."""
    t = (text or "").strip()
    if not t:
        return None
    no = bool(_NO_RE.search(t))
    yes = bool(_YES_RE.search(t))
    if yes and not no:
        return True
    if no and not yes:
        return False
    return None


async def wolfram_is_equal(a: str, b: str) -> Optional[bool]:
    """
    Ask Wolfram whether two expressions are mathematically equal.
    Returns True/False on a definitive verdict, None when unavailable or
    ambiguous — the caller keeps its local behavior on None.
    """
    backend = _REGISTRY.get("wolfram")
    if backend is None or not backend.available():
        return None

    query = f"Is ({a}) equal to ({b})? Answer yes or no."
    try:
        if backend.kind == "mcp":
            result = await _mcp_call(
                backend.url or "", _pick_tool(backend, ("query", "ask", "llm")),
                {"input": query}, VERIFY_TIMEOUT_S,
            )
            text = _mcp_result_text(result)
        else:
            appid = os.getenv("WOLFRAM_APP_ID", "").strip()
            import httpx
            async with httpx.AsyncClient(timeout=VERIFY_TIMEOUT_S) as client:
                resp = await client.get(
                    backend.url or "",
                    params={"appid": appid, "input": query},
                )
                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code}")
                text = resp.text
        backend.record_success()
        return _parse_equality_verdict(text)
    except Exception as exc:
        backend.record_failure(str(exc))
        return None


async def wolfram_expression_valid(expr: str) -> Optional[bool]:
    """Is `expr` a well-defined mathematical expression? (verifier fallback)"""
    backend = _REGISTRY.get("wolfram")
    if backend is None or not backend.available():
        return None
    query = (f"Is ({expr}) a well-defined, finite mathematical expression? "
             "Answer yes or no.")
    try:
        if backend.kind == "mcp":
            result = await _mcp_call(
                backend.url or "", _pick_tool(backend, ("query", "ask", "llm")),
                {"input": query}, VERIFY_TIMEOUT_S,
            )
            text = _mcp_result_text(result)
        else:
            appid = os.getenv("WOLFRAM_APP_ID", "").strip()
            import httpx
            async with httpx.AsyncClient(timeout=VERIFY_TIMEOUT_S) as client:
                resp = await client.get(backend.url or "",
                                        params={"appid": appid, "input": query})
                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code}")
                text = resp.text
        backend.record_success()
        return _parse_equality_verdict(text)
    except Exception as exc:
        backend.record_failure(str(exc))
        return None


# ── Visualization: GeoGebra routing ──────────────────────────────────────────

COMPLEX_SCENE_THRESHOLD = 6  # elements; below this Mafs is faster and cleaner


def _scene_to_commands(scene: list[dict]) -> list[str]:
    """GeometryElement dicts → GeoGebra construction commands."""
    cmds: list[str] = []
    for i, el in enumerate(scene):
        k = el.get("kind")
        try:
            if k == "point":
                cmds.append(f"P{i}=({el['x']},{el['y']})")
            elif k == "segment":
                cmds.append(f"Segment(({el['x1']},{el['y1']}),({el['x2']},{el['y2']}))")
            elif k == "circle":
                cmds.append(f"Circle(({el['cx']},{el['cy']}),{el['r']})")
            elif k == "polygon":
                pts = ",".join(f"({x},{y})" for x, y in el.get("points", []))
                cmds.append(f"Polygon({pts})")
            elif k == "vector":
                cmds.append(
                    f"Vector(({el['x']},{el['y']}),"
                    f"({el['x'] + el['dx']},{el['y'] + el['dy']}))"
                )
        except Exception:
            continue
    return cmds


async def maybe_render_scene(scene: list[dict]) -> Optional[dict]:
    """
    Route a geometry scene to GeoGebra when it's configured, healthy, and the
    scene is complex enough to be worth the hop. Returns a wb_image payload
    {"image_b64", "media_type"} or None → caller falls back to the local
    Mafs renderer (the default and the guaranteed path).
    """
    backend = _REGISTRY.get("geogebra")
    if (backend is None or not backend.available()
            or len(scene) <= COMPLEX_SCENE_THRESHOLD):
        return None
    try:
        tool = _pick_tool(backend, ("render", "export", "construct", "draw"))
        result = await _mcp_call(
            backend.url or "", tool,
            {"commands": _scene_to_commands(scene), "format": "png"},
            RENDER_TIMEOUT_S,
        )
        image_b64 = _mcp_result_image(result)
        if not image_b64:
            raise RuntimeError("no image content in MCP result")
        backend.record_success()
        return {"image_b64": image_b64, "media_type": "image/png"}
    except Exception as exc:
        backend.record_failure(str(exc))
        return None


# ── MCP result helpers ────────────────────────────────────────────────────────

def _pick_tool(backend: Backend, preferred: tuple) -> str:
    for want in preferred:
        for name in backend.tools:
            if want in str(name).lower():
                return str(name)
    return backend.tools[0] if backend.tools else preferred[0]


def _mcp_result_text(result: Any) -> str:
    try:
        parts = []
        for c in getattr(result, "content", []) or []:
            if getattr(c, "type", "") == "text":
                parts.append(getattr(c, "text", ""))
        return "\n".join(parts)
    except Exception:
        return ""


def _mcp_result_image(result: Any) -> Optional[str]:
    try:
        for c in getattr(result, "content", []) or []:
            if getattr(c, "type", "") == "image":
                return getattr(c, "data", None)
    except Exception:
        pass
    return None
