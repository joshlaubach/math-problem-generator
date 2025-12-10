"""Calculus III concept map."""
from concepts import Concept, register_concept

# Vectors
register_concept(Concept(
    id="calc3.vectors.basics",
    name="Vector Operations",
    course_id="calculus_3",
    unit_id="calc3_vectors",
    topic_id="calc3_vector_basics",
    kind="definition",
    description="Vector addition, scalar multiplication, magnitude",
    prerequisites=["geo.coordinate.distance_midpoint"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$\\vec{v} = \\langle v_1, v_2, v_3 \\rangle$"],
    tags=["vectors"]
))

register_concept(Concept(
    id="calc3.vectors.dot_cross",
    name="Dot and Cross Products",
    course_id="calculus_3",
    unit_id="calc3_vectors",
    topic_id="calc3_dot_cross",
    kind="skill",
    description="Computing dot and cross products; applications",
    prerequisites=["calc3.vectors.basics"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$\\vec{u} \\cdot \\vec{v} = |\\vec{u}||\\vec{v}|\\cos(\\theta)$"],
    tags=["vectors"]
))

register_concept(Concept(
    id="calc3.vectors.curves",
    name="Curves in Space",
    course_id="calculus_3",
    unit_id="calc3_vectors",
    topic_id="calc3_curves",
    kind="skill",
    description="Parametric curves; velocity and acceleration; arc length",
    prerequisites=["calc3.vectors.basics", "precalc.parametric.equations"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$\\vec{r}(t) = \\langle t, t^2, t^3 \\rangle$"],
    tags=["curves"]
))

# Multivariable Calculus
register_concept(Concept(
    id="calc3.multivariable.partial_derivatives",
    name="Partial Derivatives",
    course_id="calculus_3",
    unit_id="calc3_multivariable",
    topic_id="calc3_partial_deriv",
    kind="skill",
    description="Computing partial derivatives; gradient vector",
    prerequisites=["calc1.derivatives.power_rule"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$\\frac{\\partial f}{\\partial x}$"],
    tags=["multivariable"]
))

register_concept(Concept(
    id="calc3.multivariable.double_integrals",
    name="Double Integrals",
    course_id="calculus_3",
    unit_id="calc3_multivariable",
    topic_id="calc3_multiple_integrals",
    kind="skill",
    description="Computing double integrals; Fubini's theorem",
    prerequisites=["calc1.integration.definite_integral"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$\\iint_R f(x,y) \\, dA$"],
    tags=["integration"]
))

register_concept(Concept(
    id="calc3.multivariable.triple_integrals",
    name="Triple Integrals",
    course_id="calculus_3",
    unit_id="calc3_multivariable",
    topic_id="calc3_triple_integrals",
    kind="skill",
    description="Computing triple integrals in rectangular, cylindrical, spherical",
    prerequisites=["calc3.multivariable.double_integrals"],
    difficulty_min=5,
    difficulty_max=6,
    examples_latex=["$\\iiint_W f(x,y,z) \\, dV$"],
    tags=["integration"]
))

# Vector Calculus
register_concept(Concept(
    id="calc3.vector_calc.fields",
    name="Vector Fields",
    course_id="calculus_3",
    unit_id="calc3_vector_calc",
    topic_id="calc3_vector_fields",
    kind="definition",
    description="Understanding vector fields; curl and divergence",
    prerequisites=["calc3.multivariable.partial_derivatives"],
    difficulty_min=5,
    difficulty_max=6,
    examples_latex=["$\\vec{F}(x,y) = \\langle P, Q \\rangle$"],
    tags=["vector_fields"]
))

register_concept(Concept(
    id="calc3.vector_calc.line_integrals",
    name="Line Integrals",
    course_id="calculus_3",
    unit_id="calc3_vector_calc",
    topic_id="calc3_line_integrals",
    kind="skill",
    description="Computing line integrals; conservative fields; potential functions",
    prerequisites=["calc3.vector_calc.fields"],
    difficulty_min=5,
    difficulty_max=6,
    examples_latex=["$\\int_C \\vec{F} \\cdot d\\vec{r}$"],
    tags=["line_integrals"]
))

register_concept(Concept(
    id="calc3.vector_calc.surface_integrals",
    name="Surface Integrals and Divergence Theorem",
    course_id="calculus_3",
    unit_id="calc3_vector_calc",
    topic_id="calc3_surface_integrals",
    kind="skill",
    description="Surface integrals; Stokes' theorem; divergence theorem",
    prerequisites=["calc3.vector_calc.line_integrals"],
    difficulty_min=5,
    difficulty_max=6,
    examples_latex=["$\\iint_S \\vec{F} \\cdot d\\vec{S}$"],
    tags=["surface_integrals"]
))
