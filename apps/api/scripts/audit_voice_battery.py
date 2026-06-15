"""Voice translation test battery: runs every expression through the real
latex_to_speech pipeline (the LLM rewrite is the only path; on failure the
converter raises and the UI falls back to silent text).

Run from apps/api:  python scripts/audit_voice_battery.py
Writes results to scripts/audit_voice_results.json
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from agents.latex_to_speech import latex_to_speech  # noqa: E402

# (id, text sent to the pipeline, expected spoken form)
ITEMS: list[tuple[str, str, str]] = [
    # ── Battery 1: Integrals ──
    ("i1", r"$\int_a^b f(x)\,dx$", "the integral from a to b of f of x, d x"),
    ("i2", r"$\int_0^\infty e^{-x}\,dx$", "the integral from 0 to infinity of e to the negative x, d x"),
    ("i3", r"$\int f(x)\,dx$", "the integral of f of x, d x"),
    ("i4", r"$\iint_D f(x,y)\,dA$", "the double integral over D of f of x y, d A"),
    ("i5", r"$\iiint_V f\,dV$", "the triple integral over V of f, d V"),
    ("i6", r"$\oint_C \vec{F}\cdot d\vec{r}$", "the line integral of F around C"),
    ("i7", r"$\int_0^1 \int_0^1 xy\,dx\,dy$", "the integral from 0 to 1, the integral from 0 to 1, of x y, d x d y"),
    ("i8", r"$\int_0^{2\pi}\int_0^r f\,r'\,dr'\,d\theta$", "the integral from 0 to 2 pi, the integral from 0 to r, of f times r prime, d r prime d theta"),
    ("i9", r"$\iiint_E f\,\rho^2\sin\phi\,d\rho\,d\phi\,d\theta$", "the triple integral of f, rho squared sine phi, d rho d phi d theta"),
    # ── Battery 2: Derivatives ──
    ("d1", r"$\frac{dy}{dx}$", "d y over d x"),
    ("d2", r"$\frac{\partial f}{\partial x}$", "the partial of f with respect to x"),
    ("d3", r"$\frac{\partial^2 f}{\partial x \partial y}$", "the mixed second partial of f with respect to x and y"),
    ("d4", r"$f'(x)$", "f prime of x"),
    ("d5", r"$f''(x)$", "f double prime of x"),
    ("d6", r"$f^{(n)}(x)$", "the nth derivative of f of x"),
    ("d7", r"$\dot{x}$", "x dot"),
    ("d8", r"$\frac{dz}{dt} = \frac{\partial z}{\partial x}\frac{dx}{dt} + \frac{\partial z}{\partial y}\frac{dy}{dt}$",
     "d z over d t equals the partial of z with respect to x times d x over d t, plus the partial of z with respect to y times d y over d t"),
    # ── Battery 3: nabla ──
    ("n1", r"$\nabla f$", "the gradient of f"),
    ("n2", r"$\nabla \cdot \vec{F}$", "the divergence of F"),
    ("n3", r"$\nabla \times \vec{F}$", "the curl of F"),
    ("n4", r"$\nabla^2 f$", "the Laplacian of f"),
    ("n5", r"$\nabla \times (\nabla f) = \vec{0}$", "the curl of the gradient of f equals the zero vector"),
    ("n6", r"$\nabla \cdot (\nabla \times \vec{F}) = 0$", "the divergence of the curl of F equals 0"),
    # ── Battery 4: Fundamental theorems ──
    ("t1", r"$\int_C \nabla f \cdot d\vec{r} = f(\vec{b}) - f(\vec{a})$",
     "the line integral of the gradient of f along C equals f of b minus f of a"),
    ("t2", r"$\oint_C P\,dx + Q\,dy = \iint_D \left(\frac{\partial Q}{\partial x} - \frac{\partial P}{\partial y}\right)dA$",
     "the line integral around C of P d x plus Q d y, equals the double integral over D of the partial of Q with respect to x minus the partial of P with respect to y, d A"),
    ("t3", r"$\iint_S (\nabla \times \vec{F})\cdot d\vec{S} = \oint_C \vec{F}\cdot d\vec{r}$",
     "the surface integral of the curl of F over S equals the line integral of F around C"),
    ("t4", r"$\iiint_E \nabla \cdot \vec{F}\,dV = \oiint_S \vec{F}\cdot d\vec{S}$",
     "the triple integral of the divergence of F over E equals the flux of F through the closed surface S"),
    # ── Battery 5: Ambiguous symbols (context embedded) ──
    ("a1", r"For a real number, simplify $|x|$.", "the absolute value of x"),
    ("a2", r"For the complex number $z = 3 + 4i$, find $|z|$.", "the modulus of z"),
    ("a3", r"For the matrix $A$, compute $|A|$.", "the determinant of A"),
    ("a4", r"$\|v\|$", "the norm of v"),
    ("a5", r"Suppose $a \mid b$ for integers a and b.", "a divides b"),
    ("a6", r"$\{x \mid x > 0\}$", "the set of x such that x is greater than 0"),
    ("a7", r"$P(A \mid B)$", "the probability of A given B"),
    ("a8", r"Evaluate $f(x)\big|_{x=0}$.", "f of x evaluated at x equals 0"),
    ("a9", r"$X \sim N(0,1)$", "X is distributed as standard normal"),
    ("a10", r"$\triangle ABC \sim \triangle DEF$", "triangle ABC is similar to triangle DEF"),
    ("a11", r"As $n \to \infty$, $f(n) \sim g(n)$.", "f of n is asymptotically equivalent to g of n"),
    ("a12", r"$\frac{df}{dx}$", "d f over d x (not 'the partial')"),
    # ── Battery 6: Coordinate systems ──
    ("c1", r"$\iint_D f(r,\theta)\,r\,dr\,d\theta$", "the double integral of f of r theta, times r, d r d theta (the Jacobian r must be spoken)"),
    ("c2", r"$\iiint_E f\,r\,dr\,d\theta\,dz$", "the triple integral of f, r d r d theta d z"),
    ("c3", r"$x = \rho\sin\phi\cos\theta$", "x equals rho sine phi cosine theta"),
    # ── Battery 7: Compound and nested ──
    ("p1", r"$\frac{d}{dx}\left[\int_a^x f(t)\,dt\right] = f(x)$",
     "the derivative with respect to x of the integral from a to x of f of t, d t, equals f of x"),
    ("p2", r"$\lim_{n\to\infty}\left(1+\frac{1}{n}\right)^n = e$",
     "the limit as n approaches infinity of, the quantity 1 plus 1 over n, to the n, equals e"),
    ("p3", r"$\frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$",
     "negative b plus or minus the square root of b squared minus 4 a c, all over 2 a"),
    ("p4", r"$\sum_{n=1}^\infty \frac{1}{n^2} = \frac{\pi^2}{6}$",
     "the sum from n equals 1 to infinity of 1 over n squared, equals pi squared over 6"),
    ("p5", r"$e^{i\pi} + 1 = 0$", "e to the i pi plus 1 equals 0"),
    ("p6", r"$\hat{\beta} = (X^T X)^{-1} X^T y$",
     "beta hat equals the quantity X transpose X, inverse, times X transpose y"),
    # ── Battery 8: Tokens that must never be spoken ──
    ("z1", r"$\left(\frac{a}{b}\right)$", "a over b (no delimiter names)"),
    ("z2", r"$\begin{pmatrix} 1 \\ 0 \end{pmatrix}$", "the column vector 1, 0 (no 'begin pmatrix')"),
    ("z3", r"$\{x \in \mathbb{R} \mid x > 0\}$", "the set of x in the real numbers such that x is greater than 0"),
    ("z4", r"$\text{tr}(A)$", "the trace of A"),
    ("z5", r"$f(x)\Big|_{x=1}$", "f of x evaluated at x equals 1"),
    ("z6", r"$\underbrace{x+x+\cdots+x}_{n}$", "x plus x plus ... plus x, n times (no 'underbrace')"),
    ("z7", r"$\overbrace{a_1+\cdots+a_n}^{n\text{ terms}}$", "a 1 plus ... plus a n, n terms (no 'overbrace')"),
]

# Tokens that must never appear in spoken output (Section 7)
_FORBIDDEN = re.compile(
    r"[$\\{}^_&~]|dollar|backslash|underscore|caret|\bfrac\b|\bsqrt\b|\bbegin\b|\bend\b"
    r"|pmatrix|vmatrix|\bleft\b paren|delimiter|\bcdot\b|\bbig\b|underbrace|overbrace"
    r"|\bint\b|\biint\b|\boint\b|\bnabla\b|\bvec\b|\bmid\b|\btext\b|la\s?tex",
    re.IGNORECASE,
)


def forbidden_tokens(s: str) -> list[str]:
    return sorted(set(m.group(0) for m in _FORBIDDEN.finditer(s)))


async def run_one(sem, item):
    item_id, text, expected = item
    async with sem:
        try:
            llm_out = await latex_to_speech(text)
        except Exception as exc:  # noqa: BLE001
            llm_out = f"<ERROR: {exc}>"
    return {
        "id": item_id,
        "input": text,
        "expected": expected,
        "llm_output": llm_out,
        "llm_forbidden_tokens": forbidden_tokens(llm_out),
    }


async def main():
    sem = asyncio.Semaphore(6)
    results = await asyncio.gather(*(run_one(sem, it) for it in ITEMS))
    out = pathlib.Path(__file__).parent / "audit_voice_results.json"
    out.write_text(json.dumps(list(results), indent=2, ensure_ascii=False), encoding="utf-8")
    llm_fail = sum(1 for r in results if r["llm_forbidden_tokens"])
    print(f"Wrote {out}")
    print(f"Token-level failures - LLM path: {llm_fail}/{len(results)}")


if __name__ == "__main__":
    asyncio.run(main())
