"""
Algebra 1 Concept Map and Registry

Defines ~60 concepts across 8 major units of Algebra 1 curriculum.
Forms a DAG with prerequisites enabling intelligent sequencing and recommendations.

Units:
  1. Foundations (integer/fraction prerequisites)
  2. Expressions & Simplification
  3. Linear Equations
  4. Linear Inequalities
  5. Linear Functions & Graphs
  6. Systems of Equations/Inequalities
  7. Polynomials & Factoring
  8. Quadratic Functions & Equations
"""

from concepts import Concept, register_concept, validate_concept_graph, CONCEPTS, CONCEPTS


# ============================================================================
# UNIT 1: Foundations (Integer & Fraction Prerequisites)
# ============================================================================
# These are prerequisites used across multiple Algebra 1 units.
# Typically covered in Prealgebra but assumed knowledge in Algebra 1.

register_concept(
    Concept(
        id="pre.int.add_same_sign",
        name="Add Integers (Same Sign)",
        course_id="alg1",
        unit_id="alg1_unit_foundations",
        topic_id="alg1_foundations_integers",
        kind="skill",
        description="Add two integers with the same sign (e.g., 3 + 5, -3 + (-5))",
        prerequisites=[],
        difficulty_min=1,
        difficulty_max=1,
        examples_latex=[r"3 + 5", r"-3 + (-5)", r"12 + 8"],
        tags=["arithmetic", "integers", "prerequisite"],
    )
)

# Alias concept expected by some consumers for foundational integer operations
register_concept(
    Concept(
        id="alg1.foundations.add_subtract",
        name="Add and Subtract Integers",
        course_id="alg1",
        unit_id="alg1_unit_foundations",
        topic_id="alg1_foundations_integers",
        kind="skill",
        description="Add or subtract integers with sign rules (combines same-sign and different-sign cases)",
        prerequisites=["pre.int.add_same_sign", "pre.int.add_diff_sign"],
        difficulty_min=1,
        difficulty_max=2,
        examples_latex=[r"7 + (-3)", r"-5 - 8", r"12 - (-4)"],
        tags=["arithmetic", "integers", "prerequisite"],
    )
)

register_concept(
    Concept(
        id="pre.int.add_diff_sign",
        name="Add Integers (Different Signs)",
        course_id="alg1",
        unit_id="alg1_unit_foundations",
        topic_id="alg1_foundations_integers",
        kind="skill",
        description="Add two integers with different signs (e.g., 7 + (-3), -5 + 2)",
        prerequisites=["pre.int.add_same_sign"],
        difficulty_min=1,
        difficulty_max=2,
        examples_latex=[r"7 + (-3)", r"-5 + 2", r"10 - 7"],
        tags=["arithmetic", "integers", "prerequisite"],
    )
)

register_concept(
    Concept(
        id="pre.int.mul",
        name="Multiply Integers",
        course_id="alg1",
        unit_id="alg1_unit_foundations",
        topic_id="alg1_foundations_integers",
        kind="skill",
        description="Multiply integers including sign rules (positive × positive, negative × negative, mixed signs)",
        prerequisites=[],
        difficulty_min=1,
        difficulty_max=2,
        examples_latex=[r"3 \times 5", r"(-3) \times (-5)", r"3 \times (-5)"],
        tags=["arithmetic", "integers", "prerequisite"],
    )
)

register_concept(
    Concept(
        id="pre.int.div",
        name="Divide Integers",
        course_id="alg1",
        unit_id="alg1_unit_foundations",
        topic_id="alg1_foundations_integers",
        kind="skill",
        description="Divide integers with correct sign handling (e.g., 15 ÷ 3, -15 ÷ (-3), -15 ÷ 3)",
        prerequisites=["pre.int.mul"],
        difficulty_min=1,
        difficulty_max=2,
        examples_latex=[r"15 \div 3", r"(-15) \div (-3)", r"(-15) \div 3"],
        tags=["arithmetic", "integers", "prerequisite"],
    )
)

register_concept(
    Concept(
        id="pre.frac.simplify",
        name="Simplify Fractions",
        course_id="alg1",
        unit_id="alg1_unit_foundations",
        topic_id="alg1_foundations_fractions",
        kind="skill",
        description="Reduce fractions to lowest terms using GCF",
        prerequisites=[],
        difficulty_min=1,
        difficulty_max=2,
        examples_latex=[r"\frac{6}{9}", r"\frac{12}{18}", r"\frac{15}{25}"],
        tags=["arithmetic", "fractions", "prerequisite"],
    )
)

register_concept(
    Concept(
        id="pre.frac.add_same_den",
        name="Add Fractions (Same Denominator)",
        course_id="alg1",
        unit_id="alg1_unit_foundations",
        topic_id="alg1_foundations_fractions",
        kind="skill",
        description="Add fractions with same denominator",
        prerequisites=["pre.frac.simplify"],
        difficulty_min=1,
        difficulty_max=2,
        examples_latex=[r"\frac{2}{5} + \frac{1}{5}", r"\frac{3}{7} + \frac{2}{7}"],
        tags=["arithmetic", "fractions", "prerequisite"],
    )
)

register_concept(
    Concept(
        id="pre.frac.add_diff_den",
        name="Add Fractions (Different Denominators)",
        course_id="alg1",
        unit_id="alg1_unit_foundations",
        topic_id="alg1_foundations_fractions",
        kind="skill",
        description="Add fractions with different denominators using LCD",
        prerequisites=["pre.frac.add_same_den"],
        difficulty_min=2,
        difficulty_max=3,
        examples_latex=[r"\frac{1}{2} + \frac{1}{3}", r"\frac{2}{5} + \frac{3}{4}"],
        tags=["arithmetic", "fractions", "prerequisite"],
    )
)

# ============================================================================
# UNIT 2: Expressions & Simplification
# ============================================================================

register_concept(
    Concept(
        id="alg1.expr.variables_basic",
        name="Variables and Substitution",
        course_id="alg1",
        unit_id="alg1_unit_expressions",
        topic_id="alg1_expressions",
        kind="definition",
        description="Understand variables as unknown quantities and substitute values",
        prerequisites=[],
        difficulty_min=1,
        difficulty_max=2,
        examples_latex=[r"x + 5", r"3y", r"a - b"],
        tags=["algebra", "expressions", "variables"],
    )
)

register_concept(
    Concept(
        id="alg1.expr.combine_like_terms",
        name="Combine Like Terms",
        course_id="alg1",
        unit_id="alg1_unit_expressions",
        topic_id="alg1_expressions",
        kind="skill",
        description="Simplify expressions by combining terms with same variables/powers",
        prerequisites=["alg1.expr.variables_basic"],
        difficulty_min=1,
        difficulty_max=3,
        examples_latex=[r"3x + 5x - 2", r"2a + 3b + 4a - b"],
        tags=["algebra", "expressions", "simplification"],
    )
)

register_concept(
    Concept(
        id="alg1.expr.distributive_basic",
        name="Distributive Property (Basic)",
        course_id="alg1",
        unit_id="alg1_unit_expressions",
        topic_id="alg1_expressions",
        kind="skill",
        description="Expand expressions using a(b + c) = ab + ac",
        prerequisites=["alg1.expr.variables_basic", "pre.int.mul"],
        difficulty_min=1,
        difficulty_max=3,
        examples_latex=[r"3(x + 2)", r"2(4x - 1)"],
        tags=["algebra", "expressions", "distributive"],
    )
)

register_concept(
    Concept(
        id="alg1.expr.distributive_advanced",
        name="Distributive Property (Advanced)",
        course_id="alg1",
        unit_id="alg1_unit_expressions",
        topic_id="alg1_expressions",
        kind="skill",
        description="Expand complex expressions with multiple terms or nested distributions",
        prerequisites=["alg1.expr.distributive_basic", "alg1.expr.combine_like_terms"],
        difficulty_min=3,
        difficulty_max=4,
        examples_latex=[r"2(3x + 5y) - 4(x - 2)", r"-2(x - 3) + 5x"],
        tags=["algebra", "expressions", "distributive"],
    )
)

register_concept(
    Concept(
        id="alg1.expr.translate_words_to_expr",
        name="Translate Word Phrases to Expressions",
        course_id="alg1",
        unit_id="alg1_unit_expressions",
        topic_id="alg1_expressions",
        kind="skill",
        description="Write algebraic expressions from word descriptions",
        prerequisites=["alg1.expr.variables_basic"],
        difficulty_min=2,
        difficulty_max=4,
        examples_latex=[r"\text{5 more than } x", r"\text{twice a number}"],
        tags=["algebra", "expressions", "modeling"],
    )
)

# ============================================================================
# UNIT 3: Linear Equations (One Variable)
# ============================================================================

register_concept(
    Concept(
        id="alg1.linear_eq.one_step_int",
        name="One-Step Equations (Integers)",
        course_id="alg1",
        unit_id="alg1_unit_linear_equations",
        topic_id="alg1_linear_solve_one_var",
        kind="skill",
        description="Solve x + a = b or ax = b with integer coefficients",
        prerequisites=["alg1.expr.variables_basic", "pre.int.add_same_sign"],
        difficulty_min=1,
        difficulty_max=1,
        examples_latex=[r"x + 3 = 7", r"2x = 8", r"x - 5 = 2"],
        tags=["algebra", "equations", "linear"],
    )
)

register_concept(
    Concept(
        id="alg1.linear_eq.two_step_int",
        name="Two-Step Equations (Integers)",
        course_id="alg1",
        unit_id="alg1_unit_linear_equations",
        topic_id="alg1_linear_solve_one_var",
        kind="skill",
        description="Solve ax + b = c with integer coefficients",
        prerequisites=["alg1.linear_eq.one_step_int"],
        difficulty_min=2,
        difficulty_max=2,
        examples_latex=[r"2x + 3 = 11", r"3x - 5 = 10"],
        tags=["algebra", "equations", "linear"],
    )
)

register_concept(
    Concept(
        id="alg1.linear_eq.multistep_one_side",
        name="Multistep Equations (One Side)",
        course_id="alg1",
        unit_id="alg1_unit_linear_equations",
        topic_id="alg1_linear_solve_one_var",
        kind="skill",
        description="Solve equations with multiple operations and combining like terms on one side",
        prerequisites=["alg1.linear_eq.two_step_int", "alg1.expr.combine_like_terms"],
        difficulty_min=2,
        difficulty_max=3,
        examples_latex=[r"2x + 3x - 5 = 20", r"4(x + 1) = 12"],
        tags=["algebra", "equations", "linear"],
    )
)

register_concept(
    Concept(
        id="alg1.linear_eq.both_sides",
        name="Equations with Variables on Both Sides",
        course_id="alg1",
        unit_id="alg1_unit_linear_equations",
        topic_id="alg1_linear_solve_one_var",
        kind="skill",
        description="Solve equations with variables on both sides, collecting variable terms",
        prerequisites=["alg1.linear_eq.multistep_one_side"],
        difficulty_min=3,
        difficulty_max=3,
        examples_latex=[r"2x + 5 = x + 12", r"3x - 7 = x + 5"],
        tags=["algebra", "equations", "linear"],
    )
)

register_concept(
    Concept(
        id="alg1.linear_eq.rational_coeffs",
        name="Equations with Rational Coefficients",
        course_id="alg1",
        unit_id="alg1_unit_linear_equations",
        topic_id="alg1_linear_solve_one_var",
        kind="skill",
        description="Solve equations with fractions or decimals",
        prerequisites=["alg1.linear_eq.both_sides", "pre.frac.add_diff_den"],
        difficulty_min=3,
        difficulty_max=4,
        examples_latex=[r"\frac{x}{2} + 3 = 7", r"0.5x + 2 = 5"],
        tags=["algebra", "equations", "linear", "fractions"],
    )
)

register_concept(
    Concept(
        id="alg1.linear_eq.special_identity",
        name="Special Cases (Identity & Contradiction)",
        course_id="alg1",
        unit_id="alg1_unit_linear_equations",
        topic_id="alg1_linear_solve_one_var",
        kind="definition",
        description="Recognize and solve equations with no solution or infinitely many solutions",
        prerequisites=["alg1.linear_eq.both_sides"],
        difficulty_min=4,
        difficulty_max=5,
        examples_latex=[r"2x + 3 = 2x + 5", r"2x + 4 = 2(x + 2)"],
        tags=["algebra", "equations", "special cases"],
    )
)

# ============================================================================
# UNIT 4: Linear Inequalities (One Variable)
# ============================================================================

register_concept(
    Concept(
        id="pre.ineq.symbols_basic",
        name="Inequality Symbols and Number Line",
        course_id="alg1",
        unit_id="alg1_unit_inequalities",
        topic_id="alg1_linear_inequalities_one_var",
        kind="definition",
        description="Understand <, >, ≤, ≥ and represent inequalities on a number line",
        prerequisites=[],
        difficulty_min=1,
        difficulty_max=2,
        examples_latex=[r"x < 5", r"y \geq -2"],
        tags=["algebra", "inequalities", "prerequisite"],
    )
)

register_concept(
    Concept(
        id="alg1.linear_ineq.one_step_int",
        name="One-Step Inequalities (Integers)",
        course_id="alg1",
        unit_id="alg1_unit_inequalities",
        topic_id="alg1_linear_inequalities_one_var",
        kind="skill",
        description="Solve x + a > b or ax < b with addition/subtraction or multiplication by positive",
        prerequisites=["pre.ineq.symbols_basic", "pre.int.add_same_sign"],
        difficulty_min=1,
        difficulty_max=2,
        examples_latex=[r"x + 3 > 7", r"2x < 8"],
        tags=["algebra", "inequalities", "linear"],
    )
)

register_concept(
    Concept(
        id="alg1.linear_ineq.two_step_int",
        name="Two-Step Inequalities (Integers)",
        course_id="alg1",
        unit_id="alg1_unit_inequalities",
        topic_id="alg1_linear_inequalities_one_var",
        kind="skill",
        description="Solve ax + b > c with integer coefficients",
        prerequisites=["alg1.linear_ineq.one_step_int"],
        difficulty_min=2,
        difficulty_max=3,
        examples_latex=[r"2x + 3 > 11", r"3x - 5 \leq 10"],
        tags=["algebra", "inequalities", "linear"],
    )
)

register_concept(
    Concept(
        id="alg1.linear_ineq.negative_coeff_reverse",
        name="Inequalities with Negative Coefficients",
        course_id="alg1",
        unit_id="alg1_unit_inequalities",
        topic_id="alg1_linear_inequalities_one_var",
        kind="skill",
        description="Solve inequalities by multiplying/dividing by negative (reverse inequality sign)",
        prerequisites=["alg1.linear_ineq.two_step_int", "pre.int.mul"],
        difficulty_min=3,
        difficulty_max=3,
        examples_latex=[r"-2x + 5 > 1", r"-x < 4"],
        tags=["algebra", "inequalities", "linear"],
    )
)

register_concept(
    Concept(
        id="alg1.linear_ineq.rational_coeffs",
        name="Inequalities with Rational Coefficients",
        course_id="alg1",
        unit_id="alg1_unit_inequalities",
        topic_id="alg1_linear_inequalities_one_var",
        kind="skill",
        description="Solve inequalities with fractions or decimals",
        prerequisites=["alg1.linear_ineq.negative_coeff_reverse", "pre.frac.add_diff_den"],
        difficulty_min=3,
        difficulty_max=4,
        examples_latex=[r"\frac{x}{2} + 3 > 7", r"0.5x - 2 \leq 5"],
        tags=["algebra", "inequalities", "fractions"],
    )
)

register_concept(
    Concept(
        id="alg1.linear_ineq.compound",
        name="Compound Inequalities",
        course_id="alg1",
        unit_id="alg1_unit_inequalities",
        topic_id="alg1_linear_inequalities_one_var",
        kind="skill",
        description="Solve and graph compound inequalities (AND/OR)",
        prerequisites=["alg1.linear_ineq.rational_coeffs"],
        difficulty_min=4,
        difficulty_max=5,
        examples_latex=[r"-2 < x + 1 < 5", r"x < -1 \text{ or } x > 3"],
        tags=["algebra", "inequalities", "compound"],
    )
)

# ============================================================================
# UNIT 5: Linear Functions & Graphs
# ============================================================================

register_concept(
    Concept(
        id="alg1.linear_func.slope_from_two_points",
        name="Find Slope from Two Points",
        course_id="alg1",
        unit_id="alg1_unit_linear_functions",
        topic_id="alg1_linear_functions_graphs",
        kind="skill",
        description="Calculate slope using m = (y₂ - y₁) / (x₂ - x₁)",
        prerequisites=["pre.int.div", "alg1.expr.translate_words_to_expr"],
        difficulty_min=2,
        difficulty_max=3,
        examples_latex=[r"m = \frac{y_2 - y_1}{x_2 - x_1}", r"(2, 3) \text{ and } (5, 9)"],
        tags=["algebra", "functions", "slope"],
    )
)

register_concept(
    Concept(
        id="alg1.linear_func.slope_from_graph",
        name="Find Slope from Graph",
        course_id="alg1",
        unit_id="alg1_unit_linear_functions",
        topic_id="alg1_linear_functions_graphs",
        kind="skill",
        description="Determine slope by counting rise/run on a graph",
        prerequisites=["alg1.linear_func.slope_from_two_points"],
        difficulty_min=2,
        difficulty_max=3,
        examples_latex=[r"\text{rise} = 2, \text{run} = 3"],
        tags=["algebra", "functions", "slope", "visual"],
    )
)

register_concept(
    Concept(
        id="alg1.linear_func.slope_intercept_form",
        name="Slope-Intercept Form",
        course_id="alg1",
        unit_id="alg1_unit_linear_functions",
        topic_id="alg1_linear_functions_graphs",
        kind="definition",
        description="Understand y = mx + b form: m is slope, b is y-intercept",
        prerequisites=["alg1.linear_func.slope_from_graph"],
        difficulty_min=2,
        difficulty_max=3,
        examples_latex=[r"y = 2x + 3", r"y = -\frac{1}{2}x - 1"],
        tags=["algebra", "functions", "form"],
    )
)

register_concept(
    Concept(
        id="alg1.linear_func.graph_from_slope_intercept",
        name="Graph a Line from Slope-Intercept Form",
        course_id="alg1",
        unit_id="alg1_unit_linear_functions",
        topic_id="alg1_linear_functions_graphs",
        kind="skill",
        description="Plot a line using y-intercept and slope",
        prerequisites=["alg1.linear_func.slope_intercept_form"],
        difficulty_min=2,
        difficulty_max=3,
        examples_latex=[r"y = 2x + 1"],
        tags=["algebra", "functions", "graphing"],
    )
)

register_concept(
    Concept(
        id="alg1.linear_func.intercepts_x_y",
        name="Find x- and y-intercepts",
        course_id="alg1",
        unit_id="alg1_unit_linear_functions",
        topic_id="alg1_linear_functions_graphs",
        kind="skill",
        description="Find where line crosses axes by solving equations",
        prerequisites=["alg1.linear_eq.both_sides"],
        difficulty_min=2,
        difficulty_max=3,
        examples_latex=[r"2x + 3y = 6"],
        tags=["algebra", "functions", "intercepts"],
    )
)

register_concept(
    Concept(
        id="alg1.linear_func.write_equation_from_point_slope",
        name="Write Equation Given Point and Slope",
        course_id="alg1",
        unit_id="alg1_unit_linear_functions",
        topic_id="alg1_linear_functions_graphs",
        kind="skill",
        description="Use point-slope form or slope-intercept to write equation",
        prerequisites=["alg1.linear_func.slope_intercept_form"],
        difficulty_min=3,
        difficulty_max=4,
        examples_latex=[r"\text{slope } = 2, \text{ point } (1, 5)"],
        tags=["algebra", "functions", "writing equations"],
    )
)

register_concept(
    Concept(
        id="alg1.linear_func.model_from_word_problem",
        name="Model Situations with Linear Functions",
        course_id="alg1",
        unit_id="alg1_unit_linear_functions",
        topic_id="alg1_linear_functions_graphs",
        kind="skill",
        description="Write and interpret linear functions from real-world contexts",
        prerequisites=["alg1.linear_func.write_equation_from_point_slope", "alg1.expr.translate_words_to_expr"],
        difficulty_min=3,
        difficulty_max=5,
        examples_latex=[r"y = 15x + 20"],
        tags=["algebra", "functions", "modeling"],
    )
)

# ============================================================================
# UNIT 6: Systems of Equations & Inequalities
# ============================================================================

register_concept(
    Concept(
        id="alg1.systems.substitution",
        name="Solve Systems by Substitution",
        course_id="alg1",
        unit_id="alg1_unit_systems",
        topic_id="alg1_systems_linear",
        kind="skill",
        description="Solve 2x2 system by solving for one variable and substituting",
        prerequisites=["alg1.linear_eq.both_sides"],
        difficulty_min=3,
        difficulty_max=4,
        examples_latex=[r"y = 2x + 1; 3x + y = 10"],
        tags=["algebra", "systems", "substitution"],
    )
)

register_concept(
    Concept(
        id="alg1.systems.elimination_basic",
        name="Solve Systems by Elimination",
        course_id="alg1",
        unit_id="alg1_unit_systems",
        topic_id="alg1_systems_linear",
        kind="skill",
        description="Add/subtract equations to eliminate variable (no scaling needed)",
        prerequisites=["alg1.systems.substitution"],
        difficulty_min=3,
        difficulty_max=4,
        examples_latex=[r"x + y = 5; x - y = 1"],
        tags=["algebra", "systems", "elimination"],
    )
)

register_concept(
    Concept(
        id="alg1.systems.elimination_scaling",
        name="Solve Systems by Elimination (with Scaling)",
        course_id="alg1",
        unit_id="alg1_unit_systems",
        topic_id="alg1_systems_linear",
        kind="skill",
        description="Scale equations before adding/subtracting to eliminate variable",
        prerequisites=["alg1.systems.elimination_basic"],
        difficulty_min=4,
        difficulty_max=4,
        examples_latex=[r"2x + 3y = 7; 3x - 2y = 4"],
        tags=["algebra", "systems", "elimination"],
    )
)

register_concept(
    Concept(
        id="alg1.systems.special_no_solution",
        name="Systems with No Solution",
        course_id="alg1",
        unit_id="alg1_unit_systems",
        topic_id="alg1_systems_linear",
        kind="definition",
        description="Recognize parallel lines that never intersect (no solution)",
        prerequisites=["alg1.systems.elimination_scaling"],
        difficulty_min=4,
        difficulty_max=4,
        examples_latex=[r"y = 2x + 1; y = 2x - 3"],
        tags=["algebra", "systems", "special cases"],
    )
)

register_concept(
    Concept(
        id="alg1.systems.special_inf_solutions",
        name="Systems with Infinitely Many Solutions",
        course_id="alg1",
        unit_id="alg1_unit_systems",
        topic_id="alg1_systems_linear",
        kind="definition",
        description="Recognize same line written two ways (infinitely many solutions)",
        prerequisites=["alg1.systems.elimination_scaling"],
        difficulty_min=4,
        difficulty_max=4,
        examples_latex=[r"2x + 2y = 4; x + y = 2"],
        tags=["algebra", "systems", "special cases"],
    )
)

register_concept(
    Concept(
        id="alg1.systems_ineq.graph_system",
        name="Graph System of Inequalities",
        course_id="alg1",
        unit_id="alg1_unit_systems",
        topic_id="alg1_systems_inequalities",
        kind="skill",
        description="Graph region satisfying multiple linear inequalities",
        prerequisites=["alg1.linear_ineq.compound", "alg1.linear_func.graph_from_slope_intercept"],
        difficulty_min=4,
        difficulty_max=5,
        examples_latex=[r"y > x + 1; y < 2x"],
        tags=["algebra", "systems", "inequalities", "visual"],
    )
)

# ============================================================================
# UNIT 7: Polynomials & Factoring
# ============================================================================

register_concept(
    Concept(
        id="alg1.poly.add_sub",
        name="Add and Subtract Polynomials",
        course_id="alg1",
        unit_id="alg1_unit_polynomials",
        topic_id="alg1_polynomials",
        kind="skill",
        description="Combine like terms in polynomial addition/subtraction",
        prerequisites=["alg1.expr.combine_like_terms"],
        difficulty_min=2,
        difficulty_max=3,
        examples_latex=[r"(3x^2 + 2x) + (x^2 - 5)", r"(4x - 1) - (2x + 3)"],
        tags=["algebra", "polynomials", "operations"],
    )
)

register_concept(
    Concept(
        id="alg1.poly.mul_monomial",
        name="Multiply Monomial by Polynomial",
        course_id="alg1",
        unit_id="alg1_unit_polynomials",
        topic_id="alg1_polynomials",
        kind="skill",
        description="Distribute monomial across polynomial using distributive property",
        prerequisites=["alg1.expr.distributive_basic"],
        difficulty_min=2,
        difficulty_max=3,
        examples_latex=[r"2x(3x^2 + 4x - 1)"],
        tags=["algebra", "polynomials", "multiplication"],
    )
)

register_concept(
    Concept(
        id="alg1.poly.mul_binomials",
        name="Multiply Binomials (FOIL/Distributive)",
        course_id="alg1",
        unit_id="alg1_unit_polynomials",
        topic_id="alg1_polynomials",
        kind="skill",
        description="Multiply (a + b)(c + d) using FOIL or distributive property",
        prerequisites=["alg1.expr.distributive_advanced"],
        difficulty_min=3,
        difficulty_max=4,
        examples_latex=[r"(2x + 3)(x - 1)", r"(x + 2)^2"],
        tags=["algebra", "polynomials", "FOIL"],
    )
)

register_concept(
    Concept(
        id="alg1.factor.gcf",
        name="Factor Out Greatest Common Factor",
        course_id="alg1",
        unit_id="alg1_unit_factoring",
        topic_id="alg1_factoring",
        kind="skill",
        description="Find GCF and rewrite polynomial as product",
        prerequisites=["alg1.poly.mul_monomial"],
        difficulty_min=2,
        difficulty_max=3,
        examples_latex=[r"3x^2 + 6x", r"4x^3 + 8x^2 + 12x"],
        tags=["algebra", "factoring", "gcf"],
    )
)

register_concept(
    Concept(
        id="alg1.factor.trinomial_a1",
        name="Factor Trinomials (x² form)",
        course_id="alg1",
        unit_id="alg1_unit_factoring",
        topic_id="alg1_factoring",
        kind="skill",
        description="Factor x² + bx + c into (x + m)(x + n)",
        prerequisites=["alg1.poly.mul_binomials"],
        difficulty_min=3,
        difficulty_max=4,
        examples_latex=[r"x^2 + 5x + 6", r"x^2 - 3x - 10"],
        tags=["algebra", "factoring", "trinomials"],
    )
)

register_concept(
    Concept(
        id="alg1.factor.trinomial_general",
        name="Factor General Trinomials (ax² + bx + c)",
        course_id="alg1",
        unit_id="alg1_unit_factoring",
        topic_id="alg1_factoring",
        kind="skill",
        description="Factor ax² + bx + c where a ≠ 1",
        prerequisites=["alg1.factor.trinomial_a1"],
        difficulty_min=4,
        difficulty_max=5,
        examples_latex=[r"2x^2 + 7x + 3", r"3x^2 - 11x - 4"],
        tags=["algebra", "factoring", "trinomials"],
    )
)

register_concept(
    Concept(
        id="alg1.factor.diff_of_squares",
        name="Factor Difference of Squares",
        course_id="alg1",
        unit_id="alg1_unit_factoring",
        topic_id="alg1_factoring",
        kind="skill",
        description="Factor a² - b² = (a + b)(a - b)",
        prerequisites=["alg1.poly.mul_binomials"],
        difficulty_min=3,
        difficulty_max=4,
        examples_latex=[r"x^2 - 9", r"4x^2 - 25"],
        tags=["algebra", "factoring", "difference of squares"],
    )
)

# ============================================================================
# UNIT 8: Quadratic Functions & Equations
# ============================================================================

register_concept(
    Concept(
        id="alg1.quad.graph_standard_form",
        name="Graph Quadratics in Standard Form",
        course_id="alg1",
        unit_id="alg1_unit_quadratics",
        topic_id="alg1_quadratic_functions",
        kind="skill",
        description="Graph y = ax² + bx + c identifying vertex, axis of symmetry, intercepts",
        prerequisites=["alg1.linear_func.intercepts_x_y"],
        difficulty_min=4,
        difficulty_max=5,
        examples_latex=[r"y = x^2 - 4x + 3"],
        tags=["algebra", "quadratics", "graphing"],
    )
)

register_concept(
    Concept(
        id="alg1.quad.vertex_form_basic",
        name="Vertex Form (Basic)",
        course_id="alg1",
        unit_id="alg1_unit_quadratics",
        topic_id="alg1_quadratic_functions",
        kind="definition",
        description="Understand y = a(x - h)² + k with vertex (h, k)",
        prerequisites=["alg1.quad.graph_standard_form"],
        difficulty_min=4,
        difficulty_max=5,
        examples_latex=[r"y = (x - 2)^2 + 1"],
        tags=["algebra", "quadratics", "vertex form"],
    )
)

register_concept(
    Concept(
        id="alg1.quad.solve_by_factoring",
        name="Solve Quadratics by Factoring",
        course_id="alg1",
        unit_id="alg1_unit_quadratics",
        topic_id="alg1_quadratic_equations",
        kind="skill",
        description="Set quadratic = 0, factor, use zero product property to find solutions",
        prerequisites=["alg1.factor.trinomial_a1"],
        difficulty_min=3,
        difficulty_max=4,
        examples_latex=[r"x^2 + 5x + 6 = 0", r"2x^2 - 3x = 0"],
        tags=["algebra", "quadratics", "solving"],
    )
)

register_concept(
    Concept(
        id="alg1.quad.quadratic_formula",
        name="Quadratic Formula",
        course_id="alg1",
        unit_id="alg1_unit_quadratics",
        topic_id="alg1_quadratic_equations",
        kind="definition",
        description="Use x = (-b ± √(b² - 4ac)) / 2a to solve any quadratic",
        prerequisites=["alg1.quad.solve_by_factoring"],
        difficulty_min=4,
        difficulty_max=5,
        examples_latex=[r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}"],
        tags=["algebra", "quadratics", "formula"],
    )
)

register_concept(
    Concept(
        id="alg1.quad.discriminant_classify",
        name="Discriminant and Solution Classification",
        course_id="alg1",
        unit_id="alg1_unit_quadratics",
        topic_id="alg1_quadratic_equations",
        kind="skill",
        description="Use discriminant (b² - 4ac) to determine number and type of solutions",
        prerequisites=["alg1.quad.quadratic_formula"],
        difficulty_min=4,
        difficulty_max=5,
        examples_latex=[r"b^2 - 4ac"],
        tags=["algebra", "quadratics", "discriminant"],
    )
)

register_concept(
    Concept(
        id="alg1.quad.model_from_problem",
        name="Model Situations with Quadratics",
        course_id="alg1",
        unit_id="alg1_unit_quadratics",
        topic_id="alg1_quadratic_equations",
        kind="skill",
        description="Write and solve quadratic equations from real-world contexts (projectile, area, etc)",
        prerequisites=["alg1.quad.discriminant_classify", "alg1.linear_func.model_from_word_problem"],
        difficulty_min=5,
        difficulty_max=6,
        examples_latex=[r"h(t) = -16t^2 + 64t + 80"],
        tags=["algebra", "quadratics", "modeling"],
    )
)

# ============================================================================
# ============================================================================
# Validate the entire concept DAG at module load time
# ============================================================================
# ============================================================================

try:
    validate_concept_graph()
    print(f"✓ Algebra 1 concept graph validated: {len(CONCEPTS)} concepts registered")
except ValueError as e:
    print(f"✗ Concept graph validation failed:\n{e}")
    raise
