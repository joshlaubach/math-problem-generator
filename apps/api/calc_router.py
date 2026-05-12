"""
Calculator API router — CAS endpoint backed by SymPy.

POST /calc/cas  — evaluate a symbolic expression via SymPy.
  - Premium (non-free) users only.
  - Difficulty >= 5 gate enforced server-side.
  - 1 concurrent SymPy call per user (per-user asyncio semaphore).
  - 10-second hard timeout; returns error entry on expiry.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from auth_dependencies import get_current_user
from users_models import User
from rl_logger import log_event

router = APIRouter(prefix="/calc", tags=["calculator"])

# ── Thread pool for CPU-bound SymPy work ──────────────────────────────────────
_sympy_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="sympy")

# ── Per-user semaphores (1 concurrent CAS call per user) ─────────────────────
_user_semaphores: dict[str, asyncio.Semaphore] = {}


def _get_semaphore(user_id: str) -> asyncio.Semaphore:
    if user_id not in _user_semaphores:
        _user_semaphores[user_id] = asyncio.Semaphore(1)
    return _user_semaphores[user_id]


# ── Request / Response models ─────────────────────────────────────────────────

CASOperation = Literal[
    "evaluate",
    "simplify",
    "expand",
    "factor",
    "solve",
    "diff",
    "integrate",
    "integrate_definite",
    "limit",
    "det",
    "eigenvals",
    "laplace",
    "ilaplace",
    "series",
]


class CASRequest(BaseModel):
    expression: str
    operation: CASOperation = "evaluate"
    variable: str = "x"
    lower: Optional[str] = None      # definite integral lower bound
    upper: Optional[str] = None      # definite integral upper bound
    at: Optional[str] = None         # limit point / series expansion point
    direction: Optional[str] = None  # limit direction: "+", "-", "+-"
    order: int = 6                   # series expansion order
    topic_id: str = ""
    difficulty: int = 0
    problem_id: str = ""
    session_id: str = ""


class CASResponse(BaseModel):
    latex: str
    expression: str
    operation: CASOperation


class CASError(BaseModel):
    error: str
    message: str


# ── SymPy evaluation (runs in thread pool) ───────────────────────────────────

def _sympy_evaluate(req: CASRequest) -> tuple[str, str]:
    """Return (latex_str, expr_str). Raises ValueError on bad input."""
    import sympy as sp
    from sympy.integrals.transforms import laplace_transform, inverse_laplace_transform

    # Parse symbols
    var = sp.Symbol(req.variable)
    s = sp.Symbol("s")
    t = sp.Symbol("t")

    expr = sp.sympify(req.expression, locals={req.variable: var, "s": s, "t": t})

    op = req.operation

    if op == "evaluate" or op == "simplify":
        result = sp.simplify(expr)

    elif op == "expand":
        result = sp.expand(expr)

    elif op == "factor":
        result = sp.factor(expr)

    elif op == "solve":
        solutions = sp.solve(expr, var)
        result = sp.Matrix(solutions) if len(solutions) != 1 else solutions[0]

    elif op == "diff":
        result = sp.diff(expr, var)

    elif op == "integrate":
        result = sp.integrate(expr, var)

    elif op == "integrate_definite":
        lo = sp.sympify(req.lower or "0")
        hi = sp.sympify(req.upper or "1")
        result = sp.integrate(expr, (var, lo, hi))

    elif op == "limit":
        at = sp.sympify(req.at or "0")
        direction = req.direction or "+"
        result = sp.limit(expr, var, at, direction)

    elif op == "det":
        mat = sp.Matrix(sp.sympify(req.expression))
        result = mat.det()

    elif op == "eigenvals":
        mat = sp.Matrix(sp.sympify(req.expression))
        ev = mat.eigenvals()
        result = sp.Eq(sp.Symbol("eigenvalues"), sp.Matrix(list(ev.keys())))

    elif op == "laplace":
        lt, _, _ = laplace_transform(expr, t, s)
        result = lt

    elif op == "ilaplace":
        result = inverse_laplace_transform(expr, s, t)

    elif op == "series":
        at = sp.sympify(req.at or "0")
        result = sp.series(expr, var, at, req.order).removeO()

    else:
        raise ValueError(f"Unknown operation: {op}")

    latex_str = sp.latex(result)
    expr_str = str(result)
    return latex_str, expr_str


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/cas", response_model=CASResponse)
async def cas_evaluate(
    req: CASRequest,
    current_user: User = Depends(get_current_user),
) -> CASResponse:
    """Evaluate a symbolic expression via SymPy (premium, difficulty >= 5 only)."""

    # Premium gate
    if getattr(current_user, "tier", "free") == "free":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CAS calculator requires a paid plan.",
        )

    # Difficulty gate
    if req.difficulty < 5:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CAS calculator is only available on difficulty 5–6 problems.",
        )

    sem = _get_semaphore(current_user.id)

    async with sem:
        loop = asyncio.get_event_loop()
        try:
            latex_str, expr_str = await asyncio.wait_for(
                loop.run_in_executor(_sympy_executor, _sympy_evaluate, req),
                timeout=10.0,
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail="CAS evaluation timed out. Simplify your expression and try again.",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not evaluate: {exc}",
            )

    # Log the send event
    try:
        log_event(
            session_id=req.session_id or "unknown",
            user_id=current_user.id,
            topic_id=req.topic_id,
            difficulty=req.difficulty,
            event_type="calculator_send",
            payload={
                "calculator_level": "cas",
                "operation": req.operation,
                "had_cas_upgrade": True,
            },
        )
    except Exception:
        pass  # logging is fire-and-forget

    return CASResponse(latex=latex_str, expression=expr_str, operation=req.operation)
