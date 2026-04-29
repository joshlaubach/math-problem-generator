"""
Taxonomy module for the math problem generator.

Defines the hierarchical structure: Course -> Unit -> Topic.
"""

from dataclasses import dataclass, field


@dataclass
class Topic:
    """Represents a specific topic within a unit."""
    id: str
    name: str
    description: str
    prerequisites: list[str] = field(default_factory=list)


@dataclass
class Unit:
    """Represents a unit within a course."""
    id: str
    name: str
    topics: list[Topic] = field(default_factory=list)


@dataclass
class Course:
    """Represents a course with units and topics."""
    id: str
    name: str
    units: list[Unit] = field(default_factory=list)


def get_algebra1_course() -> Course:
    """
    Returns a Course instance for Algebra I with units and topics.
    
    Course: Algebra I
    Unit: Linear equations and inequalities
    Topics: 
        - Solving one-variable linear equations
        - Solving one-variable linear inequalities
    """
    linear_equations_topic = Topic(
        id="alg1_linear_solve_one_var",
        name="Solving one-variable linear equations",
        description="Techniques for solving equations of the form ax + b = cx + d "
                    "and other one-variable linear equations.",
        prerequisites=[]
    )
    
    linear_inequalities_topic = Topic(
        id="alg1_linear_inequalities_one_var",
        name="Solving one-variable linear inequalities",
        description="Techniques for solving inequalities of the form ax + b < cx + d "
                    "and other one-variable linear inequalities, including proper "
                    "handling of inequality reversal with negative coefficients.",
        prerequisites=["alg1_linear_solve_one_var"]
    )
    
    unit = Unit(
        id="alg1_unit_linear_equations",
        name="Linear equations and inequalities",
        topics=[linear_equations_topic, linear_inequalities_topic]
    )
    
    course = Course(
        id="algebra_1",
        name="Algebra I",
        units=[unit]
    )
    
    return course


def get_prealgebra_course() -> Course:
    """Returns a Course instance for Pre-Algebra."""
    units = [
        Unit(
            id="prealg_integers",
            name="Integers and Operations",
            topics=[
                Topic(id="prealg_int_add_sub", name="Integer Addition and Subtraction", description=""),
                Topic(id="prealg_int_mul_div", name="Integer Multiplication and Division", description=""),
            ]
        ),
        Unit(
            id="prealg_fractions",
            name="Fractions and Decimals",
            topics=[
                Topic(id="prealg_frac_basics", name="Fraction Basics and Equivalence", description=""),
                Topic(id="prealg_frac_ops", name="Fraction Operations", description=""),
                Topic(id="prealg_decimals", name="Decimal Operations", description=""),
            ]
        ),
        Unit(
            id="prealg_ratios",
            name="Ratios, Proportions, and Percent",
            topics=[
                Topic(id="prealg_ratios_props", name="Ratios and Proportions", description=""),
                Topic(id="prealg_percent", name="Percentages and Applications", description=""),
            ]
        ),
    ]
    return Course(id="prealgebra", name="Pre-Algebra", units=units)


def get_algebra2_course() -> Course:
    """Returns a Course instance for Algebra II."""
    units = [
        Unit(
            id="alg2_quadratic",
            name="Quadratic Functions",
            topics=[
                Topic(id="alg2_quad_graphing", name="Graphing and Properties", description=""),
                Topic(id="alg2_quad_solving", name="Solving Quadratic Equations", description=""),
            ]
        ),
        Unit(
            id="alg2_polynomials",
            name="Polynomials and Factoring",
            topics=[
                Topic(id="alg2_poly_ops", name="Polynomial Operations", description=""),
                Topic(id="alg2_factoring", name="Factoring Techniques", description=""),
            ]
        ),
        Unit(
            id="alg2_rational",
            name="Rational Functions",
            topics=[
                Topic(id="alg2_rational_simplify", name="Simplifying Rational Expressions", description=""),
                Topic(id="alg2_rational_eqs", name="Rational Equations", description=""),
            ]
        ),
        Unit(
            id="alg2_exp_log",
            name="Exponential and Logarithmic Functions",
            topics=[
                Topic(id="alg2_exponential", name="Exponential Functions", description=""),
                Topic(id="alg2_logarithms", name="Logarithmic Functions", description=""),
            ]
        ),
        Unit(
            id="alg2_sequences",
            name="Sequences and Series",
            topics=[
                Topic(id="alg2_arithmetic_seq", name="Arithmetic Sequences", description=""),
                Topic(id="alg2_geometric_seq", name="Geometric Sequences", description=""),
            ]
        ),
    ]
    return Course(id="algebra_2", name="Algebra II", units=units)


def get_geometry_course() -> Course:
    """Returns a Course instance for Geometry."""
    units = [
        Unit(
            id="geo_foundations",
            name="Geometric Foundations",
            topics=[
                Topic(id="geo_points_lines", name="Points, Lines, and Angles", description=""),
                Topic(id="geo_angle_relationships", name="Angle Relationships", description=""),
            ]
        ),
        Unit(
            id="geo_triangles",
            name="Triangles",
            topics=[
                Topic(id="geo_triangle_congruence", name="Triangle Congruence", description=""),
                Topic(id="geo_triangle_similarity", name="Triangle Similarity", description=""),
                Topic(id="geo_triangle_properties", name="Special Triangle Properties", description=""),
            ]
        ),
        Unit(
            id="geo_polygons",
            name="Polygons and Quadrilaterals",
            topics=[
                Topic(id="geo_quad_properties", name="Quadrilateral Properties", description=""),
                Topic(id="geo_area_perimeter", name="Area and Perimeter", description=""),
            ]
        ),
        Unit(
            id="geo_circles",
            name="Circles",
            topics=[
                Topic(id="geo_circle_basics", name="Circle Fundamentals", description=""),
                Topic(id="geo_circle_angles", name="Angles in Circles", description=""),
                Topic(id="geo_arc_chord", name="Arcs and Chords", description=""),
            ]
        ),
        Unit(
            id="geo_coordinate",
            name="Coordinate Geometry",
            topics=[
                Topic(id="geo_coord_distance", name="Distance and Midpoint", description=""),
                Topic(id="geo_coord_slope", name="Slope and Lines", description=""),
            ]
        ),
        Unit(
            id="geo_transformations",
            name="Transformations and Symmetry",
            topics=[
                Topic(id="geo_translations", name="Translations", description=""),
                Topic(id="geo_reflections", name="Reflections", description=""),
                Topic(id="geo_rotations", name="Rotations", description=""),
            ]
        ),
    ]
    return Course(id="geometry", name="Geometry", units=units)


def get_precalculus_course() -> Course:
    """Returns a Course instance for Pre-Calculus and Trigonometry."""
    units = [
        Unit(
            id="precalc_functions",
            name="Functions and Families",
            topics=[
                Topic(id="precalc_func_basics", name="Function Basics", description=""),
                Topic(id="precalc_func_transforms", name="Function Transformations", description=""),
                Topic(id="precalc_func_composition", name="Function Composition", description=""),
            ]
        ),
        Unit(
            id="precalc_trig",
            name="Trigonometry",
            topics=[
                Topic(id="precalc_trig_ratios", name="Trigonometric Ratios", description=""),
                Topic(id="precalc_trig_identities", name="Trigonometric Identities", description=""),
                Topic(id="precalc_trig_equations", name="Trigonometric Equations", description=""),
            ]
        ),
        Unit(
            id="precalc_inverse",
            name="Inverse Functions and Trig",
            topics=[
                Topic(id="precalc_inverse_trig", name="Inverse Trigonometric Functions", description=""),
            ]
        ),
        Unit(
            id="precalc_polar",
            name="Polar and Parametric",
            topics=[
                Topic(id="precalc_polar_coords", name="Polar Coordinates", description=""),
                Topic(id="precalc_parametric", name="Parametric Equations", description=""),
            ]
        ),
        Unit(
            id="precalc_limits",
            name="Limits and Continuity",
            topics=[
                Topic(id="precalc_limits", name="Limits Fundamentals", description=""),
                Topic(id="precalc_continuity", name="Continuity", description=""),
            ]
        ),
    ]
    return Course(id="precalculus", name="Pre-Calculus and Trigonometry", units=units)


def get_calculus1_course() -> Course:
    """Returns a Course instance for Calculus I."""
    units = [
        Unit(
            id="calc1_limits",
            name="Limits and Continuity",
            topics=[
                Topic(id="calc1_limit_def", name="Limit Definition and Evaluation", description=""),
                Topic(id="calc1_continuity", name="Continuity and Discontinuity", description=""),
            ]
        ),
        Unit(
            id="calc1_derivatives",
            name="Derivatives",
            topics=[
                Topic(id="calc1_deriv_def", name="Derivative Definition", description=""),
                Topic(id="calc1_deriv_rules", name="Differentiation Rules", description=""),
                Topic(id="calc1_chain_rule", name="Chain Rule and Related Rates", description=""),
            ]
        ),
        Unit(
            id="calc1_applications",
            name="Applications of Derivatives",
            topics=[
                Topic(id="calc1_optimization", name="Optimization", description=""),
                Topic(id="calc1_extrema", name="Extrema and Concavity", description=""),
            ]
        ),
        Unit(
            id="calc1_integration",
            name="Integration",
            topics=[
                Topic(id="calc1_antiderivatives", name="Antiderivatives", description=""),
                Topic(id="calc1_definite_integral", name="Definite Integrals", description=""),
                Topic(id="calc1_ftc", name="Fundamental Theorem of Calculus", description=""),
            ]
        ),
    ]
    return Course(id="calculus_1", name="Calculus I", units=units)


def get_calculus2_course() -> Course:
    """Returns a Course instance for Calculus II."""
    units = [
        Unit(
            id="calc2_integration_tech",
            name="Techniques of Integration",
            topics=[
                Topic(id="calc2_integration_parts", name="Integration by Parts", description=""),
                Topic(id="calc2_partial_fractions", name="Partial Fractions", description=""),
                Topic(id="calc2_trig_substitution", name="Trigonometric Substitution", description=""),
            ]
        ),
        Unit(
            id="calc2_applications",
            name="Applications of Integration",
            topics=[
                Topic(id="calc2_area", name="Area Between Curves", description=""),
                Topic(id="calc2_volume", name="Volume of Solids", description=""),
                Topic(id="calc2_arc_length", name="Arc Length and Surface Area", description=""),
            ]
        ),
        Unit(
            id="calc2_sequences",
            name="Sequences and Series",
            topics=[
                Topic(id="calc2_sequences", name="Sequences", description=""),
                Topic(id="calc2_series_convergence", name="Series and Convergence", description=""),
                Topic(id="calc2_power_series", name="Power Series", description=""),
            ]
        ),
    ]
    return Course(id="calculus_2", name="Calculus II", units=units)


def get_calculus3_course() -> Course:
    """Returns a Course instance for Calculus III."""
    units = [
        Unit(
            id="calc3_vectors",
            name="Vectors and Space Curves",
            topics=[
                Topic(id="calc3_vector_basics", name="Vector Basics", description=""),
                Topic(id="calc3_dot_cross", name="Dot and Cross Products", description=""),
                Topic(id="calc3_curves", name="Curves in Space", description=""),
            ]
        ),
        Unit(
            id="calc3_multivariable",
            name="Multivariable Functions",
            topics=[
                Topic(id="calc3_partial_deriv", name="Partial Derivatives", description=""),
                Topic(id="calc3_multiple_integrals", name="Multiple Integrals", description=""),
                Topic(id="calc3_triple_integrals", name="Triple Integrals", description=""),
            ]
        ),
        Unit(
            id="calc3_vector_calc",
            name="Vector Calculus",
            topics=[
                Topic(id="calc3_vector_fields", name="Vector Fields", description=""),
                Topic(id="calc3_line_integrals", name="Line Integrals", description=""),
                Topic(id="calc3_surface_integrals", name="Surface Integrals", description=""),
            ]
        ),
    ]
    return Course(id="calculus_3", name="Calculus III", units=units)


def get_probstat_course() -> Course:
    """Returns a Course instance for Probability and Statistics."""
    units = [
        Unit(
            id="probstat_combinatorics",
            name="Combinatorics and Counting",
            topics=[
                Topic(id="probstat_permutations", name="Permutations", description=""),
                Topic(id="probstat_combinations", name="Combinations", description=""),
            ]
        ),
        Unit(
            id="probstat_probability",
            name="Probability",
            topics=[
                Topic(id="probstat_basic_prob", name="Basic Probability", description=""),
                Topic(id="probstat_conditional", name="Conditional Probability", description=""),
                Topic(id="probstat_random_variables", name="Random Variables", description=""),
            ]
        ),
        Unit(
            id="probstat_distributions",
            name="Distributions",
            topics=[
                Topic(id="probstat_discrete_dist", name="Discrete Distributions", description=""),
                Topic(id="probstat_continuous_dist", name="Continuous Distributions", description=""),
            ]
        ),
        Unit(
            id="probstat_statistics",
            name="Statistical Inference",
            topics=[
                Topic(id="probstat_descriptive", name="Descriptive Statistics", description=""),
                Topic(id="probstat_hypothesis", name="Hypothesis Testing", description=""),
                Topic(id="probstat_confidence", name="Confidence Intervals", description=""),
            ]
        ),
    ]
    return Course(id="probstat", name="Probability and Statistics", units=units)


def get_linearalgebra_course() -> Course:
    """Returns a Course instance for Linear Algebra."""
    units = [
        Unit(
            id="linalg_vectors",
            name="Vectors and Vector Spaces",
            topics=[
                Topic(id="linalg_vector_basics", name="Vector Operations", description=""),
                Topic(id="linalg_subspaces", name="Subspaces", description=""),
            ]
        ),
        Unit(
            id="linalg_matrices",
            name="Matrices",
            topics=[
                Topic(id="linalg_matrix_ops", name="Matrix Operations", description=""),
                Topic(id="linalg_determinants", name="Determinants", description=""),
                Topic(id="linalg_inverse", name="Matrix Inverse", description=""),
            ]
        ),
        Unit(
            id="linalg_systems",
            name="Systems of Linear Equations",
            topics=[
                Topic(id="linalg_gauss_elimination", name="Gaussian Elimination", description=""),
                Topic(id="linalg_rank_nullity", name="Rank and Nullity", description=""),
            ]
        ),
        Unit(
            id="linalg_eigenvalues",
            name="Eigenvalues and Eigenvectors",
            topics=[
                Topic(id="linalg_characteristic_poly", name="Characteristic Polynomial", description=""),
                Topic(id="linalg_diagonalization", name="Diagonalization", description=""),
            ]
        ),
    ]
    return Course(id="linear_algebra", name="Linear Algebra", units=units)


def get_diffeq_course() -> Course:
    """Returns a Course instance for Differential Equations."""
    units = [
        Unit(
            id="diffeq_firstorder",
            name="First Order Differential Equations",
            topics=[
                Topic(id="diffeq_separable", name="Separable Equations", description=""),
                Topic(id="diffeq_linear_first", name="Linear First Order", description=""),
            ]
        ),
        Unit(
            id="diffeq_highorder",
            name="Higher Order Linear Equations",
            topics=[
                Topic(id="diffeq_linear_const", name="Linear with Constant Coefficients", description=""),
                Topic(id="diffeq_nonhomogeneous", name="Nonhomogeneous Equations", description=""),
            ]
        ),
        Unit(
            id="diffeq_systems",
            name="Systems of Differential Equations",
            topics=[
                Topic(id="diffeq_linear_systems", name="Linear Systems", description=""),
                Topic(id="diffeq_qualitative", name="Qualitative Analysis", description=""),
            ]
        ),
    ]
    return Course(id="differential_equations", name="Differential Equations", units=units)


def get_proofs_course() -> Course:
    """Returns a Course instance for Proofs and Contest Math."""
    units = [
        Unit(
            id="proofs_logic",
            name="Logic and Proof Techniques",
            topics=[
                Topic(id="proofs_logic_basics", name="Logic Basics", description=""),
                Topic(id="proofs_direct", name="Direct Proof", description=""),
                Topic(id="proofs_contradiction", name="Proof by Contradiction", description=""),
                Topic(id="proofs_induction", name="Mathematical Induction", description=""),
            ]
        ),
        Unit(
            id="proofs_inequalities",
            name="Inequalities and Optimization",
            topics=[
                Topic(id="proofs_ineq_techniques", name="Inequality Techniques", description=""),
                Topic(id="proofs_optimization", name="Optimization Problems", description=""),
            ]
        ),
        Unit(
            id="proofs_numbertheory",
            name="Number Theory Basics",
            topics=[
                Topic(id="proofs_divisibility", name="Divisibility and Primes", description=""),
                Topic(id="proofs_modular", name="Modular Arithmetic", description=""),
            ]
        ),
        Unit(
            id="proofs_combinatorics",
            name="Combinatorics",
            topics=[
                Topic(id="proofs_counting", name="Counting Techniques", description=""),
                Topic(id="proofs_graph_theory", name="Basic Graph Theory", description=""),
            ]
        ),
    ]
    return Course(id="proofs_contest", name="Proofs and Contest Math", units=units)


def get_sat_course() -> Course:
    """Returns a Course instance for SAT Math."""
    units = [
        Unit(
            id="sat_algebra",
            name="SAT Algebra",
            topics=[
                Topic(id="sat_linear", name="Linear Equations and Inequalities", description=""),
                Topic(id="sat_quadratic", name="Quadratic Functions", description=""),
                Topic(id="sat_systems", name="Systems of Equations", description=""),
            ]
        ),
        Unit(
            id="sat_geometry",
            name="SAT Geometry",
            topics=[
                Topic(id="sat_geo_shapes", name="Shapes and Area", description=""),
                Topic(id="sat_geo_trig", name="Trigonometry Basics", description=""),
            ]
        ),
        Unit(
            id="sat_numbers",
            name="SAT Numbers and Operations",
            topics=[
                Topic(id="sat_ratios", name="Ratios and Percentages", description=""),
                Topic(id="sat_exponents", name="Exponents and Radicals", description=""),
            ]
        ),
        Unit(
            id="sat_data",
            name="SAT Data Analysis",
            topics=[
                Topic(id="sat_statistics", name="Statistics and Probability", description=""),
            ]
        ),
    ]
    return Course(id="sat_math", name="SAT Math", units=units)


def get_ap_calc_ab_course() -> Course:
    """Returns a Course instance for AP Calculus AB."""
    units = [
        Unit(
            id="ap_ab_limits",
            name="Limits and Continuity",
            topics=[
                Topic(id="ap_ab_limit_eval", name="Limit Evaluation", description=""),
                Topic(id="ap_ab_continuity", name="Continuity", description=""),
            ]
        ),
        Unit(
            id="ap_ab_derivatives",
            name="Derivatives",
            topics=[
                Topic(id="ap_ab_deriv_def", name="Derivative Definition", description=""),
                Topic(id="ap_ab_deriv_rules", name="Differentiation Rules", description=""),
            ]
        ),
        Unit(
            id="ap_ab_applications",
            name="Applications of Derivatives",
            topics=[
                Topic(id="ap_ab_curve_sketch", name="Curve Sketching", description=""),
                Topic(id="ap_ab_optimization", name="Optimization", description=""),
            ]
        ),
        Unit(
            id="ap_ab_integration",
            name="Integration",
            topics=[
                Topic(id="ap_ab_antiderivatives", name="Antiderivatives", description=""),
                Topic(id="ap_ab_definite_int", name="Definite Integrals", description=""),
            ]
        ),
    ]
    return Course(id="ap_calc_ab", name="AP Calculus AB", units=units)


def get_ap_calc_bc_course() -> Course:
    """Returns a Course instance for AP Calculus BC."""
    units = [
        Unit(
            id="ap_bc_parametric",
            name="Parametric and Polar",
            topics=[
                Topic(id="ap_bc_parametric_eq", name="Parametric Equations", description=""),
                Topic(id="ap_bc_polar", name="Polar Functions", description=""),
            ]
        ),
        Unit(
            id="ap_bc_series",
            name="Sequences and Series",
            topics=[
                Topic(id="ap_bc_sequences", name="Sequences", description=""),
                Topic(id="ap_bc_series_conv", name="Series and Convergence", description=""),
                Topic(id="ap_bc_power_series", name="Power Series", description=""),
            ]
        ),
        Unit(
            id="ap_bc_integration_adv",
            name="Advanced Integration",
            topics=[
                Topic(id="ap_bc_integration_parts", name="Integration by Parts", description=""),
                Topic(id="ap_bc_partial_frac", name="Partial Fractions", description=""),
            ]
        ),
    ]
    return Course(id="ap_calc_bc", name="AP Calculus BC", units=units)


def get_ap_stats_course() -> Course:
    """Returns a Course instance for AP Statistics."""
    units = [
        Unit(
            id="ap_stats_exploratory",
            name="Exploratory Data Analysis",
            topics=[
                Topic(id="ap_stats_display", name="Displaying Data", description=""),
                Topic(id="ap_stats_measures", name="Summary Statistics", description=""),
            ]
        ),
        Unit(
            id="ap_stats_probability",
            name="Probability and Distributions",
            topics=[
                Topic(id="ap_stats_basic_prob", name="Basic Probability", description=""),
                Topic(id="ap_stats_normal", name="Normal Distribution", description=""),
                Topic(id="ap_stats_sampling", name="Sampling Distributions", description=""),
            ]
        ),
        Unit(
            id="ap_stats_inference",
            name="Statistical Inference",
            topics=[
                Topic(id="ap_stats_confidence", name="Confidence Intervals", description=""),
                Topic(id="ap_stats_hypothesis", name="Hypothesis Tests", description=""),
            ]
        ),
    ]
    return Course(id="ap_stats", name="AP Statistics", units=units)
