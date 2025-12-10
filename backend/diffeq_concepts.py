"""Differential Equations concept map."""
from concepts import Concept, register_concept

# First Order
register_concept(Concept(
    id="diffeq.firstorder.separable",
    name="Separable Differential Equations",
    course_id="differential_equations",
    unit_id="diffeq_firstorder",
    topic_id="diffeq_separable",
    kind="skill",
    description="Solving separable first-order ODEs",
    prerequisites=["calc1.integration.substitution"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$\\frac{dy}{dx} = f(x)g(y)$"],
    tags=["ode"]
))

register_concept(Concept(
    id="diffeq.firstorder.linear",
    name="Linear First-Order Differential Equations",
    course_id="differential_equations",
    unit_id="diffeq_firstorder",
    topic_id="diffeq_linear_first",
    kind="skill",
    description="Solving linear first-order ODEs with integrating factor",
    prerequisites=["diffeq.firstorder.separable"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$\\frac{dy}{dx} + P(x)y = Q(x)$"],
    tags=["ode"]
))

register_concept(Concept(
    id="diffeq.firstorder.applications",
    name="Applications of First-Order Equations",
    course_id="differential_equations",
    unit_id="diffeq_firstorder",
    topic_id="diffeq_separable",
    kind="skill",
    description="Exponential growth/decay, mixing problems",
    prerequisites=["diffeq.firstorder.linear"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$\\frac{dA}{dt} = rA$"],
    tags=["applications"]
))

# Higher Order
register_concept(Concept(
    id="diffeq.highorder.linear_constant",
    name="Linear ODEs with Constant Coefficients",
    course_id="differential_equations",
    unit_id="diffeq_highorder",
    topic_id="diffeq_linear_const",
    kind="skill",
    description="Solving linear homogeneous ODEs with constant coefficients",
    prerequisites=["diffeq.firstorder.applications", "linalg.eigen.characteristic_polynomial"],
    difficulty_min=5,
    difficulty_max=6,
    examples_latex=["$a\\frac{d^2y}{dx^2} + b\\frac{dy}{dx} + cy = 0$"],
    tags=["ode"]
))

register_concept(Concept(
    id="diffeq.highorder.nonhomogeneous",
    name="Nonhomogeneous Linear Equations",
    course_id="differential_equations",
    unit_id="diffeq_highorder",
    topic_id="diffeq_nonhomogeneous",
    kind="skill",
    description="Method of undetermined coefficients; variation of parameters",
    prerequisites=["diffeq.highorder.linear_constant"],
    difficulty_min=5,
    difficulty_max=6,
    examples_latex=["$ay'' + by' + cy = f(x)$"],
    tags=["ode"]
))

# Systems
register_concept(Concept(
    id="diffeq.systems.linear_systems",
    name="Systems of Linear Differential Equations",
    course_id="differential_equations",
    unit_id="diffeq_systems",
    topic_id="diffeq_linear_systems",
    kind="skill",
    description="Solving systems using matrices and eigenvalues",
    prerequisites=["diffeq.highorder.nonhomogeneous", "linalg.eigen.diagonalization"],
    difficulty_min=5,
    difficulty_max=6,
    examples_latex=["$\\frac{d\\vec{x}}{dt} = A\\vec{x}$"],
    tags=["systems"]
))

register_concept(Concept(
    id="diffeq.systems.phase_plane",
    name="Qualitative Analysis and Phase Plane",
    course_id="differential_equations",
    unit_id="diffeq_systems",
    topic_id="diffeq_qualitative",
    kind="skill",
    description="Phase plane analysis; stability; critical points",
    prerequisites=["diffeq.systems.linear_systems"],
    difficulty_min=5,
    difficulty_max=6,
    examples_latex=["Equilibrium points", "Stability analysis"],
    tags=["qualitative"]
))
