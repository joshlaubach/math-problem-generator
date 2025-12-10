"""AP Calculus concept map.

AP Calculus includes both AP Calculus AB and BC content.
References precalculus concepts and builds on them.
"""
from concepts import Concept, register_concept

# Limits and Continuity
register_concept(Concept(
    id="ap_calc.limits.definition",
    name="Limit Definition and Evaluation",
    course_id="ap_calculus",
    unit_id="ap_limits",
    topic_id="ap_limits_def",
    kind="definition",
    description="Formal definition of limits and limit evaluation techniques",
    prerequisites=["precalc.functions.behavior_at_infinity"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$\\lim_{x \\to a} f(x) = L$"],
    tags=["ap_calculus", "limits"]
))

register_concept(Concept(
    id="ap_calc.limits.continuity",
    name="Continuity and Intermediate Value Theorem",
    course_id="ap_calculus",
    unit_id="ap_limits",
    topic_id="ap_limits_cont",
    kind="theorem",
    description="Continuity definitions and IVT",
    prerequisites=["ap_calc.limits.definition"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["Is $f$ continuous at $x=c$?"],
    tags=["ap_calculus", "limits"]
))

# Derivatives
register_concept(Concept(
    id="ap_calc.derivatives.definition",
    name="Derivative as a Limit",
    course_id="ap_calculus",
    unit_id="ap_derivatives",
    topic_id="ap_deriv_def",
    kind="definition",
    description="Derivative definition: $f'(x) = \\lim_{h \\to 0} \\frac{f(x+h)-f(x)}{h}$",
    prerequisites=["ap_calc.limits.definition"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$f'(a) = \\lim_{x \\to a} \\frac{f(x) - f(a)}{x - a}$"],
    tags=["ap_calculus", "derivatives"]
))

register_concept(Concept(
    id="ap_calc.derivatives.power_rule",
    name="Power Rule and Basic Derivative Rules",
    course_id="ap_calculus",
    unit_id="ap_derivatives",
    topic_id="ap_deriv_rules",
    kind="skill",
    description="Power rule, product rule, quotient rule, chain rule",
    prerequisites=["ap_calc.derivatives.definition"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$(x^n)' = nx^{n-1}$", "$(fg)' = f'g + fg'$"],
    tags=["ap_calculus", "derivatives"]
))

register_concept(Concept(
    id="ap_calc.derivatives.chain_rule",
    name="Chain Rule",
    course_id="ap_calculus",
    unit_id="ap_derivatives",
    topic_id="ap_deriv_chain",
    kind="skill",
    description="Chain rule for composite functions",
    prerequisites=["ap_calc.derivatives.power_rule"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$\\frac{d}{dx}[f(g(x))] = f'(g(x)) \\cdot g'(x)$"],
    tags=["ap_calculus", "chain_rule"]
))

register_concept(Concept(
    id="ap_calc.derivatives.implicit",
    name="Implicit Differentiation",
    course_id="ap_calculus",
    unit_id="ap_derivatives",
    topic_id="ap_deriv_implicit",
    kind="skill",
    description="Implicit differentiation and related rates",
    prerequisites=["ap_calc.derivatives.chain_rule"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["Differentiate $x^2 + y^2 = 25$ with respect to $x$"],
    tags=["ap_calculus", "implicit_differentiation"]
))

register_concept(Concept(
    id="ap_calc.derivatives.applications",
    name="Applications of Derivatives",
    course_id="ap_calculus",
    unit_id="ap_derivatives",
    topic_id="ap_deriv_apps",
    kind="skill",
    description="Critical points, extrema, optimization, concavity",
    prerequisites=["ap_calc.derivatives.power_rule"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["Find maxima/minima", "Analyze concavity"],
    tags=["ap_calculus", "optimization"]
))

register_concept(Concept(
    id="ap_calc.derivatives.mean_value_theorem",
    name="Mean Value Theorem",
    course_id="ap_calculus",
    unit_id="ap_derivatives",
    topic_id="ap_deriv_mvt",
    kind="theorem",
    description="MVT and Rolle's Theorem",
    prerequisites=["ap_calc.limits.continuity", "ap_calc.derivatives.definition"],
    difficulty_min=4,
    difficulty_max=4,
    examples_latex=["There exists $c$ where $f'(c) = \\frac{f(b) - f(a)}{b - a}$"],
    tags=["ap_calculus", "theorems"]
))

# Integrals
register_concept(Concept(
    id="ap_calc.integrals.definition",
    name="Riemann Sums and Definite Integrals",
    course_id="ap_calculus",
    unit_id="ap_integrals",
    topic_id="ap_int_def",
    kind="definition",
    description="Riemann sums and integral definition",
    prerequisites=["ap_calc.limits.definition"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$\\int_a^b f(x) \\, dx = \\lim_{n \\to \\infty} \\sum f(x_i) \\Delta x$"],
    tags=["ap_calculus", "integrals"]
))

register_concept(Concept(
    id="ap_calc.integrals.ftc",
    name="Fundamental Theorem of Calculus",
    course_id="ap_calculus",
    unit_id="ap_integrals",
    topic_id="ap_int_ftc",
    kind="theorem",
    description="FTC Parts 1 and 2, relating derivatives and integrals",
    prerequisites=["ap_calc.integrals.definition", "ap_calc.derivatives.definition"],
    difficulty_min=4,
    difficulty_max=4,
    examples_latex=["$\\frac{d}{dx}\\int_a^x f(t) dt = f(x)$"],
    tags=["ap_calculus", "ftc"]
))

register_concept(Concept(
    id="ap_calc.integrals.antiderivatives",
    name="Antiderivatives and Indefinite Integrals",
    course_id="ap_calculus",
    unit_id="ap_integrals",
    topic_id="ap_int_antideriv",
    kind="skill",
    description="Finding antiderivatives and indefinite integrals",
    prerequisites=["ap_calc.derivatives.power_rule"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$\\int x^n dx = \\frac{x^{n+1}}{n+1} + C$"],
    tags=["ap_calculus", "antiderivatives"]
))

register_concept(Concept(
    id="ap_calc.integrals.u_substitution",
    name="U-Substitution",
    course_id="ap_calculus",
    unit_id="ap_integrals",
    topic_id="ap_int_substitution",
    kind="skill",
    description="Integration by u-substitution",
    prerequisites=["ap_calc.integrals.antiderivatives", "ap_calc.derivatives.chain_rule"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["Let $u = g(x)$, then $\\int f(g(x))g'(x) dx = \\int f(u) du$"],
    tags=["ap_calculus", "integration_techniques"]
))

register_concept(Concept(
    id="ap_calc.integrals.area_volume",
    name="Area and Volume Applications",
    course_id="ap_calculus",
    unit_id="ap_integrals",
    topic_id="ap_int_apps",
    kind="skill",
    description="Area between curves, volumes of revolution",
    prerequisites=["ap_calc.integrals.ftc"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$A = \\int_a^b |f(x) - g(x)| dx$"],
    tags=["ap_calculus", "applications"]
))

# BC-specific topics
register_concept(Concept(
    id="ap_calc.bc.integration_by_parts",
    name="Integration by Parts (BC only)",
    course_id="ap_calculus",
    unit_id="ap_integrals",
    topic_id="ap_int_ibp",
    kind="skill",
    description="Integration by parts for BC exam",
    prerequisites=["ap_calc.integrals.u_substitution"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$\\int u \\, dv = uv - \\int v \\, du$"],
    tags=["ap_calculus", "bc", "integration_techniques"]
))

register_concept(Concept(
    id="ap_calc.bc.series",
    name="Infinite Series and Convergence (BC only)",
    course_id="ap_calculus",
    unit_id="ap_series",
    topic_id="ap_series_conv",
    kind="definition",
    description="Series convergence tests, Taylor series",
    prerequisites=["ap_calc.limits.definition"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$\\sum_{n=1}^{\\infty} a_n$", "Taylor series: $f(x) = \\sum a_n(x-c)^n$"],
    tags=["ap_calculus", "bc", "series"]
))

register_concept(Concept(
    id="ap_calc.bc.parametric",
    name="Parametric and Polar Equations (BC only)",
    course_id="ap_calculus",
    unit_id="ap_parametric",
    topic_id="ap_para_polar",
    kind="skill",
    description="Derivatives and integrals with parametric and polar equations",
    prerequisites=["ap_calc.derivatives.chain_rule", "ap_calc.integrals.ftc"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$\\frac{dy}{dx} = \\frac{dy/dt}{dx/dt}$"],
    tags=["ap_calculus", "bc", "parametric"]
))

# Differential Equations
register_concept(Concept(
    id="ap_calc.diff_eq.separation",
    name="Separable Differential Equations",
    course_id="ap_calculus",
    unit_id="ap_differential_eq",
    topic_id="ap_diff_eq_sep",
    kind="skill",
    description="Solving separable differential equations",
    prerequisites=["ap_calc.integrals.u_substitution"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$\\frac{dy}{dx} = g(x)h(y)$"],
    tags=["ap_calculus", "differential_equations"]
))

register_concept(Concept(
    id="ap_calc.diff_eq.slope_fields",
    name="Slope Fields and Euler's Method",
    course_id="ap_calculus",
    unit_id="ap_differential_eq",
    topic_id="ap_diff_eq_visual",
    kind="skill",
    description="Visual representation and numerical methods for differential equations",
    prerequisites=["ap_calc.derivatives.definition"],
    difficulty_min=3,
    difficulty_max=3,
    examples_latex=["Sketch slope field for $\\frac{dy}{dx} = f(x, y)$"],
    tags=["ap_calculus", "differential_equations"]
))

# Test Strategy
register_concept(Concept(
    id="ap_calc.test_strategy.free_response",
    name="Free Response and Exam Strategies",
    course_id="ap_calculus",
    unit_id="ap_derivatives",
    topic_id="ap_deriv_def",
    kind="strategy",
    description="AP exam structure and strategies",
    prerequisites=[],
    difficulty_min=1,
    difficulty_max=1,
    examples_latex=["Show work clearly"],
    tags=["ap_calculus", "test_strategy"]
))
