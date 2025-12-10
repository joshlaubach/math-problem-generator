"""Pre-Calculus and Trigonometry concept map."""
from concepts import Concept, register_concept

# Functions
register_concept(Concept(
    id="precalc.functions.domain_range",
    name="Function Domain and Range",
    course_id="precalculus",
    unit_id="precalc_functions",
    topic_id="precalc_func_basics",
    kind="definition",
    description="Understanding domain and range of functions",
    prerequisites=["alg1.expr.variables_basic"],
    difficulty_min=2,
    difficulty_max=3,
    examples_latex=["$f(x) = \\sqrt{x}$, domain: $x \\geq 0$"],
    tags=["functions"]
))

register_concept(Concept(
    id="precalc.functions.transformations",
    name="Function Transformations",
    course_id="precalculus",
    unit_id="precalc_functions",
    topic_id="precalc_func_transforms",
    kind="skill",
    description="Shifts, stretches, reflections of parent functions",
    prerequisites=["precalc.functions.domain_range"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$f(x) + k$, $f(x-h)$"],
    tags=["transformations"]
))

register_concept(Concept(
    id="precalc.functions.composition",
    name="Function Composition and Inverses",
    course_id="precalculus",
    unit_id="precalc_functions",
    topic_id="precalc_func_composition",
    kind="skill",
    description="Composing functions; finding inverses",
    prerequisites=["precalc.functions.domain_range"],
    difficulty_min=3,
    difficulty_max=5,
    examples_latex=["$(f \\circ g)(x) = f(g(x))$"],
    tags=["composition", "inverses"]
))

# Trigonometry
register_concept(Concept(
    id="precalc.trig.ratios",
    name="Trigonometric Ratios",
    course_id="precalculus",
    unit_id="precalc_trig",
    topic_id="precalc_trig_ratios",
    kind="definition",
    description="Sine, cosine, tangent and reciprocal ratios",
    prerequisites=["geo.triangles.pythagorean"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$\\sin(\\theta) = \\frac{\\text{opposite}}{\\text{hypotenuse}}$"],
    tags=["trigonometry"]
))

register_concept(Concept(
    id="precalc.trig.unit_circle",
    name="Unit Circle and Reference Angles",
    course_id="precalculus",
    unit_id="precalc_trig",
    topic_id="precalc_trig_ratios",
    kind="definition",
    description="Unit circle values; reference angles for all quadrants",
    prerequisites=["precalc.trig.ratios"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$\\cos(30°) = \\frac{\\sqrt{3}}{2}$"],
    tags=["trigonometry"]
))

register_concept(Concept(
    id="precalc.trig.identities",
    name="Trigonometric Identities",
    course_id="precalculus",
    unit_id="precalc_trig",
    topic_id="precalc_trig_identities",
    kind="skill",
    description="Pythagorean, sum/difference, double angle identities",
    prerequisites=["precalc.trig.unit_circle"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$\\sin^2(\\theta) + \\cos^2(\\theta) = 1$"],
    tags=["identities"]
))

register_concept(Concept(
    id="precalc.trig.equations",
    name="Solving Trigonometric Equations",
    course_id="precalculus",
    unit_id="precalc_trig",
    topic_id="precalc_trig_equations",
    kind="skill",
    description="Finding solutions to trig equations",
    prerequisites=["precalc.trig.identities"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$\\sin(x) = \\frac{1}{2}$"],
    tags=["trigonometry", "equations"]
))

# Inverse Trig
register_concept(Concept(
    id="precalc.inverse.inverse_trig",
    name="Inverse Trigonometric Functions",
    course_id="precalculus",
    unit_id="precalc_inverse",
    topic_id="precalc_inverse_trig",
    kind="definition",
    description="Arcsin, arccos, arctan and their domains",
    prerequisites=["precalc.trig.unit_circle", "precalc.functions.composition"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$y = \\arcsin(x)$"],
    tags=["inverse_trig"]
))

# Polar and Parametric
register_concept(Concept(
    id="precalc.polar.coordinates",
    name="Polar Coordinates",
    course_id="precalculus",
    unit_id="precalc_polar",
    topic_id="precalc_polar_coords",
    kind="definition",
    description="Converting between rectangular and polar; graphing polar curves",
    prerequisites=["precalc.trig.ratios"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$(r, \\theta)$, $x = r\\cos(\\theta)$"],
    tags=["polar"]
))

register_concept(Concept(
    id="precalc.parametric.equations",
    name="Parametric Equations",
    course_id="precalculus",
    unit_id="precalc_polar",
    topic_id="precalc_parametric",
    kind="definition",
    description="Parametric curves; converting to/from rectangular",
    prerequisites=["geo.coordinate.equations_circles"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$x = t$, $y = t^2$"],
    tags=["parametric"]
))

# Limits
register_concept(Concept(
    id="precalc.limits.intuitive",
    name="Limits (Intuitive Approach)",
    course_id="precalculus",
    unit_id="precalc_limits",
    topic_id="precalc_limits",
    kind="definition",
    description="Understanding limits intuitively; one-sided limits",
    prerequisites=["precalc.functions.domain_range"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$\\lim_{x \\to a} f(x) = L$"],
    tags=["limits"]
))

register_concept(Concept(
    id="precalc.limits.continuity",
    name="Continuity",
    course_id="precalculus",
    unit_id="precalc_limits",
    topic_id="precalc_continuity",
    kind="definition",
    description="Understanding continuity; identifying discontinuities",
    prerequisites=["precalc.limits.intuitive"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["Continuous at $x=a$ if $\\lim_{x \\to a} f(x) = f(a)$"],
    tags=["limits", "continuity"]
))
