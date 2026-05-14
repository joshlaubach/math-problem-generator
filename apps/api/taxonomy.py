"""
Taxonomy module for the math problem generator.

Defines the hierarchical structure: Course -> Unit -> Topic.
"""

from dataclasses import dataclass, field
from typing import Literal

CalcMode = Literal["none", "scientific", "graphing", "cas"]


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
    is_honors: bool = False  # auto-detected from "(H)" suffix in name


@dataclass
class Course:
    """Represents a course with units and topics."""
    id: str
    name: str
    units: list[Unit] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Unit-level calculator mode defaults
# All topics in a unit inherit this mode unless overridden individually.
# ---------------------------------------------------------------------------
UNIT_CALC_DEFAULTS: dict[str, CalcMode] = {
    # Pre-Algebra — foundational arithmetic, all exact by hand
    "pa_u01": "none", "pa_u02": "none", "pa_u03": "none", "pa_u04": "none",
    "pa_u05": "none", "pa_u06": "none", "pa_u07": "none",

    # Algebra I
    "a1_u01": "none", "a1_u02": "none", "a1_u03": "none", "a1_u04": "none",
    "a1_u05": "none",
    "a1_u06": "scientific",  # Exponential Functions — growth/decay, large exponents
    "a1_u07": "none", "a1_u08": "none", "a1_u09": "none",
    "a1_u10": "scientific",  # Radical Functions — irrational roots
    "a1_u11": "scientific",  # Data Analysis — σ, mean, spread

    # Geometry
    "geo_u01": "none", "geo_u02": "none", "geo_u03": "none", "geo_u04": "none",
    "geo_u05": "none", "geo_u06": "none", "geo_u07": "none", "geo_u08": "none",
    "geo_u09": "scientific",  # Right Triangles — sin/cos/tan of arbitrary angles
    "geo_u10": "none",        # Circles — exact arc/sector formulas
    "geo_u11": "scientific",  # Area and Volume — decimal π computations
    "geo_u12": "none",

    # Algebra II
    "a2_u01": "none", "a2_u02": "none", "a2_u03": "none",
    "a2_u04": "graphing",    # Polynomial Functions — irrational zeros via graphing
    "a2_u05": "scientific",  # Rational Exponents and Radicals
    "a2_u06": "scientific",  # Exponential and Logarithmic Functions
    "a2_u07": "graphing",    # Rational Functions — asymptote/zero analysis
    "a2_u08": "scientific",  # Sequences and Series — large sums
    "a2_u09": "graphing",    # Trigonometric Functions — graphing waves
    "a2_u10": "scientific",  # Probability — large combinations
    "a2_u11": "scientific",  # Data Analysis and Statistics

    # Pre-Calculus
    "pc_u01": "graphing", "pc_u02": "graphing",
    "pc_u03": "scientific",  # Exponential and Logarithmic Functions
    "pc_u04": "graphing",    # Trigonometric Functions — graphing waves
    "pc_u05": "none",        # Analytic Trigonometry — identity proofs
    "pc_u06": "scientific",  # Law of Sines/Cosines
    "pc_u07": "graphing",    # Linear Systems and Matrices
    "pc_u08": "scientific",  # Sequences, Series, Probability
    "pc_u09": "graphing",    # Analytic Geometry — conics
    "pc_u10": "graphing",    # (H) Analytic Geometry in 3D
    "pc_u11": "graphing",    # (H) Limits and Introduction to Calculus

    # Calculus I
    "c1_u01": "graphing",    # Limits — graphical limit analysis
    "c1_u02": "none",        # Derivative Rules — symbolic
    "c1_u03": "graphing",    # Applications of Derivatives — curve sketching
    "c1_u04": "none",        # Integrals — symbolic antidifferentiation
    "c1_u05": "graphing",    # Applications of Integrals
    "c1_u06": "graphing",    # First Order DEs — slope fields

    # Calculus II
    "c2_u01": "cas",         # Integration Techniques — exact symbolic
    "c2_u02": "graphing",    # Further Applications
    "c2_u03": "graphing",    # Parametric and Polar
    "c2_u04": "cas",         # Series and Power Series

    # Calculus III
    "c3_u01": "graphing", "c3_u02": "graphing", "c3_u03": "graphing",
    "c3_u04": "cas",         # Multiple Integrals
    "c3_u05": "cas",         # Vector Calculus — Stokes, divergence
    "c3_u06": "graphing",    # Second Order DEs

    # Differential Equations
    "de_u01": "scientific",  # First Order DEs
    "de_u02": "graphing",    # Numerical Methods — Euler, RK4
    "de_u03": "scientific",  # Second Order DEs
    "de_u04": "graphing",    # Phase Plane Analysis
    "de_u05": "scientific",  # Higher Order DEs
    "de_u06": "graphing",     # Laplace Transforms — CAS not typically permitted in DiffEQ courses
    "de_u07": "graphing",     # Series Solutions
    "de_u08": "graphing",     # Matrix Methods — eigenvalue computation
    "de_u09": "graphing",     # (H) Partial Differential Equations

    # Linear Algebra
    "la_u01": "none", "la_u02": "none", "la_u03": "none", "la_u04": "none",
    "la_u05": "none", "la_u06": "none",
    "la_u07": "cas",         # Eigenvalues — 4×4+ characteristic polynomials
    "la_u08": "cas",         # Inner Product Spaces — Gram-Schmidt, QR
    "la_u09": "cas",         # (H) Operators on Inner Product Spaces
    "la_u10": "cas",         # (H) Operators on Complex Vector Spaces
    "la_u11": "cas",         # (H) Multilinear Algebra

    # Discrete Math
    "dm_u01": "none", "dm_u02": "none", "dm_u03": "none", "dm_u04": "none",
    "dm_u05": "none", "dm_u06": "none",
    "dm_u07": "scientific",  # Combinatorics — large factorials
    "dm_u08": "none", "dm_u09": "none",
    "dm_u10": "none",        # (H) Boolean Algebra and Automata

    # Proofs — all pen-and-paper
    "pf_u01": "none", "pf_u02": "none", "pf_u03": "none", "pf_u04": "none",
    "pf_u05": "none", "pf_u06": "none", "pf_u07": "none", "pf_u08": "none",

    # Contest Math — competitions prohibit calculators
    "cm_u01": "none", "cm_u02": "none", "cm_u03": "none", "cm_u04": "none",
    "cm_u05": "none", "cm_u06": "none", "cm_u07": "none", "cm_u08": "none",

    # Probability
    # Intro Probability and Statistics (AP Stats level, no calculus)
    "ips_u01": "scientific",  # Exploring Data — σ, z-scores
    "ips_u02": "graphing",    # Bivariate Data — scatterplots, regression
    "ips_u03": "none",        # Study Design — conceptual
    "ips_u04": "none",        # Intro Probability — exact calculations
    "ips_u05": "scientific",  # Counting — large factorials
    "ips_u06": "none",        # Conditional Probability — exact
    "ips_u07": "scientific",  # Discrete RVs — binomial, geometric
    "ips_u08": "scientific",  # Normal Distribution — z-scores, CDF
    "ips_u09": "scientific",  # Sampling Distributions — CLT approximations
    "ips_u10": "scientific",  # Estimation — CI calculations
    "ips_u11": "scientific",  # Hypothesis Testing — test statistics
    "ips_u12": "scientific",  # Categorical Data — chi-square
    "ips_u13": "scientific",  # Regression Inference — t-statistics

    # Probability Theory (STAT-134, calculus-based)
    # prob_u04 requires Calculus III (multiple integrals)
    # prob_u06 requires Calculus II (Taylor series for MGFs)
    "prob_u01": "none",        # Probability Axioms — formal proofs
    "prob_u02": "scientific",  # Discrete Distributions — Poisson, MGFs
    "prob_u03": "scientific",  # Continuous Distributions — PDFs, CDFs
    "prob_u04": "cas",         # Joint Distributions — double integrals (Calc III)
    "prob_u05": "cas",         # Conditional Expectation — integration
    "prob_u06": "cas",         # Transforms and Sums — MGFs via Taylor series (Calc II)
    "prob_u07": "cas",         # Special Distributions — Jacobians, multivariate
    "prob_u08": "scientific",  # Limit Theorems — convergence results
    "prob_u09": "scientific",  # Markov Chains — matrix methods

    # Mathematical Statistics (STAT-135 + Applied Econometrics)
    "ms_u01": "scientific",   # Statistical Models and Estimation
    "ms_u02": "scientific",   # Information Bounds — Fisher information
    "ms_u03": "scientific",   # Bayesian Inference
    "ms_u04": "scientific",   # Hypothesis Testing Theory
    "ms_u05": "scientific",   # Asymptotic Theory
    "ms_u06": "scientific",   # Nonparametric Methods
    "ms_u07": "cas",          # Linear Models — matrix algebra
    "ms_u08": "scientific",   # Generalized Linear Models
    "ms_u09": "scientific",   # Applied Econometrics (H)

    # Statistics
    # (stat_u* units retired — content moved to intro_prob_stats and mathematical_statistics)
}


# ---------------------------------------------------------------------------
# Pre-Algebra
# ---------------------------------------------------------------------------

def get_prealgebra_course() -> Course:
    return Course(id="prealgebra", name="Pre-Algebra", units=[
        Unit(id="pa_u01", name="Introduction to Integers", topics=[
            Topic(id="pa_001", name="Understanding Positive and Negative Numbers", description=""),
            Topic(id="pa_002", name="The Number Line", description=""),
            Topic(id="pa_003", name="Absolute Value", description=""),
            Topic(id="pa_004", name="Comparing and Ordering Integers", description=""),
            Topic(id="pa_005", name="Adding and Subtracting Integers", description=""),
            Topic(id="pa_006", name="Multiplying and Dividing Integers", description=""),
            Topic(id="pa_007", name="Order of Operations with Integers", description=""),
        ]),
        Unit(id="pa_u02", name="Fractions and Mixed Numbers", topics=[
            Topic(id="pa_008", name="Understanding Fractions and Equivalent Fractions", description=""),
            Topic(id="pa_009", name="Simplifying Fractions", description=""),
            Topic(id="pa_010", name="Comparing and Ordering Fractions", description=""),
            Topic(id="pa_011", name="Adding and Subtracting Fractions", description=""),
            Topic(id="pa_012", name="Multiplying Fractions", description=""),
            Topic(id="pa_013", name="Dividing Fractions", description=""),
            Topic(id="pa_014", name="Mixed Numbers and Improper Fractions", description=""),
            Topic(id="pa_015", name="Operations with Mixed Numbers", description=""),
        ]),
        Unit(id="pa_u03", name="Decimals", topics=[
            Topic(id="pa_016", name="Understanding and Reading Decimals", description=""),
            Topic(id="pa_017", name="Comparing and Ordering Decimals", description=""),
            Topic(id="pa_018", name="Rounding Decimals", description=""),
            Topic(id="pa_019", name="Adding and Subtracting Decimals", description=""),
            Topic(id="pa_020", name="Multiplying Decimals", description=""),
            Topic(id="pa_021", name="Dividing Decimals", description=""),
            Topic(id="pa_022", name="Converting Between Fractions and Decimals", description=""),
        ]),
        Unit(id="pa_u04", name="Ratios and Proportions", topics=[
            Topic(id="pa_023", name="Understanding Ratios and Rates", description=""),
            Topic(id="pa_024", name="Unit Rates", description=""),
            Topic(id="pa_025", name="Proportions and Cross Multiplication", description=""),
            Topic(id="pa_026", name="Percent as a Ratio", description=""),
            Topic(id="pa_027", name="Percent of a Number", description=""),
            Topic(id="pa_028", name="Percent Change (Increase and Decrease)", description=""),
            Topic(id="pa_029", name="Applications: Tax, Tip, and Discount", description=""),
        ]),
        Unit(id="pa_u05", name="Basic Geometry", topics=[
            Topic(id="pa_030", name="Points, Lines, and Planes", description=""),
            Topic(id="pa_031", name="Classifying Angles", description=""),
            Topic(id="pa_032", name="Angle Relationships (Complementary, Supplementary, Vertical)", description=""),
            Topic(id="pa_033", name="Classifying Triangles", description=""),
            Topic(id="pa_034", name="Classifying Polygons", description=""),
            Topic(id="pa_035", name="Perimeter and Area of Basic Shapes", description=""),
            Topic(id="pa_036", name="Introduction to the Coordinate Plane", description=""),
        ]),
        Unit(id="pa_u06", name="Introduction to Algebra", topics=[
            Topic(id="pa_037", name="Variables and Expressions", description=""),
            Topic(id="pa_038", name="Writing and Evaluating Algebraic Expressions", description=""),
            Topic(id="pa_039", name="Properties of Real Numbers", description=""),
            Topic(id="pa_040", name="Solving One-Step Equations", description=""),
            Topic(id="pa_041", name="Solving Two-Step Equations", description=""),
            Topic(id="pa_042", name="Writing and Solving Inequalities", description=""),
            Topic(id="pa_043", name="Introduction to Functions and Tables", description=""),
        ]),
        Unit(id="pa_u07", name="Problem-Solving Strategies", topics=[
            Topic(id="pa_044", name="Translating Word Problems into Equations", description=""),
            Topic(id="pa_045", name="Guess, Check, and Revise", description=""),
            Topic(id="pa_046", name="Drawing Diagrams and Models", description=""),
            Topic(id="pa_047", name="Finding Patterns", description=""),
            Topic(id="pa_048", name="Working Backwards", description=""),
            Topic(id="pa_049", name="Using Tables and Graphs", description=""),
        ]),
    ])


# ---------------------------------------------------------------------------
# Algebra 1
# ---------------------------------------------------------------------------

def get_algebra1_course() -> Course:
    return Course(id="algebra_1", name="Algebra I", units=[
        Unit(id="a1_u01", name="Solving Linear Equations", topics=[
            Topic(id="a1_001", name="Properties of Equality", description=""),
            Topic(id="a1_002", name="Solving One-Step Equations", description=""),
            Topic(id="a1_003", name="Solving Two-Step Equations", description=""),
            Topic(id="a1_004", name="Solving Multi-Step Equations", description=""),
            Topic(id="a1_005", name="Equations with Variables on Both Sides", description=""),
            Topic(id="a1_006", name="Solving Literal Equations and Formulas", description=""),
            Topic(id="a1_007", name="Absolute Value Equations", description=""),
        ]),
        Unit(id="a1_u02", name="Solving Linear Inequalities", topics=[
            Topic(id="a1_008", name="Properties of Inequality", description=""),
            Topic(id="a1_009", name="Solving One-Step Inequalities", description=""),
            Topic(id="a1_010", name="Solving Multi-Step Inequalities", description=""),
            Topic(id="a1_011", name="Compound Inequalities (And/Or)", description=""),
            Topic(id="a1_012", name="Absolute Value Inequalities", description=""),
            Topic(id="a1_013", name="Graphing Inequalities on a Number Line", description=""),
        ]),
        Unit(id="a1_u03", name="Graphing Linear Functions", topics=[
            Topic(id="a1_014", name="The Coordinate Plane and Plotting Points", description=""),
            Topic(id="a1_015", name="Introduction to Functions and Function Notation", description=""),
            Topic(id="a1_016", name="Domain and Range", description=""),
            Topic(id="a1_017", name="Graphing Linear Equations by Table", description=""),
            Topic(id="a1_018", name="Slope and Rate of Change", description=""),
            Topic(id="a1_019", name="Graphing Using Slope-Intercept Form", description=""),
            Topic(id="a1_020", name="Graphing Using Intercepts", description=""),
            Topic(id="a1_021", name="Horizontal and Vertical Lines", description=""),
        ]),
        Unit(id="a1_u04", name="Writing Linear Functions", topics=[
            Topic(id="a1_022", name="Writing Equations in Slope-Intercept Form", description=""),
            Topic(id="a1_023", name="Writing Equations in Point-Slope Form", description=""),
            Topic(id="a1_024", name="Writing Equations in Standard Form", description=""),
            Topic(id="a1_025", name="Parallel and Perpendicular Lines", description=""),
            Topic(id="a1_026", name="Scatter Plots and Lines of Best Fit", description=""),
            Topic(id="a1_027", name="Arithmetic Sequences as Linear Functions", description=""),
        ]),
        Unit(id="a1_u05", name="Solving Systems of Linear Equations", topics=[
            Topic(id="a1_028", name="Introduction to Systems and Graphing Solutions", description=""),
            Topic(id="a1_029", name="Solving by Substitution", description=""),
            Topic(id="a1_030", name="Solving by Elimination", description=""),
            Topic(id="a1_031", name="Special Systems (No Solution, Infinitely Many)", description=""),
            Topic(id="a1_032", name="Applications of Systems", description=""),
            Topic(id="a1_033", name="Graphing Systems of Linear Inequalities", description=""),
        ]),
        Unit(id="a1_u06", name="Exponential Functions and Sequences", topics=[
            Topic(id="a1_034", name="Properties of Exponents", description=""),
            Topic(id="a1_035", name="Zero and Negative Exponents", description=""),
            Topic(id="a1_036", name="Scientific Notation", description=""),
            Topic(id="a1_037", name="Exponential Growth Functions", description=""),
            Topic(id="a1_038", name="Exponential Decay Functions", description=""),
            Topic(id="a1_039", name="Geometric Sequences", description=""),
            Topic(id="a1_040", name="Comparing Linear and Exponential Models", description=""),
        ]),
        Unit(id="a1_u07", name="Polynomial Equations and Factoring", topics=[
            Topic(id="a1_041", name="Adding and Subtracting Polynomials", description=""),
            Topic(id="a1_042", name="Multiplying Polynomials", description=""),
            Topic(id="a1_043", name="Special Products (Difference of Squares, Perfect Squares)", description=""),
            Topic(id="a1_044", name="Factoring GCF", description=""),
            Topic(id="a1_045", name="Factoring Trinomials (a=1)", description=""),
            Topic(id="a1_046", name="Factoring Trinomials (a≠1)", description=""),
            Topic(id="a1_047", name="Factoring Special Cases", description=""),
            Topic(id="a1_048", name="Solving Polynomial Equations by Factoring", description=""),
        ]),
        Unit(id="a1_u08", name="Graphing Quadratic Equations", topics=[
            Topic(id="a1_049", name="Introduction to Parabolas", description=""),
            Topic(id="a1_050", name="Graphing y = ax²", description=""),
            Topic(id="a1_051", name="Graphing y = ax² + c", description=""),
            Topic(id="a1_052", name="Graphing y = ax² + bx + c", description=""),
            Topic(id="a1_053", name="Finding the Vertex and Axis of Symmetry", description=""),
            Topic(id="a1_054", name="Identifying Key Features of Parabolas", description=""),
            Topic(id="a1_055", name="Comparing Linear, Quadratic, and Exponential Graphs", description=""),
        ]),
        Unit(id="a1_u09", name="Solving Quadratic Equations", topics=[
            Topic(id="a1_056", name="Solving by Square Roots", description=""),
            Topic(id="a1_057", name="Solving by Completing the Square", description=""),
            Topic(id="a1_058", name="The Quadratic Formula", description=""),
            Topic(id="a1_059", name="The Discriminant", description=""),
            Topic(id="a1_060", name="Choosing a Solution Method", description=""),
            Topic(id="a1_061", name="Applications of Quadratic Equations", description=""),
        ]),
        Unit(id="a1_u10", name="Radical Functions and Equations", topics=[
            Topic(id="a1_062", name="Square Roots and Cube Roots", description=""),
            Topic(id="a1_063", name="Simplifying Radical Expressions", description=""),
            Topic(id="a1_064", name="Graphing Square Root and Cube Root Functions", description=""),
            Topic(id="a1_065", name="Solving Radical Equations", description=""),
            Topic(id="a1_066", name="The Pythagorean Theorem", description=""),
            Topic(id="a1_067", name="Distance and Midpoint Formulas", description=""),
        ]),
        Unit(id="a1_u11", name="Data Analysis and Displays", topics=[
            Topic(id="a1_068", name="Measures of Center (Mean, Median, Mode)", description=""),
            Topic(id="a1_069", name="Measures of Variation (Range, IQR)", description=""),
            Topic(id="a1_070", name="Box-and-Whisker Plots", description=""),
            Topic(id="a1_071", name="Histograms and Frequency Distributions", description=""),
            Topic(id="a1_072", name="Stem-and-Leaf Plots", description=""),
            Topic(id="a1_073", name="Two-Way Tables", description=""),
            Topic(id="a1_074", name="Choosing Appropriate Data Displays", description=""),
        ]),
    ])


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

def get_geometry_course() -> Course:
    return Course(id="geometry", name="Geometry", units=[
        Unit(id="geo_u01", name="Basics of Geometry", topics=[
            Topic(id="geo_001", name="Undefined Terms: Points, Lines, and Planes", description=""),
            Topic(id="geo_002", name="Segments, Rays, and Angles", description=""),
            Topic(id="geo_003", name="Measuring Segments and Angles", description=""),
            Topic(id="geo_004", name="Angle Bisectors and Segment Bisectors", description=""),
            Topic(id="geo_005", name="Classifying Angles and Angle Pairs", description=""),
            Topic(id="geo_006", name="Perimeter, Circumference, and Area (Review)", description=""),
            Topic(id="geo_007", name="Introduction to Three-Dimensional Figures", description=""),
        ]),
        Unit(id="geo_u02", name="Reasoning and Proofs", topics=[
            Topic(id="geo_008", name="Inductive Reasoning and Conjectures", description=""),
            Topic(id="geo_009", name="Conditional Statements and Converses", description=""),
            Topic(id="geo_010", name="Biconditional Statements", description=""),
            Topic(id="geo_011", name="Deductive Reasoning", description=""),
            Topic(id="geo_012", name="Introduction to Two-Column Proofs", description=""),
            Topic(id="geo_013", name="Proving Segment and Angle Relationships", description=""),
            Topic(id="geo_014", name="Paragraph and Flow Proofs (H)", description=""),
        ]),
        Unit(id="geo_u03", name="Parallel and Perpendicular Lines", topics=[
            Topic(id="geo_015", name="Identifying Lines and Transversals", description=""),
            Topic(id="geo_016", name="Parallel Lines and Angle Pairs", description=""),
            Topic(id="geo_017", name="Proving Lines Parallel", description=""),
            Topic(id="geo_018", name="Perpendicular Lines and Their Properties", description=""),
            Topic(id="geo_019", name="Slopes of Parallel and Perpendicular Lines", description=""),
            Topic(id="geo_020", name="Writing Equations of Parallel and Perpendicular Lines", description=""),
        ]),
        Unit(id="geo_u04", name="Transformations", topics=[
            Topic(id="geo_021", name="Translations", description=""),
            Topic(id="geo_022", name="Reflections", description=""),
            Topic(id="geo_023", name="Rotations", description=""),
            Topic(id="geo_024", name="Compositions of Transformations", description=""),
            Topic(id="geo_025", name="Dilations", description=""),
            Topic(id="geo_026", name="Symmetry (Line and Rotational)", description=""),
            Topic(id="geo_027", name="Introduction to Tessellations (H)", description=""),
        ]),
        Unit(id="geo_u05", name="Congruent Triangles", topics=[
            Topic(id="geo_028", name="Triangle Angle Sum and Exterior Angle Theorems", description=""),
            Topic(id="geo_029", name="Classifying Triangles", description=""),
            Topic(id="geo_030", name="Congruence and Corresponding Parts", description=""),
            Topic(id="geo_031", name="Triangle Congruence: SSS and SAS", description=""),
            Topic(id="geo_032", name="Triangle Congruence: ASA, AAS, and HL", description=""),
            Topic(id="geo_033", name="Using Congruent Triangles in Proofs", description=""),
            Topic(id="geo_034", name="Isosceles and Equilateral Triangles", description=""),
        ]),
        Unit(id="geo_u06", name="Relationships within Triangles", topics=[
            Topic(id="geo_035", name="Midsegments of Triangles", description=""),
            Topic(id="geo_036", name="Perpendicular Bisectors and Angle Bisectors", description=""),
            Topic(id="geo_037", name="Medians, Altitudes, and Centroids", description=""),
            Topic(id="geo_038", name="Triangle Inequality Theorem", description=""),
            Topic(id="geo_039", name="Hinge Theorem and Indirect Proofs (H)", description=""),
            Topic(id="geo_040", name="Triangle Concurrency Proofs (H)", description=""),
        ]),
        Unit(id="geo_u07", name="Quadrilaterals and Other Polygons", topics=[
            Topic(id="geo_041", name="Interior and Exterior Angles of Polygons", description=""),
            Topic(id="geo_042", name="Properties of Parallelograms", description=""),
            Topic(id="geo_043", name="Proving a Quadrilateral is a Parallelogram", description=""),
            Topic(id="geo_044", name="Properties of Special Parallelograms (Rectangles, Rhombi, Squares)", description=""),
            Topic(id="geo_045", name="Properties of Trapezoids and Kites", description=""),
            Topic(id="geo_046", name="Coordinate Proofs with Quadrilaterals (H)", description=""),
        ]),
        Unit(id="geo_u08", name="Similarity", topics=[
            Topic(id="geo_047", name="Ratios and Proportions in Geometry", description=""),
            Topic(id="geo_048", name="Similar Polygons", description=""),
            Topic(id="geo_049", name="Triangle Similarity: AA, SSS, SAS", description=""),
            Topic(id="geo_050", name="Triangle Proportionality Theorem", description=""),
            Topic(id="geo_051", name="Dilations and Similarity", description=""),
            Topic(id="geo_052", name="Similarity in Three-Dimensional Figures (H)", description=""),
        ]),
        Unit(id="geo_u09", name="Right Triangles and Trigonometry", topics=[
            Topic(id="geo_053", name="The Pythagorean Theorem and Its Converse", description=""),
            Topic(id="geo_054", name="Special Right Triangles (45-45-90 and 30-60-90)", description=""),
            Topic(id="geo_055", name="Introduction to Trigonometric Ratios", description=""),
            Topic(id="geo_056", name="Solving Right Triangles with Trig", description=""),
            Topic(id="geo_057", name="Angles of Elevation and Depression", description=""),
            Topic(id="geo_058", name="Law of Sines (H)", description=""),
            Topic(id="geo_059", name="Law of Cosines (H)", description=""),
        ]),
        Unit(id="geo_u10", name="Circles", topics=[
            Topic(id="geo_060", name="Lines and Segments in Circles", description=""),
            Topic(id="geo_061", name="Arcs and Central Angles", description=""),
            Topic(id="geo_062", name="Inscribed Angles and Intercepted Arcs", description=""),
            Topic(id="geo_063", name="Tangent Lines and Secants", description=""),
            Topic(id="geo_064", name="Angle Relationships in Circles", description=""),
            Topic(id="geo_065", name="Segment Relationships in Circles", description=""),
            Topic(id="geo_066", name="Equations of Circles (H)", description=""),
            Topic(id="geo_067", name="Arc Length and Sector Area", description=""),
        ]),
        Unit(id="geo_u11", name="Circumference, Area, and Volume", topics=[
            Topic(id="geo_068", name="Area of Triangles, Quadrilaterals, and Polygons", description=""),
            Topic(id="geo_069", name="Area and Circumference of Circles", description=""),
            Topic(id="geo_070", name="Surface Area of Prisms and Cylinders", description=""),
            Topic(id="geo_071", name="Surface Area of Pyramids and Cones", description=""),
            Topic(id="geo_072", name="Volume of Prisms and Cylinders", description=""),
            Topic(id="geo_073", name="Volume of Pyramids and Cones", description=""),
            Topic(id="geo_074", name="Surface Area and Volume of Spheres", description=""),
            Topic(id="geo_075", name="Cavalieri's Principle (H)", description=""),
        ]),
        Unit(id="geo_u12", name="Probability", topics=[
            Topic(id="geo_076", name="Sample Spaces and Basic Probability", description=""),
            Topic(id="geo_077", name="Theoretical vs. Experimental Probability", description=""),
            Topic(id="geo_078", name="Compound Events: And/Or", description=""),
            Topic(id="geo_079", name="Independent and Dependent Events", description=""),
            Topic(id="geo_080", name="Conditional Probability", description=""),
            Topic(id="geo_081", name="Permutations and Combinations", description=""),
            Topic(id="geo_082", name="Geometric Probability (H)", description=""),
        ]),
    ])


# ---------------------------------------------------------------------------
# Algebra 2
# ---------------------------------------------------------------------------

def get_algebra2_course() -> Course:
    return Course(id="algebra_2", name="Algebra II", units=[
        Unit(id="a2_u01", name="Linear Functions", topics=[
            Topic(id="a2_001", name="Domain, Range, and Function Notation (Review)", description=""),
            Topic(id="a2_002", name="Parent Functions and Transformations", description=""),
            Topic(id="a2_003", name="Absolute Value Functions and Transformations", description=""),
            Topic(id="a2_004", name="Piecewise Functions", description=""),
            Topic(id="a2_005", name="Solving Absolute Value Equations and Inequalities", description=""),
            Topic(id="a2_006", name="Modeling with Linear Functions", description=""),
        ]),
        Unit(id="a2_u02", name="Quadratic Functions", topics=[
            Topic(id="a2_007", name="Graphing Quadratics in Standard Form", description=""),
            Topic(id="a2_008", name="Graphing Quadratics in Vertex Form", description=""),
            Topic(id="a2_009", name="Transformations of Quadratic Functions", description=""),
            Topic(id="a2_010", name="Factoring Review", description=""),
            Topic(id="a2_011", name="Quadratic Inequalities", description=""),
            Topic(id="a2_012", name="Modeling with Quadratic Functions", description=""),
        ]),
        Unit(id="a2_u03", name="Quadratic Equations and Complex Numbers", topics=[
            Topic(id="a2_013", name="Solving Quadratics by Completing the Square", description=""),
            Topic(id="a2_014", name="The Quadratic Formula and Discriminant", description=""),
            Topic(id="a2_015", name="Introduction to Complex Numbers", description=""),
            Topic(id="a2_016", name="Operations with Complex Numbers", description=""),
            Topic(id="a2_017", name="Solving Quadratics with Complex Solutions", description=""),
            Topic(id="a2_018", name="The Fundamental Theorem of Algebra (Introduction) (H)", description=""),
        ]),
        Unit(id="a2_u04", name="Polynomial Functions", topics=[
            Topic(id="a2_019", name="Graphing Polynomial Functions and End Behavior", description=""),
            Topic(id="a2_020", name="Adding, Subtracting, and Multiplying Polynomials", description=""),
            Topic(id="a2_021", name="Dividing Polynomials: Long Division", description=""),
            Topic(id="a2_022", name="Dividing Polynomials: Synthetic Division", description=""),
            Topic(id="a2_023", name="The Remainder and Factor Theorems", description=""),
            Topic(id="a2_024", name="Finding Rational Zeros", description=""),
            Topic(id="a2_025", name="Writing Polynomial Equations from Roots", description=""),
            Topic(id="a2_026", name="Transformations of Polynomial Functions (H)", description=""),
        ]),
        Unit(id="a2_u05", name="Rational Exponents and Radical Functions", topics=[
            Topic(id="a2_027", name="nth Roots and Rational Exponents", description=""),
            Topic(id="a2_028", name="Properties of Rational Exponents", description=""),
            Topic(id="a2_029", name="Graphing Radical Functions", description=""),
            Topic(id="a2_030", name="Solving Radical Equations and Inequalities", description=""),
            Topic(id="a2_031", name="Function Composition", description=""),
            Topic(id="a2_032", name="Inverse Functions", description=""),
            Topic(id="a2_033", name="Radical Inequalities (H)", description=""),
        ]),
        Unit(id="a2_u06", name="Exponential and Logarithmic Functions", topics=[
            Topic(id="a2_034", name="Graphing Exponential Functions", description=""),
            Topic(id="a2_035", name="The Natural Base e", description=""),
            Topic(id="a2_036", name="Introduction to Logarithms", description=""),
            Topic(id="a2_037", name="Properties of Logarithms", description=""),
            Topic(id="a2_038", name="Solving Exponential Equations", description=""),
            Topic(id="a2_039", name="Solving Logarithmic Equations", description=""),
            Topic(id="a2_040", name="Modeling with Exponential and Logarithmic Functions", description=""),
            Topic(id="a2_041", name="Logistic Growth Models (H)", description=""),
        ]),
        Unit(id="a2_u07", name="Rational Functions", topics=[
            Topic(id="a2_042", name="Inverse Variation and the Reciprocal Function", description=""),
            Topic(id="a2_043", name="Graphing Rational Functions (Asymptotes, Holes)", description=""),
            Topic(id="a2_044", name="Multiplying and Dividing Rational Expressions", description=""),
            Topic(id="a2_045", name="Adding and Subtracting Rational Expressions", description=""),
            Topic(id="a2_046", name="Solving Rational Equations", description=""),
            Topic(id="a2_047", name="Partial Fraction Decomposition (H)", description=""),
        ]),
        Unit(id="a2_u08", name="Sequences and Series", topics=[
            Topic(id="a2_048", name="Arithmetic Sequences and Series", description=""),
            Topic(id="a2_049", name="Geometric Sequences and Series", description=""),
            Topic(id="a2_050", name="Sigma Notation", description=""),
            Topic(id="a2_051", name="Infinite Geometric Series", description=""),
            Topic(id="a2_052", name="Recursive Sequences", description=""),
            Topic(id="a2_053", name="The Binomial Theorem (H)", description=""),
        ]),
        Unit(id="a2_u09", name="Trigonometric Ratios and Functions", topics=[
            Topic(id="a2_054", name="Right Triangle Trigonometry Review", description=""),
            Topic(id="a2_055", name="Angles in Standard Position and Radian Measure", description=""),
            Topic(id="a2_056", name="The Unit Circle", description=""),
            Topic(id="a2_057", name="Graphing Sine and Cosine Functions", description=""),
            Topic(id="a2_058", name="Graphing Other Trigonometric Functions", description=""),
            Topic(id="a2_059", name="Inverse Trigonometric Functions", description=""),
            Topic(id="a2_060", name="Law of Sines and Cosines", description=""),
        ]),
        Unit(id="a2_u10", name="Probability", topics=[
            Topic(id="a2_061", name="Sample Spaces and Basic Counting Principles", description=""),
            Topic(id="a2_062", name="Permutations and Combinations", description=""),
            Topic(id="a2_063", name="Binomial Distributions", description=""),
            Topic(id="a2_064", name="Normal Distributions", description=""),
            Topic(id="a2_065", name="Using Normal Distributions", description=""),
            Topic(id="a2_066", name="Expected Value (H)", description=""),
        ]),
        Unit(id="a2_u11", name="Data Analysis and Statistics", topics=[
            Topic(id="a2_067", name="Measures of Center and Spread", description=""),
            Topic(id="a2_068", name="Data Displays and Interpreting Graphs", description=""),
            Topic(id="a2_069", name="Sampling Methods and Bias", description=""),
            Topic(id="a2_070", name="Surveys, Experiments, and Observational Studies", description=""),
            Topic(id="a2_071", name="Introduction to Hypothesis Testing (H)", description=""),
            Topic(id="a2_072", name="Margin of Error and Confidence Intervals (H)", description=""),
        ]),
    ])


# ---------------------------------------------------------------------------
# Pre-Calculus
# ---------------------------------------------------------------------------

def get_precalculus_course() -> Course:
    return Course(id="precalculus", name="Pre-Calculus and Trigonometry", units=[
        Unit(id="pc_u01", name="Functions and Graphs", topics=[
            Topic(id="pc_001", name="Review of Function Notation, Domain, and Range", description=""),
            Topic(id="pc_002", name="Parent Functions and Transformations", description=""),
            Topic(id="pc_003", name="Combining Functions (Sum, Difference, Product, Quotient)", description=""),
            Topic(id="pc_004", name="Composition of Functions", description=""),
            Topic(id="pc_005", name="Inverse Functions", description=""),
            Topic(id="pc_006", name="Modeling with Functions", description=""),
            Topic(id="pc_007", name="Parametric Equations (Introduction) (H)", description=""),
        ]),
        Unit(id="pc_u02", name="Polynomial, Power, and Rational Functions", topics=[
            Topic(id="pc_008", name="Polynomial Functions and End Behavior", description=""),
            Topic(id="pc_009", name="Dividing Polynomials and the Remainder Theorem", description=""),
            Topic(id="pc_010", name="Real Zeros of Polynomial Functions", description=""),
            Topic(id="pc_011", name="Complex Zeros and the Fundamental Theorem of Algebra", description=""),
            Topic(id="pc_012", name="Graphs of Rational Functions", description=""),
            Topic(id="pc_013", name="Solving Polynomial and Rational Inequalities", description=""),
            Topic(id="pc_014", name="Power Functions and Regression Models", description=""),
        ]),
        Unit(id="pc_u03", name="Exponential and Logarithmic Functions", topics=[
            Topic(id="pc_015", name="Exponential Functions and Their Graphs", description=""),
            Topic(id="pc_016", name="The Natural Exponential Function", description=""),
            Topic(id="pc_017", name="Logarithmic Functions and Their Graphs", description=""),
            Topic(id="pc_018", name="Properties of Logarithms", description=""),
            Topic(id="pc_019", name="Solving Exponential and Logarithmic Equations", description=""),
            Topic(id="pc_020", name="Modeling with Exponential and Logarithmic Functions", description=""),
            Topic(id="pc_021", name="Logistic Functions and Population Models (H)", description=""),
        ]),
        Unit(id="pc_u04", name="Trigonometric Functions", topics=[
            Topic(id="pc_022", name="Angles and Their Measure (Degrees and Radians)", description=""),
            Topic(id="pc_023", name="The Unit Circle", description=""),
            Topic(id="pc_024", name="Trigonometric Functions of Any Angle", description=""),
            Topic(id="pc_025", name="Graphs of Sine and Cosine", description=""),
            Topic(id="pc_026", name="Graphs of Other Trigonometric Functions", description=""),
            Topic(id="pc_027", name="Inverse Trigonometric Functions", description=""),
            Topic(id="pc_028", name="Harmonic Motion and Sinusoidal Models (H)", description=""),
        ]),
        Unit(id="pc_u05", name="Analytic Trigonometry", topics=[
            Topic(id="pc_029", name="Fundamental Trigonometric Identities", description=""),
            Topic(id="pc_030", name="Verifying Trigonometric Identities", description=""),
            Topic(id="pc_031", name="Sum and Difference Identities", description=""),
            Topic(id="pc_032", name="Double-Angle and Half-Angle Identities", description=""),
            Topic(id="pc_033", name="Solving Trigonometric Equations", description=""),
            Topic(id="pc_034", name="Product-to-Sum and Sum-to-Product Formulas (H)", description=""),
        ]),
        Unit(id="pc_u06", name="Additional Topics in Trigonometry", topics=[
            Topic(id="pc_035", name="Law of Sines", description=""),
            Topic(id="pc_036", name="Law of Cosines", description=""),
            Topic(id="pc_037", name="Area of a Triangle (SAS and Heron's Formula)", description=""),
            Topic(id="pc_038", name="Vectors in the Plane", description=""),
            Topic(id="pc_039", name="Dot Product and Projections", description=""),
            Topic(id="pc_040", name="Trigonometric Form of Complex Numbers (H)", description=""),
            Topic(id="pc_041", name="DeMoivre's Theorem and nth Roots (H)", description=""),
        ]),
        Unit(id="pc_u07", name="Linear Systems and Matrices", topics=[
            Topic(id="pc_042", name="Solving Linear Systems (Review and Extension)", description=""),
            Topic(id="pc_043", name="Multivariable Linear Systems and Row Reduction", description=""),
            Topic(id="pc_044", name="Matrix Operations", description=""),
            Topic(id="pc_045", name="Matrix Multiplication", description=""),
            Topic(id="pc_046", name="Inverse Matrices and Solving Matrix Equations", description=""),
            Topic(id="pc_047", name="Determinants and Cramer's Rule (H)", description=""),
            Topic(id="pc_048", name="Linear Programming (H)", description=""),
        ]),
        Unit(id="pc_u08", name="Sequences, Series, and Probability", topics=[
            Topic(id="pc_049", name="Arithmetic and Geometric Sequences", description=""),
            Topic(id="pc_050", name="Series and Sigma Notation", description=""),
            Topic(id="pc_051", name="The Binomial Theorem", description=""),
            Topic(id="pc_052", name="Counting Principles, Permutations, Combinations", description=""),
            Topic(id="pc_053", name="Introduction to Probability", description=""),
            Topic(id="pc_054", name="Mathematical Induction (H)", description=""),
        ]),
        Unit(id="pc_u09", name="Topics in Analytic Geometry", topics=[
            Topic(id="pc_055", name="Parabolas", description=""),
            Topic(id="pc_056", name="Ellipses", description=""),
            Topic(id="pc_057", name="Hyperbolas", description=""),
            Topic(id="pc_058", name="Rotation of Conics (H)", description=""),
            Topic(id="pc_059", name="Polar Coordinates and Graphs", description=""),
            Topic(id="pc_060", name="Parametric Equations and Curves", description=""),
            Topic(id="pc_061", name="Conic Sections in Polar Form (H)", description=""),
        ]),
        Unit(id="pc_u10", name="Analytic Geometry in 3 Dimensions (H)", topics=[
            Topic(id="pc_062", name="The Three-Dimensional Coordinate System (H)", description=""),
            Topic(id="pc_063", name="Vectors in Three Dimensions (H)", description=""),
            Topic(id="pc_064", name="The Cross Product (H)", description=""),
            Topic(id="pc_065", name="Lines and Planes in Space (H)", description=""),
            Topic(id="pc_066", name="Surfaces in Three Dimensions (H)", description=""),
        ]),
        Unit(id="pc_u11", name="Limits and an Introduction to Calculus (H)", topics=[
            Topic(id="pc_067", name="Introduction to Limits (H)", description=""),
            Topic(id="pc_068", name="Evaluating Limits Analytically (H)", description=""),
            Topic(id="pc_069", name="Continuity and One-Sided Limits (H)", description=""),
            Topic(id="pc_070", name="Infinite Limits and Limits at Infinity (H)", description=""),
            Topic(id="pc_071", name="Introduction to the Derivative (H)", description=""),
            Topic(id="pc_072", name="Introduction to Integration (H)", description=""),
        ]),
    ])


# ---------------------------------------------------------------------------
# Calculus 1
# ---------------------------------------------------------------------------

def get_calculus1_course() -> Course:
    return Course(id="calculus_1", name="Calculus I", units=[
        Unit(id="c1_u01", name="Limits", topics=[
            Topic(id="c1_001", name="Intuitive Introduction to Limits", description=""),
            Topic(id="c1_002", name="Computing Limits Algebraically", description=""),
            Topic(id="c1_003", name="One-Sided Limits and Continuity", description=""),
            Topic(id="c1_004", name="Limits Involving Infinity", description=""),
            Topic(id="c1_005", name="The Epsilon-Delta Definition of a Limit (H)", description=""),
            Topic(id="c1_006", name="Continuity and the Intermediate Value Theorem", description=""),
        ]),
        Unit(id="c1_u02", name="Derivative Rules", topics=[
            Topic(id="c1_007", name="The Derivative as a Rate of Change and Slope", description=""),
            Topic(id="c1_008", name="The Power Rule", description=""),
            Topic(id="c1_009", name="Product and Quotient Rules", description=""),
            Topic(id="c1_010", name="Derivatives of Trigonometric Functions", description=""),
            Topic(id="c1_011", name="The Chain Rule", description=""),
            Topic(id="c1_012", name="Implicit Differentiation", description=""),
            Topic(id="c1_013", name="Derivatives of Exponential and Logarithmic Functions", description=""),
            Topic(id="c1_014", name="Derivatives of Inverse Trigonometric Functions (H)", description=""),
            Topic(id="c1_015", name="Higher-Order Derivatives", description=""),
        ]),
        Unit(id="c1_u03", name="Applications of Derivatives", topics=[
            Topic(id="c1_016", name="Related Rates", description=""),
            Topic(id="c1_017", name="Linear Approximation and Differentials", description=""),
            Topic(id="c1_018", name="Extreme Values and the Closed Interval Method", description=""),
            Topic(id="c1_019", name="The Mean Value Theorem", description=""),
            Topic(id="c1_020", name="Monotonicity and the First Derivative Test", description=""),
            Topic(id="c1_021", name="Concavity and the Second Derivative Test", description=""),
            Topic(id="c1_022", name="L'Hôpital's Rule and Indeterminate Forms", description=""),
            Topic(id="c1_023", name="Curve Sketching", description=""),
            Topic(id="c1_024", name="Optimization Problems", description=""),
            Topic(id="c1_025", name="Newton's Method (H)", description=""),
        ]),
        Unit(id="c1_u04", name="Integrals", topics=[
            Topic(id="c1_026", name="Antiderivatives and Indefinite Integrals", description=""),
            Topic(id="c1_027", name="Riemann Sums and Definite Integrals", description=""),
            Topic(id="c1_028", name="The Fundamental Theorem of Calculus (Part 1 and 2)", description=""),
            Topic(id="c1_029", name="Substitution Rule (u-substitution)", description=""),
            Topic(id="c1_030", name="Integrals of Exponential and Logarithmic Functions", description=""),
            Topic(id="c1_031", name="Integrals of Trigonometric Functions", description=""),
            Topic(id="c1_032", name="Numerical Integration: Trapezoidal and Simpson's Rules (H)", description=""),
        ]),
        Unit(id="c1_u05", name="Applications of Integrals", topics=[
            Topic(id="c1_033", name="Area Between Curves", description=""),
            Topic(id="c1_034", name="Volume by Disk and Washer Methods", description=""),
            Topic(id="c1_035", name="Volume by Shell Method", description=""),
            Topic(id="c1_036", name="Average Value of a Function", description=""),
            Topic(id="c1_037", name="Rectilinear Motion Using Integration", description=""),
            Topic(id="c1_038", name="Arc Length (H)", description=""),
            Topic(id="c1_039", name="Surface Area of Revolution (H)", description=""),
        ]),
        Unit(id="c1_u06", name="First Order Differential Equations", topics=[
            Topic(id="c1_040", name="Introduction to Differential Equations", description=""),
            Topic(id="c1_041", name="Slope Fields and Solution Curves", description=""),
            Topic(id="c1_042", name="Separable Differential Equations", description=""),
            Topic(id="c1_043", name="Exponential Growth and Decay Models", description=""),
            Topic(id="c1_044", name="Logistic Growth Models (H)", description=""),
            Topic(id="c1_045", name="Euler's Method (H)", description=""),
        ]),
    ])


# ---------------------------------------------------------------------------
# Calculus 2
# ---------------------------------------------------------------------------

def get_calculus2_course() -> Course:
    return Course(id="calculus_2", name="Calculus II", units=[
        Unit(id="c2_u01", name="Integration Techniques", topics=[
            Topic(id="c2_001", name="Review of u-Substitution", description=""),
            Topic(id="c2_002", name="Integration by Parts", description=""),
            Topic(id="c2_003", name="Trigonometric Integrals", description=""),
            Topic(id="c2_004", name="Trigonometric Substitution", description=""),
            Topic(id="c2_005", name="Partial Fractions", description=""),
            Topic(id="c2_006", name="Improper Integrals", description=""),
            Topic(id="c2_007", name="Integration Using Tables and CAS (H)", description=""),
            Topic(id="c2_008", name="Hyperbolic Functions and Their Integrals (H)", description=""),
        ]),
        Unit(id="c2_u02", name="Further Applications of Integrals", topics=[
            Topic(id="c2_009", name="Arc Length", description=""),
            Topic(id="c2_010", name="Surface Area of Revolution", description=""),
            Topic(id="c2_011", name="Work, Force, and Pressure Applications", description=""),
            Topic(id="c2_012", name="Center of Mass and Moments (H)", description=""),
            Topic(id="c2_013", name="Probability and Integration (H)", description=""),
        ]),
        Unit(id="c2_u03", name="Parametric Equations and Polar Coordinates", topics=[
            Topic(id="c2_014", name="Parametric Equations and Curves", description=""),
            Topic(id="c2_015", name="Calculus with Parametric Curves (Tangents, Arc Length)", description=""),
            Topic(id="c2_016", name="Polar Coordinates and Graphs", description=""),
            Topic(id="c2_017", name="Area and Arc Length in Polar Coordinates", description=""),
            Topic(id="c2_018", name="Conic Sections in Polar Form (H)", description=""),
        ]),
        Unit(id="c2_u04", name="Sequences, Series, and Power Series", topics=[
            Topic(id="c2_019", name="Sequences and Their Limits", description=""),
            Topic(id="c2_020", name="Introduction to Series and the Divergence Test", description=""),
            Topic(id="c2_021", name="Integral Test and p-Series", description=""),
            Topic(id="c2_022", name="Comparison Tests", description=""),
            Topic(id="c2_023", name="Alternating Series and Absolute Convergence", description=""),
            Topic(id="c2_024", name="Ratio and Root Tests", description=""),
            Topic(id="c2_025", name="Power Series and Radius of Convergence", description=""),
            Topic(id="c2_026", name="Taylor and Maclaurin Series", description=""),
            Topic(id="c2_027", name="Applications of Taylor Series (H)", description=""),
            Topic(id="c2_028", name="Fourier Series (Introduction) (H)", description=""),
        ]),
    ])


# ---------------------------------------------------------------------------
# Calculus 3
# ---------------------------------------------------------------------------

def get_calculus3_course() -> Course:
    return Course(id="calculus_3", name="Calculus III", units=[
        Unit(id="c3_u01", name="Vectors and 3D Space", topics=[
            Topic(id="c3_001", name="Coordinate Systems in Three Dimensions", description=""),
            Topic(id="c3_002", name="Vectors in 3D: Operations and Properties", description=""),
            Topic(id="c3_003", name="The Dot Product", description=""),
            Topic(id="c3_004", name="The Cross Product", description=""),
            Topic(id="c3_005", name="Lines and Planes in Space", description=""),
            Topic(id="c3_006", name="Cylinders and Quadric Surfaces (H)", description=""),
        ]),
        Unit(id="c3_u02", name="Vector Functions", topics=[
            Topic(id="c3_007", name="Vector-Valued Functions and Space Curves", description=""),
            Topic(id="c3_008", name="Derivatives and Integrals of Vector Functions", description=""),
            Topic(id="c3_009", name="Arc Length and Curvature", description=""),
            Topic(id="c3_010", name="Motion in Space: Velocity and Acceleration", description=""),
            Topic(id="c3_011", name="Tangential and Normal Components of Acceleration (H)", description=""),
            Topic(id="c3_012", name="Kepler's Laws of Planetary Motion (H)", description=""),
        ]),
        Unit(id="c3_u03", name="Partial Derivatives", topics=[
            Topic(id="c3_013", name="Functions of Several Variables and Level Curves", description=""),
            Topic(id="c3_014", name="Limits and Continuity in Several Variables (H)", description=""),
            Topic(id="c3_015", name="Partial Derivatives", description=""),
            Topic(id="c3_016", name="Tangent Planes and Linear Approximation", description=""),
            Topic(id="c3_017", name="The Chain Rule for Multivariable Functions", description=""),
            Topic(id="c3_018", name="Directional Derivatives and the Gradient", description=""),
            Topic(id="c3_019", name="Maximum and Minimum Values", description=""),
            Topic(id="c3_020", name="Lagrange Multipliers (H)", description=""),
        ]),
        Unit(id="c3_u04", name="Multiple Integrals", topics=[
            Topic(id="c3_021", name="Double Integrals over Rectangles", description=""),
            Topic(id="c3_022", name="Double Integrals over General Regions", description=""),
            Topic(id="c3_023", name="Double Integrals in Polar Coordinates", description=""),
            Topic(id="c3_024", name="Applications: Area, Volume, Mass, and Center of Mass", description=""),
            Topic(id="c3_025", name="Triple Integrals", description=""),
            Topic(id="c3_026", name="Triple Integrals in Cylindrical and Spherical Coordinates", description=""),
            Topic(id="c3_027", name="Change of Variables and the Jacobian (H)", description=""),
        ]),
        Unit(id="c3_u05", name="Vector Calculus", topics=[
            Topic(id="c3_028", name="Vector Fields", description=""),
            Topic(id="c3_029", name="Line Integrals (Scalar and Vector)", description=""),
            Topic(id="c3_030", name="The Fundamental Theorem for Line Integrals", description=""),
            Topic(id="c3_031", name="Green's Theorem", description=""),
            Topic(id="c3_032", name="Curl and Divergence", description=""),
            Topic(id="c3_033", name="Parametric Surfaces and Surface Integrals", description=""),
            Topic(id="c3_034", name="Stokes' Theorem", description=""),
            Topic(id="c3_035", name="The Divergence Theorem", description=""),
            Topic(id="c3_036", name="Differential Forms (Introduction) (H)", description=""),
        ]),
        Unit(id="c3_u06", name="Second Order Differential Equations", topics=[
            Topic(id="c3_037", name="Second Order Linear Homogeneous Equations", description=""),
            Topic(id="c3_038", name="Characteristic Equations with Complex Roots", description=""),
            Topic(id="c3_039", name="Nonhomogeneous Equations: Undetermined Coefficients", description=""),
            Topic(id="c3_040", name="Nonhomogeneous Equations: Variation of Parameters", description=""),
            Topic(id="c3_041", name="Series Solutions (Introduction) (H)", description=""),
            Topic(id="c3_042", name="Boundary Value Problems (H)", description=""),
        ]),
    ])


# ---------------------------------------------------------------------------
# Differential Equations
# ---------------------------------------------------------------------------

def get_diffeq_course() -> Course:
    return Course(id="differential_equations", name="Differential Equations", units=[
        Unit(id="de_u01", name="First Order Differential Equations", topics=[
            Topic(id="de_001", name="Classifications and Terminology", description=""),
            Topic(id="de_002", name="Separable Equations", description=""),
            Topic(id="de_003", name="Linear First Order Equations and Integrating Factors", description=""),
            Topic(id="de_004", name="Exact Equations", description=""),
            Topic(id="de_005", name="Substitution Methods (Bernoulli, Homogeneous) (H)", description=""),
            Topic(id="de_006", name="Existence and Uniqueness Theorem (H)", description=""),
        ]),
        Unit(id="de_u02", name="Mathematical Models and Numerical Methods with First Order DEs", topics=[
            Topic(id="de_007", name="Population Growth and Decay Models", description=""),
            Topic(id="de_008", name="Mixing Problems and Compartmental Analysis", description=""),
            Topic(id="de_009", name="Newton's Law of Cooling", description=""),
            Topic(id="de_010", name="Euler's Method", description=""),
            Topic(id="de_011", name="Improved Euler and Runge-Kutta Methods (H)", description=""),
            Topic(id="de_012", name="Error Analysis in Numerical Methods (H)", description=""),
        ]),
        Unit(id="de_u03", name="Second Order Differential Equations", topics=[
            Topic(id="de_013", name="Homogeneous Equations with Constant Coefficients", description=""),
            Topic(id="de_014", name="Complex and Repeated Roots", description=""),
            Topic(id="de_015", name="Undetermined Coefficients", description=""),
            Topic(id="de_016", name="Variation of Parameters", description=""),
            Topic(id="de_017", name="Free Mechanical Vibrations", description=""),
            Topic(id="de_018", name="Forced Oscillations and Resonance (H)", description=""),
            Topic(id="de_019", name="Electrical Circuit Analogies (H)", description=""),
        ]),
        Unit(id="de_u04", name="Introduction to Systems and Phase Plane Analysis", topics=[
            Topic(id="de_020", name="Introduction to Systems of DEs", description=""),
            Topic(id="de_021", name="Elimination Method for Linear Systems", description=""),
            Topic(id="de_022", name="Phase Plane and Trajectories", description=""),
            Topic(id="de_023", name="Stability of Equilibrium Points", description=""),
            Topic(id="de_024", name="Linearization of Nonlinear Systems (H)", description=""),
            Topic(id="de_025", name="Limit Cycles and the Poincaré-Bendixson Theorem (H)", description=""),
        ]),
        Unit(id="de_u05", name="Higher Order Differential Equations", topics=[
            Topic(id="de_026", name="Linear Independence and the Wronskian", description=""),
            Topic(id="de_027", name="Homogeneous Higher Order Equations", description=""),
            Topic(id="de_028", name="Undetermined Coefficients for Higher Order Equations", description=""),
            Topic(id="de_029", name="Variation of Parameters for Higher Order Equations", description=""),
            Topic(id="de_030", name="Cauchy-Euler Equations (H)", description=""),
        ]),
        Unit(id="de_u06", name="Laplace Transforms", topics=[
            Topic(id="de_031", name="Definition and Basic Properties", description=""),
            Topic(id="de_032", name="Inverse Laplace Transforms", description=""),
            Topic(id="de_033", name="Solving IVPs with Laplace Transforms", description=""),
            Topic(id="de_034", name="Step Functions and Discontinuous Forcing", description=""),
            Topic(id="de_035", name="Convolution and the Convolution Theorem", description=""),
            Topic(id="de_036", name="Dirac Delta Function and Impulse Problems (H)", description=""),
        ]),
        Unit(id="de_u07", name="Series Solutions to Differential Equations", topics=[
            Topic(id="de_037", name="Power Series Review", description=""),
            Topic(id="de_038", name="Series Solutions Near Ordinary Points", description=""),
            Topic(id="de_039", name="Series Solutions Near Regular Singular Points (Frobenius Method)", description=""),
            Topic(id="de_040", name="Bessel's Equation and Bessel Functions (H)", description=""),
            Topic(id="de_041", name="Legendre's Equation and Legendre Polynomials (H)", description=""),
        ]),
        Unit(id="de_u08", name="Matrix Methods for Linear Systems", topics=[
            Topic(id="de_042", name="Review of Matrices and Eigenvalues", description=""),
            Topic(id="de_043", name="Homogeneous Systems with Distinct Real Eigenvalues", description=""),
            Topic(id="de_044", name="Complex and Repeated Eigenvalues", description=""),
            Topic(id="de_045", name="Fundamental Matrices and Matrix Exponentials", description=""),
            Topic(id="de_046", name="Nonhomogeneous Linear Systems", description=""),
            Topic(id="de_047", name="Variation of Parameters for Systems (H)", description=""),
        ]),
        Unit(id="de_u09", name="Partial Differential Equations (H)", topics=[
            Topic(id="de_048", name="Classification of PDEs (H)", description=""),
            Topic(id="de_049", name="Fourier Series (H)", description=""),
            Topic(id="de_050", name="The Heat Equation and Separation of Variables (H)", description=""),
            Topic(id="de_051", name="The Wave Equation (H)", description=""),
            Topic(id="de_052", name="Laplace's Equation and Harmonic Functions (H)", description=""),
            Topic(id="de_053", name="Fourier Transforms (Introduction) (H)", description=""),
        ]),
    ])


# ---------------------------------------------------------------------------
# Linear Algebra
# ---------------------------------------------------------------------------

def get_linearalgebra_course() -> Course:
    return Course(id="linear_algebra", name="Linear Algebra", units=[
        Unit(id="la_u01", name="Linear Equations and Matrices", topics=[
            Topic(id="la_001", name="Systems of Linear Equations", description=""),
            Topic(id="la_002", name="Row Reduction and Echelon Forms", description=""),
            Topic(id="la_003", name="Vector Equations and Span", description=""),
            Topic(id="la_004", name="The Matrix Equation Ax = b", description=""),
            Topic(id="la_005", name="Solution Sets and Free Variables", description=""),
            Topic(id="la_006", name="Applications of Linear Systems", description=""),
            Topic(id="la_007", name="Linear Independence", description=""),
        ]),
        Unit(id="la_u02", name="Matrix Theory", topics=[
            Topic(id="la_008", name="Matrix Operations (Addition, Scalar Multiplication)", description=""),
            Topic(id="la_009", name="Matrix Multiplication", description=""),
            Topic(id="la_010", name="The Transpose and Its Properties", description=""),
            Topic(id="la_011", name="Invertible Matrices and the Inverse", description=""),
            Topic(id="la_012", name="Elementary Matrices and LU Decomposition (H)", description=""),
            Topic(id="la_013", name="The Determinant: Definition and Properties", description=""),
            Topic(id="la_014", name="Cofactor Expansion and Cramer's Rule (H)", description=""),
        ]),
        Unit(id="la_u03", name="Fields and Vector Spaces", topics=[
            Topic(id="la_015", name="Introduction to Fields (Real, Complex, Finite Fields)", description=""),
            Topic(id="la_016", name="Definition and Axioms of a Vector Space", description=""),
            Topic(id="la_017", name="Examples of Vector Spaces (Function Spaces, Polynomial Spaces)", description=""),
            Topic(id="la_018", name="Subspaces", description=""),
            Topic(id="la_019", name="Null Space and Column Space", description=""),
            Topic(id="la_020", name="Basis and Dimension", description=""),
            Topic(id="la_021", name="The Rank-Nullity Theorem", description=""),
        ]),
        Unit(id="la_u04", name="Finite Dimensional Vector Spaces", topics=[
            Topic(id="la_022", name="Coordinates and Change of Basis", description=""),
            Topic(id="la_023", name="Row Space and Column Space", description=""),
            Topic(id="la_024", name="The Four Fundamental Subspaces (H)", description=""),
            Topic(id="la_025", name="Affine Subspaces (H)", description=""),
            Topic(id="la_026", name="Quotient Spaces (H)", description=""),
        ]),
        Unit(id="la_u05", name="Linear Transformations", topics=[
            Topic(id="la_027", name="Definition and Examples", description=""),
            Topic(id="la_028", name="The Matrix of a Linear Transformation", description=""),
            Topic(id="la_029", name="Kernel and Image", description=""),
            Topic(id="la_030", name="Isomorphisms of Vector Spaces", description=""),
            Topic(id="la_031", name="Composition and Invertibility", description=""),
            Topic(id="la_032", name="Change of Basis for Transformations (H)", description=""),
            Topic(id="la_033", name="Dual Spaces and Dual Transformations (H)", description=""),
        ]),
        Unit(id="la_u06", name="Polynomials", topics=[
            Topic(id="la_034", name="Polynomials as a Vector Space", description=""),
            Topic(id="la_035", name="Polynomial Division and the Remainder Theorem", description=""),
            Topic(id="la_036", name="Roots, Irreducibility, and Factorization", description=""),
            Topic(id="la_037", name="Minimal Polynomials (H)", description=""),
            Topic(id="la_038", name="Cayley-Hamilton Theorem (H)", description=""),
        ]),
        Unit(id="la_u07", name="Eigenvalues and Eigenvectors", topics=[
            Topic(id="la_039", name="Introduction to Eigenvalues and Eigenvectors", description=""),
            Topic(id="la_040", name="The Characteristic Polynomial", description=""),
            Topic(id="la_041", name="Diagonalization", description=""),
            Topic(id="la_042", name="Geometric vs. Algebraic Multiplicity", description=""),
            Topic(id="la_043", name="Complex Eigenvalues", description=""),
            Topic(id="la_044", name="Applications: Discrete Dynamical Systems and Markov Chains", description=""),
            Topic(id="la_045", name="Jordan Canonical Form (H)", description=""),
        ]),
        Unit(id="la_u08", name="Inner Product Spaces", topics=[
            Topic(id="la_046", name="Inner Products and Norms", description=""),
            Topic(id="la_047", name="Orthogonality and Orthonormal Bases", description=""),
            Topic(id="la_048", name="The Gram-Schmidt Process", description=""),
            Topic(id="la_049", name="Orthogonal Projections and Least Squares", description=""),
            Topic(id="la_050", name="QR Decomposition (H)", description=""),
            Topic(id="la_051", name="Fourier Series as an Inner Product Space Application (H)", description=""),
        ]),
        Unit(id="la_u09", name="Operators on Inner Product Spaces (H)", topics=[
            Topic(id="la_052", name="Adjoint of a Linear Operator (H)", description=""),
            Topic(id="la_053", name="Self-Adjoint and Normal Operators (H)", description=""),
            Topic(id="la_054", name="The Spectral Theorem for Real Symmetric Matrices (H)", description=""),
            Topic(id="la_055", name="The Spectral Theorem for Normal Operators (H)", description=""),
            Topic(id="la_056", name="Positive Definite Operators (H)", description=""),
            Topic(id="la_057", name="Singular Value Decomposition (SVD) (H)", description=""),
        ]),
        Unit(id="la_u10", name="Operators on Complex Vector Spaces (H)", topics=[
            Topic(id="la_058", name="Generalized Eigenvectors and the Jordan Form (H)", description=""),
            Topic(id="la_059", name="Nilpotent Operators (H)", description=""),
            Topic(id="la_060", name="The Jordan Normal Form Revisited (H)", description=""),
            Topic(id="la_061", name="Rational Canonical Form (H)", description=""),
            Topic(id="la_062", name="Unitary Operators and Unitary Matrices (H)", description=""),
        ]),
        Unit(id="la_u11", name="Introduction to Multilinear Algebra (H)", topics=[
            Topic(id="la_063", name="Bilinear Forms (H)", description=""),
            Topic(id="la_064", name="Tensor Products of Vector Spaces (H)", description=""),
            Topic(id="la_065", name="Exterior Algebra and the Wedge Product (H)", description=""),
            Topic(id="la_066", name="Determinants via Exterior Algebra (H)", description=""),
            Topic(id="la_067", name="Introduction to Tensors in Applied Contexts (H)", description=""),
        ]),
    ])


# ---------------------------------------------------------------------------
# Discrete Mathematics
# ---------------------------------------------------------------------------

def get_discrete_math_course() -> Course:
    return Course(id="discrete_math", name="Discrete Mathematics", units=[
        Unit(id="dm_u01", name="Logic and Propositional Calculus", topics=[
            Topic(id="dm_001", name="Propositions and Logical Connectives", description=""),
            Topic(id="dm_002", name="Truth Tables", description=""),
            Topic(id="dm_003", name="Logical Equivalences and Laws", description=""),
            Topic(id="dm_004", name="Predicates and Quantifiers", description=""),
            Topic(id="dm_005", name="Nested Quantifiers (H)", description=""),
            Topic(id="dm_006", name="Logical Inference and Arguments", description=""),
        ]),
        Unit(id="dm_u02", name="Sets and Set Theory", topics=[
            Topic(id="dm_007", name="Set Notation and Basic Operations", description=""),
            Topic(id="dm_008", name="Subsets, Power Sets, and Cartesian Products", description=""),
            Topic(id="dm_009", name="Set Identities and Proofs", description=""),
            Topic(id="dm_010", name="Indexed Families of Sets (H)", description=""),
            Topic(id="dm_011", name="Russell's Paradox and Naive Set Theory (H)", description=""),
        ]),
        Unit(id="dm_u03", name="Proof Techniques", topics=[
            Topic(id="dm_012", name="Direct Proof", description=""),
            Topic(id="dm_013", name="Proof by Contrapositive", description=""),
            Topic(id="dm_014", name="Proof by Contradiction", description=""),
            Topic(id="dm_015", name="Proof by Cases", description=""),
            Topic(id="dm_016", name="Mathematical Induction", description=""),
            Topic(id="dm_017", name="Strong Induction and Well-Ordering (H)", description=""),
        ]),
        Unit(id="dm_u04", name="Relations", topics=[
            Topic(id="dm_018", name="Definition and Representation of Relations", description=""),
            Topic(id="dm_019", name="Properties of Relations (Reflexive, Symmetric, Transitive)", description=""),
            Topic(id="dm_020", name="Equivalence Relations and Partitions", description=""),
            Topic(id="dm_021", name="Partial Orders and Hasse Diagrams", description=""),
            Topic(id="dm_022", name="Closures of Relations (H)", description=""),
            Topic(id="dm_023", name="Relational Databases (Application) (H)", description=""),
        ]),
        Unit(id="dm_u05", name="Functions", topics=[
            Topic(id="dm_024", name="Definition, Domain, Codomain, and Range", description=""),
            Topic(id="dm_025", name="Injective, Surjective, and Bijective Functions", description=""),
            Topic(id="dm_026", name="Composition and Inverse Functions", description=""),
            Topic(id="dm_027", name="Cardinality and Countability", description=""),
            Topic(id="dm_028", name="Cantor's Theorem and Uncountability (H)", description=""),
            Topic(id="dm_029", name="Schröder-Bernstein Theorem (H)", description=""),
        ]),
        Unit(id="dm_u06", name="Number Theory", topics=[
            Topic(id="dm_030", name="Divisibility and the Division Algorithm", description=""),
            Topic(id="dm_031", name="GCD, LCM, and the Euclidean Algorithm", description=""),
            Topic(id="dm_032", name="Primes and the Fundamental Theorem of Arithmetic", description=""),
            Topic(id="dm_033", name="Modular Arithmetic and Congruences", description=""),
            Topic(id="dm_034", name="Solving Linear Congruences", description=""),
            Topic(id="dm_035", name="The Chinese Remainder Theorem (H)", description=""),
            Topic(id="dm_036", name="Fermat's Little Theorem and Euler's Theorem (H)", description=""),
            Topic(id="dm_037", name="Introduction to Cryptography (RSA) (H)", description=""),
        ]),
        Unit(id="dm_u07", name="Combinatorics", topics=[
            Topic(id="dm_038", name="The Multiplication and Addition Principles", description=""),
            Topic(id="dm_039", name="Permutations and Combinations", description=""),
            Topic(id="dm_040", name="Binomial Coefficients and Pascal's Triangle", description=""),
            Topic(id="dm_041", name="The Pigeonhole Principle", description=""),
            Topic(id="dm_042", name="Inclusion-Exclusion Principle", description=""),
            Topic(id="dm_043", name="Generating Functions (H)", description=""),
            Topic(id="dm_044", name="Recurrence Relations and Solving Techniques (H)", description=""),
            Topic(id="dm_045", name="Catalan Numbers and Combinatorial Identities (H)", description=""),
        ]),
        Unit(id="dm_u08", name="Graph Theory", topics=[
            Topic(id="dm_046", name="Introduction to Graphs: Definitions and Terminology", description=""),
            Topic(id="dm_047", name="Graph Representations (Adjacency Matrix, List)", description=""),
            Topic(id="dm_048", name="Paths, Cycles, and Connectivity", description=""),
            Topic(id="dm_049", name="Eulerian and Hamiltonian Graphs", description=""),
            Topic(id="dm_050", name="Trees and Spanning Trees", description=""),
            Topic(id="dm_051", name="Planar Graphs and Euler's Formula", description=""),
            Topic(id="dm_052", name="Graph Coloring", description=""),
            Topic(id="dm_053", name="Bipartite Graphs and Matching (H)", description=""),
            Topic(id="dm_054", name="Network Flows (H)", description=""),
        ]),
        Unit(id="dm_u09", name="Trees and Algorithms", topics=[
            Topic(id="dm_055", name="Rooted Trees and Binary Trees", description=""),
            Topic(id="dm_056", name="Tree Traversals", description=""),
            Topic(id="dm_057", name="Spanning Trees: BFS and DFS", description=""),
            Topic(id="dm_058", name="Minimum Spanning Trees: Kruskal's and Prim's Algorithms", description=""),
            Topic(id="dm_059", name="Shortest Path: Dijkstra's Algorithm", description=""),
            Topic(id="dm_060", name="Algorithm Complexity and Big-O Notation (H)", description=""),
        ]),
        Unit(id="dm_u10", name="Boolean Algebra and Automata (H)", topics=[
            Topic(id="dm_061", name="Boolean Functions and Logic Gates (H)", description=""),
            Topic(id="dm_062", name="Minimization and Karnaugh Maps (H)", description=""),
            Topic(id="dm_063", name="Finite State Machines (H)", description=""),
            Topic(id="dm_064", name="Regular Languages and Regular Expressions (H)", description=""),
            Topic(id="dm_065", name="Introduction to Turing Machines (H)", description=""),
        ]),
    ])


# ---------------------------------------------------------------------------
# Proofs
# ---------------------------------------------------------------------------

def get_proofs_course() -> Course:
    return Course(id="proofs", name="Proofs and Mathematical Reasoning", units=[
        Unit(id="pf_u01", name="Mathematical Language and Logic", topics=[
            Topic(id="pf_001", name="Mathematical Statements and Notation", description=""),
            Topic(id="pf_002", name="Logical Connectives and Quantifiers", description=""),
            Topic(id="pf_003", name="Negation of Statements and Quantifiers", description=""),
            Topic(id="pf_004", name="Implications and Equivalences", description=""),
            Topic(id="pf_005", name="How to Read and Write Mathematics", description=""),
        ]),
        Unit(id="pf_u02", name="Fundamental Proof Techniques", topics=[
            Topic(id="pf_006", name="Direct Proof", description=""),
            Topic(id="pf_007", name="Proof by Contrapositive", description=""),
            Topic(id="pf_008", name="Proof by Contradiction", description=""),
            Topic(id="pf_009", name="Proof by Cases and Without Loss of Generality", description=""),
            Topic(id="pf_010", name="Existence and Uniqueness Proofs", description=""),
            Topic(id="pf_011", name="Disproving Statements with Counterexamples", description=""),
        ]),
        Unit(id="pf_u03", name="Mathematical Induction", topics=[
            Topic(id="pf_012", name="Weak Induction", description=""),
            Topic(id="pf_013", name="Strong Induction", description=""),
            Topic(id="pf_014", name="Well-Ordering Principle", description=""),
            Topic(id="pf_015", name="Induction on Other Structures (H)", description=""),
            Topic(id="pf_016", name="Proving Combinatorial Identities by Induction", description=""),
        ]),
        Unit(id="pf_u04", name="Set Theory and Functions", topics=[
            Topic(id="pf_017", name="Proving Set Identities", description=""),
            Topic(id="pf_018", name="Proving Properties of Functions", description=""),
            Topic(id="pf_019", name="Proving Cardinality Results", description=""),
            Topic(id="pf_020", name="Cantor's Diagonalization Argument (H)", description=""),
        ]),
        Unit(id="pf_u05", name="Number Theory Proofs", topics=[
            Topic(id="pf_021", name="Divisibility Proofs", description=""),
            Topic(id="pf_022", name="Proofs with Primes and the Fundamental Theorem", description=""),
            Topic(id="pf_023", name="Modular Arithmetic Proofs", description=""),
            Topic(id="pf_024", name="Famous Results: Infinitely Many Primes, Irrationality of √2", description=""),
            Topic(id="pf_025", name="Proofs Involving the Euclidean Algorithm", description=""),
        ]),
        Unit(id="pf_u06", name="Real Analysis Foundations", topics=[
            Topic(id="pf_026", name="The Completeness Axiom and Consequences", description=""),
            Topic(id="pf_027", name="Proving Inequalities (AM-GM, Cauchy-Schwarz)", description=""),
            Topic(id="pf_028", name="Sequences and Convergence Proofs", description=""),
            Topic(id="pf_029", name="Epsilon-Delta Proofs for Limits (H)", description=""),
            Topic(id="pf_030", name="Proofs of Continuity and Differentiability (H)", description=""),
        ]),
        Unit(id="pf_u07", name="Algebraic Structures (Introduction)", topics=[
            Topic(id="pf_031", name="Proving Group Axioms", description=""),
            Topic(id="pf_032", name="Subgroups and Cosets", description=""),
            Topic(id="pf_033", name="Homomorphisms and Isomorphisms (H)", description=""),
            Topic(id="pf_034", name="Introduction to Rings and Fields (H)", description=""),
        ]),
        Unit(id="pf_u08", name="Proof Writing and Mathematical Style", topics=[
            Topic(id="pf_035", name="Common Proof Mistakes and How to Avoid Them", description=""),
            Topic(id="pf_036", name="Writing Clear and Concise Proofs", description=""),
            Topic(id="pf_037", name="Proof Revision and Critique", description=""),
            Topic(id="pf_038", name="Reading and Presenting Research-Level Mathematics (H)", description=""),
        ]),
    ])


# ---------------------------------------------------------------------------
# Contest Math
# ---------------------------------------------------------------------------

def get_contest_math_course() -> Course:
    return Course(id="contest_math", name="Contest Mathematics", units=[
        Unit(id="cm_u01", name="Algebra Techniques", topics=[
            Topic(id="cm_001", name="Algebraic Manipulation and Clever Substitution", description=""),
            Topic(id="cm_002", name="Polynomials: Roots, Vieta's Formulas, and Symmetric Functions", description=""),
            Topic(id="cm_003", name="Inequalities: AM-GM, Cauchy-Schwarz, and Power Mean", description=""),
            Topic(id="cm_004", name="Functional Equations (H)", description=""),
            Topic(id="cm_005", name="Telescoping and Clever Summations", description=""),
        ]),
        Unit(id="cm_u02", name="Number Theory", topics=[
            Topic(id="cm_006", name="Divisibility and GCD Tricks", description=""),
            Topic(id="cm_007", name="Modular Arithmetic and Residues", description=""),
            Topic(id="cm_008", name="Diophantine Equations", description=""),
            Topic(id="cm_009", name="Number Bases and Representations", description=""),
            Topic(id="cm_010", name="Lifting the Exponent Lemma (H)", description=""),
            Topic(id="cm_011", name="Quadratic Residues (H)", description=""),
        ]),
        Unit(id="cm_u03", name="Combinatorics", topics=[
            Topic(id="cm_012", name="Counting Techniques and Bijections", description=""),
            Topic(id="cm_013", name="The Pigeonhole Principle", description=""),
            Topic(id="cm_014", name="Inclusion-Exclusion", description=""),
            Topic(id="cm_015", name="Recursion and Combinatorial Arguments", description=""),
            Topic(id="cm_016", name="Generating Functions (H)", description=""),
            Topic(id="cm_017", name="Double Counting and Combinatorial Identities (H)", description=""),
        ]),
        Unit(id="cm_u04", name="Geometry", topics=[
            Topic(id="cm_018", name="Triangle Centers and Classical Results", description=""),
            Topic(id="cm_019", name="Similar Triangles and Length Chasing", description=""),
            Topic(id="cm_020", name="Power of a Point and Radical Axes", description=""),
            Topic(id="cm_021", name="Circle Theorems and Cyclic Quadrilaterals", description=""),
            Topic(id="cm_022", name="Trigonometric Methods in Geometry (H)", description=""),
            Topic(id="cm_023", name="Projective Geometry and Cross-Ratios (H)", description=""),
            Topic(id="cm_024", name="Inversion (H)", description=""),
        ]),
        Unit(id="cm_u05", name="Probability and Combinatorics", topics=[
            Topic(id="cm_025", name="Basic Probability in Contest Settings", description=""),
            Topic(id="cm_026", name="Expected Value and Linearity of Expectation", description=""),
            Topic(id="cm_027", name="Geometric Probability", description=""),
            Topic(id="cm_028", name="Markov Chains in Contests (H)", description=""),
        ]),
        Unit(id="cm_u06", name="Sequences and Series", topics=[
            Topic(id="cm_029", name="Arithmetic and Geometric Series Tricks", description=""),
            Topic(id="cm_030", name="Telescoping Series", description=""),
            Topic(id="cm_031", name="Recurrence Relations", description=""),
            Topic(id="cm_032", name="Generating Functions for Sequences (H)", description=""),
        ]),
        Unit(id="cm_u07", name="Proof-Based Contest Problems", topics=[
            Topic(id="cm_033", name="Writing Rigorous Solutions (AMC/AIME Style)", description=""),
            Topic(id="cm_034", name="Olympiad Proof Structure (USAMO/IMO Style)", description=""),
            Topic(id="cm_035", name="Extremal Principle and Invariants", description=""),
            Topic(id="cm_036", name="Coloring and Tiling Arguments", description=""),
            Topic(id="cm_037", name="Graph Theory in Olympiad Problems (H)", description=""),
        ]),
        Unit(id="cm_u08", name="Competition Strategy and Problem Solving", topics=[
            Topic(id="cm_038", name="Working Backwards and Special Cases", description=""),
            Topic(id="cm_039", name="Symmetry and Pattern Recognition", description=""),
            Topic(id="cm_040", name="Estimation and Bounding", description=""),
            Topic(id="cm_041", name="Time Management and Partial Credit Strategy", description=""),
            Topic(id="cm_042", name="Mock Competitions and Problem Sets", description=""),
        ]),
    ])


# ---------------------------------------------------------------------------
# Probability
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Introduction to Probability and Statistics  (AP Stats / non-calculus)
# ---------------------------------------------------------------------------

def get_intro_prob_stats_course() -> Course:
    return Course(id="intro_prob_stats", name="Intro Probability and Stats", units=[
        Unit(id="ips_u01", name="Exploring and Visualizing Data", topics=[
            Topic(id="stat_001", name="Types of Data and Variables", description=""),
            Topic(id="stat_002", name="Frequency Distributions and Histograms", description=""),
            Topic(id="stat_003", name="Measures of Center: Mean, Median, Mode", description=""),
            Topic(id="stat_004", name="Measures of Spread: Range, IQR, Standard Deviation", description=""),
            Topic(id="stat_005", name="Box Plots and Five-Number Summary", description=""),
            Topic(id="stat_006", name="Outliers and Resistant Measures", description=""),
        ]),
        Unit(id="ips_u02", name="Bivariate Data and Linear Regression", topics=[
            Topic(id="stat_007", name="Scatter Plots and Association", description=""),
            Topic(id="stat_008", name="Correlation", description=""),
            Topic(id="stat_009", name="Introduction to Linear Regression", description=""),
            Topic(id="stat_010", name="Residuals and the Least Squares Line", description=""),
            Topic(id="stat_011", name="Interpreting Slope and Intercept", description=""),
            Topic(id="stat_012", name="Causation vs. Correlation", description=""),
        ]),
        Unit(id="ips_u03", name="Study Design and Data Collection", topics=[
            Topic(id="stat_013", name="Sampling Methods and Bias", description=""),
            Topic(id="stat_014", name="Observational Studies vs. Experiments", description=""),
            Topic(id="stat_015", name="Experimental Design: Control, Randomization, Replication", description=""),
            Topic(id="stat_016", name="Confounding Variables", description=""),
            Topic(id="stat_017", name="Surveys and Questionnaire Design", description=""),
        ]),
        Unit(id="ips_u04", name="Introduction to Probability", topics=[
            Topic(id="prob_001", name="Sample Spaces and Events", description=""),
            Topic(id="prob_002", name="Basic Probability Rules", description=""),
            Topic(id="prob_003", name="Equally Likely Outcomes", description=""),
            Topic(id="prob_004", name="Complement, Union, and Intersection", description=""),
            Topic(id="prob_005", name="Venn Diagrams and Probability", description=""),
        ]),
        Unit(id="ips_u05", name="Counting Methods", topics=[
            Topic(id="prob_006", name="The Multiplication Principle", description=""),
            Topic(id="prob_007", name="Permutations and Combinations", description=""),
            Topic(id="prob_008", name="Counting with Repetition", description=""),
            Topic(id="prob_009", name="The Binomial Theorem and Probability", description=""),
        ]),
        Unit(id="ips_u06", name="Conditional Probability", topics=[
            Topic(id="prob_010", name="Conditional Probability", description=""),
            Topic(id="prob_011", name="The Multiplication Rule", description=""),
            Topic(id="prob_012", name="Independent Events", description=""),
            Topic(id="prob_013", name="Bayes' Theorem", description=""),
            Topic(id="prob_014", name="Tree Diagrams", description=""),
        ]),
        Unit(id="ips_u07", name="Discrete Random Variables", topics=[
            Topic(id="prob_015", name="Introduction to Random Variables", description=""),
            Topic(id="prob_016", name="Probability Distributions and Histograms", description=""),
            Topic(id="prob_017", name="Expected Value", description=""),
            Topic(id="prob_018", name="Variance and Standard Deviation", description=""),
            Topic(id="prob_019", name="The Binomial Distribution", description=""),
            Topic(id="prob_020", name="The Geometric Distribution", description=""),
        ]),
        Unit(id="ips_u08", name="Continuous Distributions and the Normal", topics=[
            Topic(id="prob_023", name="Introduction to Continuous Distributions", description=""),
            Topic(id="prob_024", name="The Uniform Distribution", description=""),
            Topic(id="prob_025", name="The Normal Distribution", description=""),
            Topic(id="prob_026", name="Standard Normal and Z-Scores", description=""),
        ]),
        Unit(id="ips_u09", name="Sampling Distributions and the Central Limit Theorem", topics=[
            Topic(id="stat_021", name="Sampling Distributions", description=""),
            Topic(id="stat_022", name="The Central Limit Theorem", description=""),
            Topic(id="prob_036", name="Simulation and the Law of Large Numbers", description=""),
            Topic(id="prob_038", name="Normal Approximation to the Binomial", description=""),
        ]),
        Unit(id="ips_u10", name="Estimation and Confidence Intervals", topics=[
            Topic(id="stat_024", name="Introduction to Estimation", description=""),
            Topic(id="stat_025", name="Confidence Intervals for a Mean", description=""),
            Topic(id="stat_026", name="Confidence Intervals for a Proportion", description=""),
            Topic(id="stat_027", name="Margin of Error and Sample Size", description=""),
            Topic(id="stat_028", name="Interpreting Confidence Intervals", description=""),
        ]),
        Unit(id="ips_u11", name="Hypothesis Testing", topics=[
            Topic(id="stat_031", name="Introduction to Hypothesis Testing", description=""),
            Topic(id="stat_032", name="One-Sample t-Test for a Mean", description=""),
            Topic(id="stat_033", name="One-Sample z-Test for a Proportion", description=""),
            Topic(id="stat_034", name="Two-Sample Tests", description=""),
            Topic(id="stat_035", name="Type I and Type II Errors", description=""),
            Topic(id="stat_036", name="p-Values and Statistical Significance", description=""),
        ]),
        Unit(id="ips_u12", name="Categorical Data Analysis", topics=[
            Topic(id="stat_039", name="Chi-Square Goodness-of-Fit Test", description=""),
            Topic(id="stat_040", name="Chi-Square Test for Independence", description=""),
            Topic(id="stat_041", name="Two-Way Tables and Expected Counts", description=""),
        ]),
        Unit(id="ips_u13", name="Inference for Regression", topics=[
            Topic(id="stat_043", name="Testing the Slope of a Regression Line", description=""),
            Topic(id="stat_044", name="Confidence Intervals for Regression", description=""),
            Topic(id="stat_045", name="Residual Analysis and Conditions for Inference", description=""),
            Topic(id="prob_039", name="Probability in Everyday Decision Making", description=""),
        ]),
    ])


# ---------------------------------------------------------------------------
# Probability Theory  (STAT-134, calculus-based)
# prob_u04 requires Calculus III (multiple integrals for joint distributions)
# prob_u06 requires Calculus II (Taylor series for moment generating functions)
# ---------------------------------------------------------------------------

def get_probability_course() -> Course:
    return Course(id="probability", name="Probability Theory", units=[
        Unit(id="prob_u01", name="Probability Axioms and Foundations", topics=[
            Topic(id="pt_001", name="Probability Spaces, Sigma-Algebras, and Axioms", description=""),
            Topic(id="pt_002", name="Combinatorial Probability and Inclusion-Exclusion", description=""),
            Topic(id="pt_003", name="Conditional Probability and Bayes' Theorem", description=""),
            Topic(id="pt_004", name="Independence: Definitions and Implications", description=""),
        ]),
        Unit(id="prob_u02", name="Discrete Distributions", topics=[
            Topic(id="prob_021", name="The Poisson Distribution", description=""),
            Topic(id="prob_022", name="Moment Generating Functions for Discrete Distributions", description=""),
            Topic(id="prob_042", name="The Negative Binomial Distribution", description=""),
            Topic(id="prob_043", name="The Hypergeometric Distribution", description=""),
        ]),
        Unit(id="prob_u03", name="Continuous Distributions", topics=[
            Topic(id="prob_027", name="The Exponential Distribution", description=""),
            Topic(id="prob_028", name="Probability Density Functions and CDFs via Integration", description=""),
            Topic(id="prob_029", name="The Gamma and Beta Distributions", description=""),
            Topic(id="prob_044", name="The Chi-Squared Distribution", description=""),
        ]),
        Unit(id="prob_u04", name="Joint Distributions", topics=[
            Topic(id="prob_030", name="Joint Distributions (Discrete)", description=""),
            Topic(id="prob_031", name="Marginal and Conditional Distributions", description=""),
            Topic(id="prob_032", name="Covariance and Correlation", description=""),
            Topic(id="prob_033", name="Joint Continuous Distributions via Double Integrals", description=""),
        ]),
        Unit(id="prob_u05", name="Conditional Expectation", topics=[
            Topic(id="prob_034", name="The Law of Total Expectation", description=""),
            Topic(id="prob_045", name="Conditional Expectation E[X|Y] as a Random Variable", description=""),
            Topic(id="prob_046", name="The Law of Total Variance", description=""),
        ]),
        Unit(id="prob_u06", name="Transforms and Sums of Random Variables", topics=[
            Topic(id="prob_047", name="Moment Generating Functions for Continuous Distributions", description=""),
            Topic(id="prob_048", name="Convolutions and Sums of Independent Random Variables", description=""),
            Topic(id="prob_035", name="Transformations of Random Variables", description=""),
            Topic(id="prob_049", name="Order Statistics", description=""),
        ]),
        Unit(id="prob_u07", name="Special Distributions and Multivariate Theory", topics=[
            Topic(id="prob_050", name="The Bivariate Normal Distribution", description=""),
            Topic(id="prob_040", name="Introduction to Risk and Insurance Models", description=""),
        ]),
        Unit(id="prob_u08", name="Limit Theorems and Inequalities", topics=[
            Topic(id="prob_041", name="Convergence of Random Variables", description=""),
            Topic(id="prob_051", name="Markov and Chebyshev Inequalities", description=""),
            Topic(id="pt_005", name="The Weak Law of Large Numbers", description=""),
            Topic(id="pt_006", name="The Central Limit Theorem via Moment Generating Functions", description=""),
        ]),
        Unit(id="prob_u09", name="Markov Chains", topics=[
            Topic(id="prob_052", name="Introduction to Markov Chains", description=""),
            Topic(id="pt_007", name="Communication Classes and Irreducibility", description=""),
            Topic(id="pt_008", name="Stationary Distributions and Detailed Balance", description=""),
            Topic(id="pt_009", name="Convergence to Stationarity and Mixing Times", description=""),
        ]),
    ])


# ---------------------------------------------------------------------------
# Mathematical Statistics  (STAT-135 + Applied Econometrics)
# ---------------------------------------------------------------------------

def get_mathematical_statistics_course() -> Course:
    return Course(id="mathematical_statistics", name="Mathematical Statistics", units=[
        Unit(id="ms_u01", name="Statistical Models and Point Estimation", topics=[
            Topic(id="ms_001", name="Statistical Models and Sufficient Statistics", description=""),
            Topic(id="ms_002", name="Method of Moments", description=""),
            Topic(id="ms_003", name="Maximum Likelihood Estimation", description=""),
            Topic(id="ms_004", name="Properties of Estimators: Bias, Variance, and MSE", description=""),
            Topic(id="ms_005", name="Consistency and Asymptotic Properties", description=""),
        ]),
        Unit(id="ms_u02", name="Information Theory and Optimal Estimation", topics=[
            Topic(id="ms_006", name="Fisher Information and the Score Function", description=""),
            Topic(id="ms_007", name="The Cramér-Rao Lower Bound", description=""),
            Topic(id="ms_008", name="Complete Sufficient Statistics", description=""),
            Topic(id="ms_009", name="The Rao-Blackwell Theorem and UMVUE", description=""),
            Topic(id="ms_010", name="The Exponential Family of Distributions", description=""),
        ]),
        Unit(id="ms_u03", name="Bayesian Inference", topics=[
            Topic(id="ms_011", name="Prior and Posterior Distributions", description=""),
            Topic(id="ms_012", name="Conjugate Priors", description=""),
            Topic(id="ms_013", name="Bayesian Point Estimation and Credible Intervals", description=""),
            Topic(id="stat_030", name="Bootstrap Confidence Intervals", description=""),
        ]),
        Unit(id="ms_u04", name="Hypothesis Testing Theory", topics=[
            Topic(id="ms_014", name="The Neyman-Pearson Lemma", description=""),
            Topic(id="ms_015", name="Uniformly Most Powerful Tests", description=""),
            Topic(id="ms_016", name="Generalized Likelihood Ratio Tests", description=""),
            Topic(id="stat_029", name="Confidence Intervals via the t-Distribution", description=""),
            Topic(id="stat_037", name="Power of a Test and Sample Size Calculations", description=""),
            Topic(id="stat_038", name="Likelihood Ratio Tests", description=""),
        ]),
        Unit(id="ms_u05", name="Asymptotic Theory", topics=[
            Topic(id="stat_023", name="Derivation of Sampling Distributions via Integration", description=""),
            Topic(id="ms_017", name="Asymptotic Normality of the MLE", description=""),
            Topic(id="ms_018", name="The Delta Method", description=""),
            Topic(id="ms_019", name="Confidence Regions and Simultaneous Inference", description=""),
        ]),
        Unit(id="ms_u06", name="Nonparametric Methods", topics=[
            Topic(id="ms_020", name="Sign and Rank Tests: Wilcoxon and Mann-Whitney", description=""),
            Topic(id="ms_021", name="The Kolmogorov-Smirnov Goodness-of-Fit Test", description=""),
            Topic(id="stat_042", name="Fisher's Exact Test", description=""),
        ]),
        Unit(id="ms_u07", name="Linear Models", topics=[
            Topic(id="ms_022", name="The Linear Model in Matrix Form", description=""),
            Topic(id="ms_023", name="The Gauss-Markov Theorem", description=""),
            Topic(id="ms_024", name="Distribution Theory in Linear Regression", description=""),
            Topic(id="stat_046", name="Multiple Linear Regression", description=""),
            Topic(id="stat_048", name="Least Squares via Calculus", description=""),
            Topic(id="ms_025", name="Analysis of Variance", description=""),
        ]),
        Unit(id="ms_u08", name="Generalized Linear Models", topics=[
            Topic(id="stat_047", name="Logistic Regression", description=""),
            Topic(id="ms_026", name="Generalized Linear Models and Link Functions", description=""),
            Topic(id="ms_027", name="Poisson Regression and Count Data", description=""),
        ]),
        Unit(id="ms_u09", name="Applied Econometrics (H)", topics=[
            Topic(id="ms_028", name="Instrumental Variables and Two-Stage Least Squares (H)", description=""),
            Topic(id="ms_029", name="Heteroskedasticity and Robust Standard Errors (H)", description=""),
            Topic(id="ms_030", name="Panel Data: Fixed and Random Effects (H)", description=""),
            Topic(id="ms_031", name="Time Series: Stationarity, Autocorrelation, and ARIMA (H)", description=""),
        ]),
    ])
