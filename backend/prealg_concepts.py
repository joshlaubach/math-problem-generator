"""
Pre-Algebra concept map.

Defines concepts for Pre-Algebra covering integers, fractions, decimals,
ratios, proportions, and percentages.
"""

from concepts import Concept, register_concept, ConceptKind


# ============================================================================
# Pre-Algebra: Integers
# ============================================================================

register_concept(Concept(
    id="prealg.integers.number_line",
    name="Number Line and Ordering",
    course_id="prealgebra",
    unit_id="prealg_integers",
    topic_id="prealg_int_add_sub",
    kind="definition",
    description="Understanding positive, negative, and zero on the number line; ordering integers",
    prerequisites=[],
    difficulty_min=1,
    difficulty_max=2,
    examples_latex=["$-3 < -1 < 2$"],
    tags=["integers", "ordering"]
))

register_concept(Concept(
    id="prealg.integers.add_subtract",
    name="Integer Addition and Subtraction",
    course_id="prealgebra",
    unit_id="prealg_integers",
    topic_id="prealg_int_add_sub",
    kind="skill",
    description="Adding and subtracting integers using rules for same/different signs",
    prerequisites=["prealg.integers.number_line"],
    difficulty_min=1,
    difficulty_max=3,
    examples_latex=["$5 + (-3) = 2$", "$-4 - 2 = -6$"],
    tags=["integers", "operations"]
))

register_concept(Concept(
    id="prealg.integers.multiply_divide",
    name="Integer Multiplication and Division",
    course_id="prealgebra",
    unit_id="prealg_integers",
    topic_id="prealg_int_mul_div",
    kind="skill",
    description="Multiplying and dividing integers; sign rules",
    prerequisites=["prealg.integers.add_subtract"],
    difficulty_min=1,
    difficulty_max=3,
    examples_latex=["$(-3) \\times 4 = -12$", "$-12 \\div (-4) = 3$"],
    tags=["integers", "operations"]
))

# ============================================================================
# Pre-Algebra: Fractions
# ============================================================================

register_concept(Concept(
    id="prealg.fractions.basics",
    name="Fraction Basics and Equivalence",
    course_id="prealgebra",
    unit_id="prealg_fractions",
    topic_id="prealg_frac_basics",
    kind="definition",
    description="Parts of fractions, equivalent fractions, simplifying",
    prerequisites=[],
    difficulty_min=1,
    difficulty_max=2,
    examples_latex=["$\\frac{2}{4} = \\frac{1}{2}$"],
    tags=["fractions"]
))

register_concept(Concept(
    id="prealg.fractions.add_subtract",
    name="Adding and Subtracting Fractions",
    course_id="prealgebra",
    unit_id="prealg_fractions",
    topic_id="prealg_frac_ops",
    kind="skill",
    description="Adding/subtracting fractions with same and different denominators",
    prerequisites=["prealg.fractions.basics"],
    difficulty_min=2,
    difficulty_max=3,
    examples_latex=["$\\frac{1}{3} + \\frac{1}{6} = \\frac{1}{2}$"],
    tags=["fractions", "operations"]
))

register_concept(Concept(
    id="prealg.fractions.multiply_divide",
    name="Multiplying and Dividing Fractions",
    course_id="prealgebra",
    unit_id="prealg_fractions",
    topic_id="prealg_frac_ops",
    kind="skill",
    description="Multiplying and dividing fractions; reciprocals",
    prerequisites=["prealg.fractions.basics"],
    difficulty_min=2,
    difficulty_max=3,
    examples_latex=["$\\frac{2}{3} \\times \\frac{3}{4} = \\frac{1}{2}$"],
    tags=["fractions", "operations"]
))

register_concept(Concept(
    id="prealg.decimals.basics",
    name="Decimal Representation and Operations",
    course_id="prealgebra",
    unit_id="prealg_fractions",
    topic_id="prealg_decimals",
    kind="skill",
    description="Decimal place value, operations with decimals, converting between fractions and decimals",
    prerequisites=["prealg.fractions.basics"],
    difficulty_min=1,
    difficulty_max=3,
    examples_latex=["$0.5 = \\frac{1}{2}$", "$1.25 + 2.75 = 4$"],
    tags=["decimals"]
))

# ============================================================================
# Pre-Algebra: Ratios and Proportions
# ============================================================================

register_concept(Concept(
    id="prealg.ratios.basic",
    name="Ratios and Rates",
    course_id="prealgebra",
    unit_id="prealg_ratios",
    topic_id="prealg_ratios_props",
    kind="definition",
    description="Understanding ratios, equivalent ratios, rates",
    prerequisites=["prealg.fractions.basics"],
    difficulty_min=2,
    difficulty_max=3,
    examples_latex=["$3:4$", "$\\text{50 miles per hour}$"],
    tags=["ratios"]
))

register_concept(Concept(
    id="prealg.ratios.proportions",
    name="Proportions and Cross-Multiplication",
    course_id="prealgebra",
    unit_id="prealg_ratios",
    topic_id="prealg_ratios_props",
    kind="skill",
    description="Solving proportions; identifying proportional relationships",
    prerequisites=["prealg.ratios.basic"],
    difficulty_min=2,
    difficulty_max=4,
    examples_latex=["$\\frac{3}{4} = \\frac{x}{8}$"],
    tags=["proportions"]
))

register_concept(Concept(
    id="prealg.percent.basic",
    name="Percentages Basics",
    course_id="prealgebra",
    unit_id="prealg_ratios",
    topic_id="prealg_percent",
    kind="definition",
    description="Understanding percentages; converting between decimals, fractions, and percents",
    prerequisites=["prealg.decimals.basics"],
    difficulty_min=2,
    difficulty_max=3,
    examples_latex=["$50\\% = 0.5 = \\frac{1}{2}$"],
    tags=["percent"]
))

register_concept(Concept(
    id="prealg.percent.applications",
    name="Percent Problems",
    course_id="prealgebra",
    unit_id="prealg_ratios",
    topic_id="prealg_percent",
    kind="skill",
    description="Finding percent of a number, percent increase/decrease, discount",
    prerequisites=["prealg.percent.basic", "prealg.ratios.proportions"],
    difficulty_min=2,
    difficulty_max=4,
    examples_latex=["$15\\% \\text{ of } 60 = 9$"],
    tags=["percent", "applications"]
))
