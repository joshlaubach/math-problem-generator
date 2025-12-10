"""Calculus II concept map."""
from concepts import Concept, register_concept

# Integration Techniques
register_concept(Concept(
    id="calc2.integration.by_parts",
    name="Integration by Parts",
    course_id="calculus_2",
    unit_id="calc2_integration_tech",
    topic_id="calc2_integration_parts",
    kind="skill",
    description="Integration by parts formula; repeated application",
    prerequisites=["calc1.integration.substitution"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$\\int u \\, dv = uv - \\int v \\, du$"],
    tags=["integration"]
))

register_concept(Concept(
    id="calc2.integration.partial_fractions",
    name="Partial Fraction Decomposition",
    course_id="calculus_2",
    unit_id="calc2_integration_tech",
    topic_id="calc2_partial_fractions",
    kind="skill",
    description="Decomposing rational functions for integration",
    prerequisites=["calc1.integration.substitution", "alg2.rational.operations"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$\\frac{1}{(x-1)(x+2)}$"],
    tags=["integration"]
))

register_concept(Concept(
    id="calc2.integration.trig_substitution",
    name="Trigonometric Substitution",
    course_id="calculus_2",
    unit_id="calc2_integration_tech",
    topic_id="calc2_trig_substitution",
    kind="skill",
    description="Using trig substitution for integrals with radicals",
    prerequisites=["calc1.integration.substitution", "precalc.trig.identities"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$\\int \\sqrt{a^2 - x^2} \\, dx$"],
    tags=["integration"]
))

# Applications of Integration
register_concept(Concept(
    id="calc2.applications.area",
    name="Area Between Curves",
    course_id="calculus_2",
    unit_id="calc2_applications",
    topic_id="calc2_area",
    kind="skill",
    description="Computing area between two curves",
    prerequisites=["calc1.integration.definite_integral"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$A = \\int_a^b [f(x) - g(x)] \\, dx$"],
    tags=["applications"]
))

register_concept(Concept(
    id="calc2.applications.volume_disk_shell",
    name="Volume: Disk and Shell Methods",
    course_id="calculus_2",
    unit_id="calc2_applications",
    topic_id="calc2_volume",
    kind="skill",
    description="Computing volume of solids of revolution",
    prerequisites=["calc2.applications.area"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$V = \\pi \\int_a^b [R(x)]^2 \\, dx$"],
    tags=["applications"]
))

register_concept(Concept(
    id="calc2.applications.arc_length",
    name="Arc Length and Surface Area",
    course_id="calculus_2",
    unit_id="calc2_applications",
    topic_id="calc2_arc_length",
    kind="skill",
    description="Computing arc length and surface area of revolution",
    prerequisites=["calc2.applications.volume_disk_shell"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$L = \\int_a^b \\sqrt{1 + [f'(x)]^2} \\, dx$"],
    tags=["applications"]
))

# Sequences and Series
register_concept(Concept(
    id="calc2.sequences.definitions",
    name="Sequences and Limits",
    course_id="calculus_2",
    unit_id="calc2_sequences",
    topic_id="calc2_sequences",
    kind="definition",
    description="Infinite sequences; convergence and divergence",
    prerequisites=["calc1.limits.evaluation"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$a_n = \\frac{1}{n}$"],
    tags=["sequences"]
))

register_concept(Concept(
    id="calc2.series.convergence_tests",
    name="Series Convergence Tests",
    course_id="calculus_2",
    unit_id="calc2_sequences",
    topic_id="calc2_series_convergence",
    kind="skill",
    description="Geometric, harmonic, integral, comparison, ratio tests",
    prerequisites=["calc2.sequences.definitions"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$\\sum_{n=1}^{\\infty} \\frac{1}{n^2}$ converges"],
    tags=["series"]
))

register_concept(Concept(
    id="calc2.series.alternating",
    name="Alternating Series and Absolute Convergence",
    course_id="calculus_2",
    unit_id="calc2_sequences",
    topic_id="calc2_series_convergence",
    kind="skill",
    description="Alternating series test; absolute vs conditional convergence",
    prerequisites=["calc2.series.convergence_tests"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$\\sum_{n=1}^{\\infty} \\frac{(-1)^n}{n}$"],
    tags=["series"]
))

register_concept(Concept(
    id="calc2.series.power_series",
    name="Power Series and Taylor Series",
    course_id="calculus_2",
    unit_id="calc2_sequences",
    topic_id="calc2_power_series",
    kind="definition",
    description="Power series; radius and interval of convergence; Taylor expansions",
    prerequisites=["calc2.series.alternating"],
    difficulty_min=5,
    difficulty_max=6,
    examples_latex=["$\\sum_{n=0}^{\\infty} \\frac{f^{(n)}(a)}{n!}(x-a)^n$"],
    tags=["power_series"]
))

register_concept(Concept(
    id="calc2.series.taylor_maclaurin",
    name="Taylor and Maclaurin Series",
    course_id="calculus_2",
    unit_id="calc2_sequences",
    topic_id="calc2_power_series",
    kind="skill",
    description="Finding Taylor series representations of functions",
    prerequisites=["calc2.series.power_series"],
    difficulty_min=5,
    difficulty_max=6,
    examples_latex=["$e^x = \\sum_{n=0}^{\\infty} \\frac{x^n}{n!}$"],
    tags=["taylor"]
))
