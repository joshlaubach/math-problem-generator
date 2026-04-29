"""Algebra II concept map."""
from concepts import Concept, register_concept

register_concept(Concept(
    id="alg2.quadratic.standard_form",
    name="Quadratic Standard Form",
    course_id="algebra_2",
    unit_id="alg2_quadratic",
    topic_id="alg2_quad_graphing",
    kind="definition",
    description="Understanding quadratic functions in standard form",
    prerequisites=["alg1.linear_func.slope_from_two_points"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$f(x) = ax^2 + bx + c$"],
    tags=["quadratic"]
))

register_concept(Concept(
    id="alg2.quadratic.vertex_form",
    name="Vertex Form and Transformations",
    course_id="algebra_2",
    unit_id="alg2_quadratic",
    topic_id="alg2_quad_graphing",
    kind="skill",
    description="Converting to vertex form; understanding transformations",
    prerequisites=["alg2.quadratic.standard_form"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$f(x) = a(x-h)^2 + k$"],
    tags=["quadratic", "transformations"]
))

register_concept(Concept(
    id="alg2.quadratic.solving_methods",
    name="Methods for Solving Quadratics",
    course_id="algebra_2",
    unit_id="alg2_quadratic",
    topic_id="alg2_quad_solving",
    kind="skill",
    description="Factoring, completing the square, quadratic formula",
    prerequisites=["alg2.quadratic.standard_form"],
    difficulty_min=3,
    difficulty_max=5,
    examples_latex=["$x = \\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}$"],
    tags=["quadratic", "solving"]
))

register_concept(Concept(
    id="alg2.polynomials.operations",
    name="Polynomial Addition and Multiplication",
    course_id="algebra_2",
    unit_id="alg2_polynomials",
    topic_id="alg2_poly_ops",
    kind="skill",
    description="Operations with polynomials of higher degree",
    prerequisites=["alg1.poly.add_sub"],
    difficulty_min=2,
    difficulty_max=4,
    examples_latex=["$(x^2+3x+2)(x+1)$"],
    tags=["polynomials"]
))

register_concept(Concept(
    id="alg2.polynomials.factoring_techniques",
    name="Advanced Factoring Techniques",
    course_id="algebra_2",
    unit_id="alg2_polynomials",
    topic_id="alg2_factoring",
    kind="skill",
    description="Factoring higher degree polynomials; grouping; special forms",
    prerequisites=["alg1.factor.trinomial_simple"],
    difficulty_min=3,
    difficulty_max=5,
    examples_latex=["$x^3 - 1 = (x-1)(x^2+x+1)$"],
    tags=["polynomials", "factoring"]
))

register_concept(Concept(
    id="alg2.rational.simplification",
    name="Simplifying Rational Expressions",
    course_id="algebra_2",
    unit_id="alg2_rational",
    topic_id="alg2_rational_simplify",
    kind="skill",
    description="Factoring and canceling in rational expressions",
    prerequisites=["alg2.polynomials.factoring_techniques"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$\\frac{x^2-1}{x-1} = x+1$"],
    tags=["rational", "simplification"]
))

register_concept(Concept(
    id="alg2.rational.operations",
    name="Operations with Rational Expressions",
    course_id="algebra_2",
    unit_id="alg2_rational",
    topic_id="alg2_rational_eqs",
    kind="skill",
    description="Adding, subtracting, multiplying, dividing rational expressions",
    prerequisites=["alg2.rational.simplification"],
    difficulty_min=3,
    difficulty_max=5,
    examples_latex=["$\\frac{1}{x} + \\frac{1}{x+1}$"],
    tags=["rational"]
))

register_concept(Concept(
    id="alg2.exponential.growth_decay",
    name="Exponential Growth and Decay",
    course_id="algebra_2",
    unit_id="alg2_exp_log",
    topic_id="alg2_exponential",
    kind="definition",
    description="Understanding exponential functions; applications",
    prerequisites=["alg1.linear_func.model_from_word_problem"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$A = Pe^{rt}$", "$P(t) = P_0 \\cdot 2^{t/d}$"],
    tags=["exponential"]
))

register_concept(Concept(
    id="alg2.logarithms.definition",
    name="Logarithms as Inverse Exponentials",
    course_id="algebra_2",
    unit_id="alg2_exp_log",
    topic_id="alg2_logarithms",
    kind="definition",
    description="Understanding logarithms; converting between exponential and logarithmic form",
    prerequisites=["alg2.exponential.growth_decay"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$\\log_b(x) = y \\Leftrightarrow b^y = x$"],
    tags=["logarithms"]
))

register_concept(Concept(
    id="alg2.logarithms.properties",
    name="Logarithm Properties and Equations",
    course_id="algebra_2",
    unit_id="alg2_exp_log",
    topic_id="alg2_logarithms",
    kind="skill",
    description="Properties of logarithms; solving logarithmic equations",
    prerequisites=["alg2.logarithms.definition"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$\\log(ab) = \\log(a) + \\log(b)$"],
    tags=["logarithms"]
))

register_concept(Concept(
    id="alg2.sequences.arithmetic",
    name="Arithmetic Sequences and Series",
    course_id="algebra_2",
    unit_id="alg2_sequences",
    topic_id="alg2_arithmetic_seq",
    kind="definition",
    description="Understanding arithmetic sequences; finding terms and sums",
    prerequisites=["alg1.expr.translate_words_to_expr"],
    difficulty_min=2,
    difficulty_max=4,
    examples_latex=["$a_n = a_1 + (n-1)d$"],
    tags=["sequences"]
))

register_concept(Concept(
    id="alg2.sequences.geometric",
    name="Geometric Sequences and Series",
    course_id="algebra_2",
    unit_id="alg2_sequences",
    topic_id="alg2_geometric_seq",
    kind="definition",
    description="Understanding geometric sequences; finding terms and sums",
    prerequisites=["alg2.exponential.growth_decay"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$a_n = a_1 \\cdot r^{n-1}$"],
    tags=["sequences"]
))
