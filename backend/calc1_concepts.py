"""Calculus I concept map."""
from concepts import Concept, register_concept

# Limits and Continuity
register_concept(Concept(
    id="calc1.limits.formal_definition",
    name="Formal Limit Definition",
    course_id="calculus_1",
    unit_id="calc1_limits",
    topic_id="calc1_limit_def",
    kind="definition",
    description="Epsilon-delta definition of limit",
    prerequisites=["precalc.limits.intuitive"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$|f(x) - L| < \\epsilon$ when $|x - a| < \\delta$"],
    tags=["limits"]
))

register_concept(Concept(
    id="calc1.limits.evaluation",
    name="Evaluating Limits",
    course_id="calculus_1",
    unit_id="calc1_limits",
    topic_id="calc1_limit_def",
    kind="skill",
    description="Algebraic techniques; L'Hôpital's rule; limits at infinity",
    prerequisites=["calc1.limits.formal_definition"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$\\lim_{x \\to \\infty} \\frac{1}{x} = 0$"],
    tags=["limits"]
))

register_concept(Concept(
    id="calc1.continuity.types",
    name="Types of Discontinuity",
    course_id="calculus_1",
    unit_id="calc1_limits",
    topic_id="calc1_continuity",
    kind="definition",
    description="Removable, jump, infinite discontinuities",
    prerequisites=["precalc.limits.continuity"],
    difficulty_min=4,
    difficulty_max=4,
    examples_latex=["Removable discontinuity at $x=a$"],
    tags=["continuity"]
))

# Derivatives
register_concept(Concept(
    id="calc1.derivatives.formal_definition",
    name="Derivative Definition (Limit of Difference Quotient)",
    course_id="calculus_1",
    unit_id="calc1_derivatives",
    topic_id="calc1_deriv_def",
    kind="definition",
    description="Instantaneous rate of change; difference quotient",
    prerequisites=["calc1.limits.evaluation"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$f'(x) = \\lim_{h \\to 0} \\frac{f(x+h) - f(x)}{h}$"],
    tags=["derivatives"]
))

register_concept(Concept(
    id="calc1.derivatives.power_rule",
    name="Power Rule",
    course_id="calculus_1",
    unit_id="calc1_derivatives",
    topic_id="calc1_deriv_rules",
    kind="skill",
    description="Differentiation using power rule",
    prerequisites=["calc1.derivatives.formal_definition"],
    difficulty_min=2,
    difficulty_max=3,
    examples_latex=["$(x^n)' = nx^{n-1}$"],
    tags=["derivatives"]
))

register_concept(Concept(
    id="calc1.derivatives.product_quotient",
    name="Product and Quotient Rules",
    course_id="calculus_1",
    unit_id="calc1_derivatives",
    topic_id="calc1_deriv_rules",
    kind="skill",
    description="Differentiation of products and quotients",
    prerequisites=["calc1.derivatives.power_rule"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$(uv)' = u'v + uv'$"],
    tags=["derivatives"]
))

register_concept(Concept(
    id="calc1.derivatives.chain_rule",
    name="Chain Rule",
    course_id="calculus_1",
    unit_id="calc1_derivatives",
    topic_id="calc1_chain_rule",
    kind="skill",
    description="Differentiation of composite functions",
    prerequisites=["calc1.derivatives.product_quotient"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$(f(g(x)))' = f'(g(x)) \\cdot g'(x)$"],
    tags=["chain_rule"]
))

register_concept(Concept(
    id="calc1.derivatives.exponential_log",
    name="Derivatives of Exponential and Logarithmic Functions",
    course_id="calculus_1",
    unit_id="calc1_derivatives",
    topic_id="calc1_deriv_rules",
    kind="skill",
    description="Differentiation of $e^x$, $a^x$, $\\ln(x)$, $\\log_a(x)$",
    prerequisites=["calc1.derivatives.chain_rule"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$(e^x)' = e^x$", "$(\\ln(x))' = \\frac{1}{x}$"],
    tags=["derivatives"]
))

register_concept(Concept(
    id="calc1.derivatives.related_rates",
    name="Related Rates",
    course_id="calculus_1",
    unit_id="calc1_derivatives",
    topic_id="calc1_chain_rule",
    kind="skill",
    description="Solving related rates problems using implicit differentiation",
    prerequisites=["calc1.derivatives.chain_rule"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$\\frac{dA}{dt} = \\frac{dA}{dr} \\cdot \\frac{dr}{dt}$"],
    tags=["related_rates"]
))

# Applications of Derivatives
register_concept(Concept(
    id="calc1.applications.extrema",
    name="Critical Points and Extrema",
    course_id="calculus_1",
    unit_id="calc1_applications",
    topic_id="calc1_extrema",
    kind="skill",
    description="Finding local and absolute extrema using derivatives",
    prerequisites=["calc1.derivatives.power_rule"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["Critical point: $f'(x) = 0$"],
    tags=["extrema"]
))

register_concept(Concept(
    id="calc1.applications.optimization",
    name="Optimization Problems",
    course_id="calculus_1",
    unit_id="calc1_applications",
    topic_id="calc1_optimization",
    kind="skill",
    description="Maximizing and minimizing real-world quantities",
    prerequisites=["calc1.applications.extrema"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["Maximize $A = length \\times width$"],
    tags=["optimization"]
))

register_concept(Concept(
    id="calc1.applications.concavity",
    name="Concavity and Inflection Points",
    course_id="calculus_1",
    unit_id="calc1_applications",
    topic_id="calc1_extrema",
    kind="skill",
    description="Second derivative test; concavity analysis",
    prerequisites=["calc1.applications.extrema"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["Inflection point: $f''(x) = 0$"],
    tags=["concavity"]
))

# Integration
register_concept(Concept(
    id="calc1.integration.antiderivatives",
    name="Antiderivatives and Indefinite Integrals",
    course_id="calculus_1",
    unit_id="calc1_integration",
    topic_id="calc1_antiderivatives",
    kind="definition",
    description="Understanding antiderivatives; power rule for integration",
    prerequisites=["calc1.derivatives.power_rule"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$\\int x^n \\, dx = \\frac{x^{n+1}}{n+1} + C$"],
    tags=["integration"]
))

register_concept(Concept(
    id="calc1.integration.definite_integral",
    name="Definite Integrals and Riemann Sums",
    course_id="calculus_1",
    unit_id="calc1_integration",
    topic_id="calc1_definite_integral",
    kind="definition",
    description="Understanding definite integrals; area under curve",
    prerequisites=["calc1.integration.antiderivatives"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$\\int_a^b f(x) \\, dx$"],
    tags=["integration"]
))

register_concept(Concept(
    id="calc1.integration.ftc",
    name="Fundamental Theorem of Calculus",
    course_id="calculus_1",
    unit_id="calc1_integration",
    topic_id="calc1_ftc",
    kind="definition",
    description="Connection between derivatives and integrals",
    prerequisites=["calc1.integration.definite_integral"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$\\frac{d}{dx} \\int_a^x f(t) \\, dt = f(x)$"],
    tags=["ftc"]
))

register_concept(Concept(
    id="calc1.integration.substitution",
    name="U-Substitution",
    course_id="calculus_1",
    unit_id="calc1_integration",
    topic_id="calc1_antiderivatives",
    kind="skill",
    description="Integration by u-substitution",
    prerequisites=["calc1.integration.antiderivatives"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$\\int f(g(x)) g'(x) \\, dx = \\int f(u) \\, du$"],
    tags=["integration"]
))
