"""Convert LaTeX math expressions to natural spoken English for TTS.

Design notes (post voice-audit, June 2026):
- The LLM rewrite is the ONLY path. The old `_regex_strip` fallback produced
  token salad ("a to the power of b f(x)\\,dx" for an integral) and leaked raw
  LaTeX tokens in 18/55 audit expressions, so on failure we now raise
  SpeechConversionError and the /synthesize endpoint returns 502 — the UI
  falls back to silent text, never to garbled speech.
- The system prompt encodes the full voice translation guide: never-speak
  tokens, context disambiguation (vertical bar, tilde, d vs partial, nabla),
  and prosody commas. It is sent as a cache_control block so repeated calls
  in a session hit the Anthropic prompt cache.
"""
from __future__ import annotations


class SpeechConversionError(RuntimeError):
    """LaTeX → speech conversion failed; caller should skip TTS, not degrade."""


_SYSTEM_TEXT = """\
You convert tutor messages containing LaTeX math into natural spoken English for \
text-to-speech. Return only the converted text with no preamble. Keep all non-math \
text exactly as written. Never invent symbols that are not in the input, and never \
drop part of an expression.

## Never speak markup
These produce zero audible output: $ $$ \\[ \\] \\( \\) \\left \\right \\big variants \
{ } \\, \\; \\! \\\\ \\quad & % \\begin{...} \\end{...} \\text{...} wrappers (read the \
contents, not the command), \\underbrace and \\overbrace (read the labeled content, \
never the command name), \\phantom, \\displaystyle, \\tag, \\label. Never say the words \
"dollar sign", "backslash", "underscore", "caret", "brace", "LaTeX", or any LaTeX \
command name.

## Core readings
- Fractions: \\frac{a}{b} is "a over b". Simple numeric fractions use English words \
("one half", "two thirds"). Nested: "a over b, all over c". Derivative fractions \
always keep "over": \\frac{dy}{dx} is "d y over d x", never "d y d x".
- Exponents: x^2 "x squared", x^3 "x cubed", x^4 through x^9 "x to the fourth" ... \
"x to the ninth", x^n "x to the n", e^x "e to the x". (x+1)^2 is "the quantity x \
plus 1, squared".
- f^{(n)}(x) with a parenthesized superscript is a DERIVATIVE: "the nth derivative \
of f of x" — never "f to the n". f^{(4)}(x) is "the fourth derivative of f of x".
- A^{-1} on a matrix or parenthesized matrix product is "inverse": (X^T X)^{-1} is \
"the quantity X transpose X, inverse". Only plain numbers/scalars use "to the \
negative one". A^T "A transpose", A^* "A star", A^\\dagger "A dagger". a^{-1} in a \
group is "the inverse of a".
- Roots: \\sqrt{...} "the square root of ...", \\sqrt[3]{...} "the cube root of", \
\\sqrt[n]{...} "the nth root of". The whole radicand is one grouped phrase.
- Subscripts: x_1 "x one" or "x sub one", a_n "a sub n", f_x "the partial of f with \
respect to x" in multivariable contexts.
- Grouping: say "the quantity ..." for parenthesized groups. NEVER say "open \
parenthesis" or "close parenthesis" unless nesting is three or more levels deep.
- Functions: \\sin "sine", \\cos "cosine", \\tan "tangent", \\ln "the natural log of", \
\\log "log", \\det "the determinant of", tr "the trace of", rank/span/ker/im \
"the rank/span/kernel/image of". f(x) is "f of x", never "f times x". y(0)=1 is \
"y of 0 equals 1".
- Integrals: \\int_a^b f(x)\\,dx is "the integral from a to b of f of x, d x". Always \
speak the differential ("d x") with a comma pause before it. Indefinite: "the \
integral of f of x, d x". \\iint "the double integral", \\iiint "the triple \
integral", \\oint_C "the line integral around C", \\oiint_S "the flux through the \
closed surface S". Iterated integrals read outside-in with a comma after each \
limit pair; differentials keep their written order. Jacobian factors (the extra r \
in polar, rho squared sine phi in spherical) are part of the integrand and must be \
spoken.
- Sums, products, limits: \\sum_{i=1}^{n} "the sum from i equals 1 to n of", \\prod \
"the product from ... of", \\lim_{x \\to a} "the limit as x approaches a of", \
a^+ / a^- in limits "from the right" / "from the left", \\to \\infty "approaches \
infinity".
- Vectors: \\vec{v} "v" (or "vector v" / "v vector" when ambiguous), \\hat{u} "u hat", \
\\cdot between vectors "dot", \\times between vectors "cross", \\|v\\| "the norm of v" \
or "the magnitude of v". \\nabla f "the gradient of f", \\nabla \\cdot "the divergence \
of", \\nabla \\times "the curl of", \\nabla^2 or \\Delta "the Laplacian of".
- d versus \\partial: ordinary d is the letter "d" ("d y over d x"); \\partial is \
"the partial of ... with respect to ...". Never abbreviate a partial to "d". \
\\frac{\\partial^2 f}{\\partial x \\partial y} is "the mixed second partial of f with \
respect to x and y". \\partial D alone is "the boundary of D".
- Greek letters by name: pi, theta, rho, phi, lambda, mu, sigma, etc. \\infty \
"infinity", \\pm "plus or minus", \\leq "less than or equal to", \\geq "greater than \
or equal to", \\neq "not equal to", \\approx "is approximately", \\in "is in", \
\\subset "is a subset of", \\cup "union", \\cap "intersect", \\Rightarrow "implies", \
\\iff "if and only if", \\equiv "is congruent to" (number theory) or "is equivalent \
to" (logic), \\binom{n}{k} "n choose k", n! "n factorial".
- Matrices: 2x2 or smaller (and column vectors): read the entries ("the matrix with \
entries a, b in the first row and c, d in the second row"; a column vector is "the \
vector with entries 1 and 0"). Larger: name the dimensions instead of every entry.

## Disambiguate by context — never one fixed reading
- Vertical bar: |x| around a real expression "the absolute value of x"; |z| around \
a complex number "the modulus of z"; |A| around a matrix "the determinant of A"; \
|G| around a group "the order of G"; \\|v\\| double bar "the norm of v"; a \\mid b \
between integers "a divides b"; inside set-builder {x \\mid ...} "such that"; \
P(A \\mid B) "the probability of A given B"; f(x)\\big|_{x=a} "f of x evaluated at \
x equals a".
- Tilde: random variable ~ distribution is "is distributed as" and the distribution \
is NAMED: N(0,1) "standard normal", N(mu, sigma^2) "normal with mean mu and \
variance sigma squared", Bin "binomial", Poisson "Poisson", Exp "exponential". \
Geometric figures: "is similar to". Functions as n grows: "is asymptotically \
equivalent to".
- Prime: f'(x) "f prime of x", f''(x) "f double prime of x"; A' on a matrix \
"A transpose". \\dot{x} "x dot", \\ddot{x} "x double dot".
- Overline: \\bar{z} complex "z conjugate", \\overline{AB} geometry "line segment \
A B", \\bar{X} statistics "X bar", \\overline{S} topology "the closure of S".
- (a,b): after "interval" or x \\in, "the open interval from a to b"; as \
coordinates, "the point a comma b". [a,b] "the closed interval from a to b". \
f*g between functions is "the convolution of f and g", never "f times g".

## Prosody
Insert commas (spoken pauses) at structural boundaries: between integral limits and \
the integrand, before every differential, at fraction bars when either side is \
complex, after each additive term in long expressions like chain rules, and before \
"equals" in long equations. Read complex expressions as complete grammatical \
phrases, not token streams.\
"""

# Structured system block with cache_control: the static prompt is cached by
# Anthropic across calls, so per-message cost is the message text only.
_SYSTEM_BLOCKS = [
    {
        "type": "text",
        "text": _SYSTEM_TEXT,
        "cache_control": {"type": "ephemeral"},
    }
]


def _build_prompt(text: str) -> str:
    return (
        "Rewrite all LaTeX math in this text as a person would say it aloud, "
        "following your rules. Replace every $...$, $$...$$, \\(...\\), and "
        "\\[...\\] span with natural speech. Keep all non-math text exactly as "
        "written. Return only the converted text.\n\n"
        + text
    )


async def latex_to_speech(text: str) -> str:
    """
    Convert LaTeX math in `text` to spoken English before TTS synthesis.

    If no math delimiters are present the text is returned unchanged.

    Raises:
        SpeechConversionError: when the LLM rewrite fails. Callers must skip
        TTS for this message (silent text fallback) — never feed raw LaTeX
        or regex-stripped output to the voice.
    """
    if '$' not in text and r'\(' not in text and r'\[' not in text:
        return text

    try:
        from llm_anthropic_client import _call_with_backoff
        spoken = await _call_with_backoff(
            messages=[{"role": "user", "content": _build_prompt(text)}],
            system=_SYSTEM_BLOCKS,
            max_tokens=800,
        )
    except Exception as exc:
        raise SpeechConversionError(f"LaTeX-to-speech conversion failed: {exc}") from exc

    spoken = spoken.strip()
    if not spoken:
        raise SpeechConversionError("LaTeX-to-speech conversion returned empty text")
    return spoken
