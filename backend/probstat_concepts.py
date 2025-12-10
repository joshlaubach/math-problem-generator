"""Probability and Statistics concept map."""
from concepts import Concept, register_concept

# Combinatorics
register_concept(Concept(
    id="probstat.combinatorics.permutations",
    name="Permutations",
    course_id="probstat",
    unit_id="probstat_combinatorics",
    topic_id="probstat_permutations",
    kind="skill",
    description="Counting permutations; factorials",
    prerequisites=[],
    difficulty_min=2,
    difficulty_max=3,
    examples_latex=["$P(n,r) = \\frac{n!}{(n-r)!}$"],
    tags=["combinatorics"]
))

register_concept(Concept(
    id="probstat.combinatorics.combinations",
    name="Combinations",
    course_id="probstat",
    unit_id="probstat_combinatorics",
    topic_id="probstat_combinations",
    kind="skill",
    description="Counting combinations; binomial coefficients",
    prerequisites=["probstat.combinatorics.permutations"],
    difficulty_min=2,
    difficulty_max=3,
    examples_latex=["$C(n,r) = \\binom{n}{r} = \\frac{n!}{r!(n-r)!}$"],
    tags=["combinatorics"]
))

# Probability
register_concept(Concept(
    id="probstat.probability.basics",
    name="Basic Probability",
    course_id="probstat",
    unit_id="probstat_probability",
    topic_id="probstat_basic_prob",
    kind="definition",
    description="Probability rules; sample spaces; events",
    prerequisites=[],
    difficulty_min=2,
    difficulty_max=3,
    examples_latex=["$P(A) = \\frac{\\text{favorable}}{\\text{total}}$"],
    tags=["probability"]
))

register_concept(Concept(
    id="probstat.probability.conditional",
    name="Conditional Probability",
    course_id="probstat",
    unit_id="probstat_probability",
    topic_id="probstat_conditional",
    kind="skill",
    description="Conditional probability; independence; Bayes' theorem",
    prerequisites=["probstat.probability.basics"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$P(A|B) = \\frac{P(A \\cap B)}{P(B)}$"],
    tags=["probability"]
))

register_concept(Concept(
    id="probstat.probability.random_variables",
    name="Random Variables and Expectation",
    course_id="probstat",
    unit_id="probstat_probability",
    topic_id="probstat_random_variables",
    kind="definition",
    description="Discrete and continuous random variables; expected value; variance",
    prerequisites=["probstat.probability.conditional"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$E[X] = \\sum x \\cdot P(X=x)$"],
    tags=["random_variables"]
))

# Distributions
register_concept(Concept(
    id="probstat.distributions.discrete",
    name="Discrete Distributions",
    course_id="probstat",
    unit_id="probstat_distributions",
    topic_id="probstat_discrete_dist",
    kind="definition",
    description="Binomial, Poisson, and other discrete distributions",
    prerequisites=["probstat.probability.random_variables"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$P(X=k) = \\binom{n}{k}p^k(1-p)^{n-k}$"],
    tags=["distributions"]
))

register_concept(Concept(
    id="probstat.distributions.normal",
    name="Normal Distribution",
    course_id="probstat",
    unit_id="probstat_distributions",
    topic_id="probstat_continuous_dist",
    kind="definition",
    description="Normal distribution; z-scores; standardization",
    prerequisites=["probstat.distributions.discrete"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$P(a < X < b) = \\int_a^b \\frac{1}{\\sigma\\sqrt{2\\pi}} e^{-(x-\\mu)^2/(2\\sigma^2)} dx$"],
    tags=["normal_distribution"]
))

# Statistics
register_concept(Concept(
    id="probstat.statistics.descriptive",
    name="Descriptive Statistics",
    course_id="probstat",
    unit_id="probstat_statistics",
    topic_id="probstat_descriptive",
    kind="definition",
    description="Mean, median, mode, standard deviation, correlation",
    prerequisites=["probstat.distributions.normal"],
    difficulty_min=1,
    difficulty_max=3,
    examples_latex=["$\\bar{x} = \\frac{1}{n}\\sum x_i$", "$s = \\sqrt{\\frac{\\sum(x_i - \\bar{x})^2}{n-1}}$"],
    tags=["statistics"]
))

register_concept(Concept(
    id="probstat.statistics.sampling_distributions",
    name="Sampling Distributions",
    course_id="probstat",
    unit_id="probstat_statistics",
    topic_id="probstat_descriptive",
    kind="definition",
    description="Distribution of sample means; central limit theorem",
    prerequisites=["probstat.statistics.descriptive"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$\\mu_{\\bar{x}} = \\mu$", "$\\sigma_{\\bar{x}} = \\frac{\\sigma}{\\sqrt{n}}$"],
    tags=["statistics"]
))

register_concept(Concept(
    id="probstat.statistics.confidence_intervals",
    name="Confidence Intervals",
    course_id="probstat",
    unit_id="probstat_statistics",
    topic_id="probstat_confidence",
    kind="skill",
    description="Constructing confidence intervals for means and proportions",
    prerequisites=["probstat.statistics.sampling_distributions"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$\\bar{x} \\pm z^* \\frac{s}{\\sqrt{n}}$"],
    tags=["inference"]
))

register_concept(Concept(
    id="probstat.statistics.hypothesis_testing",
    name="Hypothesis Testing",
    course_id="probstat",
    unit_id="probstat_statistics",
    topic_id="probstat_hypothesis",
    kind="skill",
    description="Hypothesis tests; p-values; Type I and II errors",
    prerequisites=["probstat.statistics.confidence_intervals"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$H_0: \\mu = \\mu_0$ vs $H_a: \\mu \\neq \\mu_0$"],
    tags=["hypothesis_testing"]
))

register_concept(Concept(
    id="probstat.statistics.regression",
    name="Linear Regression",
    course_id="probstat",
    unit_id="probstat_statistics",
    topic_id="probstat_hypothesis",
    kind="skill",
    description="Fitting linear models; least squares; correlation and causation",
    prerequisites=["probstat.statistics.hypothesis_testing"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$\\hat{y} = a + bx$"],
    tags=["regression"]
))
