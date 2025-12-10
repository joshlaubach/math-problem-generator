"""SAT Math concept map.

SAT concepts mostly reference core algebra, geometry, and statistics courses,
with a few test-specific meta-concepts added.
"""
from concepts import Concept, register_concept

# SAT Algebra (references Algebra 1 and 2)
register_concept(Concept(
    id="sat.algebra.linear_basics",
    name="Linear Equations and Inequalities",
    course_id="sat_math",
    unit_id="sat_algebra",
    topic_id="sat_linear",
    kind="definition",
    description="SAT-level linear equation and inequality solving",
    prerequisites=["alg1.linear_eq.one_step_int"],
    difficulty_min=1,
    difficulty_max=3,
    examples_latex=["$2x + 3 = 7$"],
    tags=["sat", "algebra"]
))

register_concept(Concept(
    id="sat.algebra.quadratic_solving",
    name="Quadratic Functions and Solving",
    course_id="sat_math",
    unit_id="sat_algebra",
    topic_id="sat_quadratic",
    kind="skill",
    description="SAT quadratic solving, graph interpretation",
    prerequisites=["alg2.quadratic.solving_methods"],
    difficulty_min=2,
    difficulty_max=4,
    examples_latex=["$x^2 - 5x + 6 = 0$"],
    tags=["sat", "quadratic"]
))

register_concept(Concept(
    id="sat.algebra.systems",
    name="Systems of Equations",
    course_id="sat_math",
    unit_id="sat_algebra",
    topic_id="sat_systems",
    kind="skill",
    description="SAT systems of linear equations",
    prerequisites=["alg1.systems.substitution"],
    difficulty_min=2,
    difficulty_max=3,
    examples_latex=["Solve two-variable systems"],
    tags=["sat"]
))

# SAT Geometry
register_concept(Concept(
    id="sat.geometry.shapes",
    name="Shapes, Area, and Volume",
    course_id="sat_math",
    unit_id="sat_geometry",
    topic_id="sat_geo_shapes",
    kind="skill",
    description="SAT area and perimeter of basic shapes",
    prerequisites=["geo.polygons.area_perimeter"],
    difficulty_min=2,
    difficulty_max=3,
    examples_latex=["$A = \\pi r^2$"],
    tags=["sat", "geometry"]
))

register_concept(Concept(
    id="sat.geometry.trigonometry",
    name="Trigonometry Basics",
    course_id="sat_math",
    unit_id="sat_geometry",
    topic_id="sat_geo_trig",
    kind="definition",
    description="Basic trig ratios for SAT",
    prerequisites=["precalc.trig.ratios"],
    difficulty_min=2,
    difficulty_max=3,
    examples_latex=["SOHCAHTOA"],
    tags=["sat", "trigonometry"]
))

# SAT Numbers and Operations
register_concept(Concept(
    id="sat.numbers.ratios_percents",
    name="Ratios and Percentages",
    course_id="sat_math",
    unit_id="sat_numbers",
    topic_id="sat_ratios",
    kind="skill",
    description="SAT ratio and percent problems",
    prerequisites=["prealg.percent.applications"],
    difficulty_min=1,
    difficulty_max=3,
    examples_latex=["$15\\% \\text{ of } x = ?$"],
    tags=["sat"]
))

register_concept(Concept(
    id="sat.numbers.exponents_radicals",
    name="Exponents and Radicals",
    course_id="sat_math",
    unit_id="sat_numbers",
    topic_id="sat_exponents",
    kind="skill",
    description="SAT exponent and radical manipulation",
    prerequisites=["alg2.exponential.growth_decay"],
    difficulty_min=2,
    difficulty_max=3,
    examples_latex=["$\\sqrt{x}$, $x^{2/3}$"],
    tags=["sat"]
))

# SAT Data Analysis
register_concept(Concept(
    id="sat.data.statistics",
    name="Statistics and Probability",
    course_id="sat_math",
    unit_id="sat_data",
    topic_id="sat_statistics",
    kind="skill",
    description="SAT-level statistics and probability",
    prerequisites=["probstat.distributions.normal"],
    difficulty_min=2,
    difficulty_max=4,
    examples_latex=["Mean, median, mode", "Basic probability"],
    tags=["sat", "statistics"]
))

# Test-specific
register_concept(Concept(
    id="sat.test_strategy.time_management",
    name="Time Management and Strategy",
    course_id="sat_math",
    unit_id="sat_algebra",
    topic_id="sat_linear",
    kind="strategy",
    description="Strategies for SAT test-taking",
    prerequisites=[],
    difficulty_min=1,
    difficulty_max=2,
    examples_latex=["Eliminate wrong answers"],
    tags=["sat", "test_strategy"]
))

register_concept(Concept(
    id="sat.test_strategy.calculator_use",
    name="Calculator and No-Calculator Sections",
    course_id="sat_math",
    unit_id="sat_algebra",
    topic_id="sat_linear",
    kind="strategy",
    description="Managing calculator and non-calculator sections",
    prerequisites=[],
    difficulty_min=1,
    difficulty_max=1,
    examples_latex=["Know when to use calculator"],
    tags=["sat", "test_strategy"]
))
