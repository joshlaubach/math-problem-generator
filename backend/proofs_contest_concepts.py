"""Proofs and Contest Math concept map."""
from concepts import Concept, register_concept

# Logic and Proof Techniques
register_concept(Concept(
    id="proofs.logic.statements",
    name="Logical Statements and Connectives",
    course_id="proofs_contest",
    unit_id="proofs_logic",
    topic_id="proofs_logic_basics",
    kind="definition",
    description="Truth tables, logical operators, tautologies",
    prerequisites=[],
    difficulty_min=2,
    difficulty_max=3,
    examples_latex=["$p \\land q$, $p \\lor q$, $\\neg p$"],
    tags=["logic"]
))

register_concept(Concept(
    id="proofs.logic.direct_proof",
    name="Direct Proof",
    course_id="proofs_contest",
    unit_id="proofs_logic",
    topic_id="proofs_direct",
    kind="definition",
    description="Proving statements directly from axioms and theorems",
    prerequisites=["proofs.logic.statements"],
    difficulty_min=2,
    difficulty_max=4,
    examples_latex=["If $p$ then $q$"],
    tags=["proof_techniques"]
))

register_concept(Concept(
    id="proofs.logic.contradiction",
    name="Proof by Contradiction",
    course_id="proofs_contest",
    unit_id="proofs_logic",
    topic_id="proofs_contradiction",
    kind="definition",
    description="Assuming negation and deriving contradiction",
    prerequisites=["proofs.logic.direct_proof"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["Assume $\\neg p$"],
    tags=["proof_techniques"]
))

register_concept(Concept(
    id="proofs.logic.induction",
    name="Mathematical Induction",
    course_id="proofs_contest",
    unit_id="proofs_logic",
    topic_id="proofs_induction",
    kind="skill",
    description="Proof by induction; base case and inductive step",
    prerequisites=["proofs.logic.direct_proof"],
    difficulty_min=3,
    difficulty_max=5,
    examples_latex=["Base case: $P(1)$", "Inductive step: $P(k) \\Rightarrow P(k+1)$"],
    tags=["induction"]
))

# Inequalities
register_concept(Concept(
    id="proofs.inequalities.techniques",
    name="Inequality Proof Techniques",
    course_id="proofs_contest",
    unit_id="proofs_inequalities",
    topic_id="proofs_ineq_techniques",
    kind="skill",
    description="AM-GM, Cauchy-Schwarz, rearrangement inequality",
    prerequisites=["proofs.logic.induction"],
    difficulty_min=4,
    difficulty_max=6,
    examples_latex=["AM-GM: $\\frac{a+b}{2} \\geq \\sqrt{ab}$"],
    tags=["inequalities"]
))

register_concept(Concept(
    id="proofs.inequalities.optimization",
    name="Optimization and Extrema",
    course_id="proofs_contest",
    unit_id="proofs_inequalities",
    topic_id="proofs_optimization",
    kind="skill",
    description="Finding maxima and minima; constrained optimization",
    prerequisites=["proofs.inequalities.techniques"],
    difficulty_min=4,
    difficulty_max=6,
    examples_latex=["Lagrange multipliers"],
    tags=["optimization"]
))

# Number Theory
register_concept(Concept(
    id="proofs.numbertheory.divisibility",
    name="Divisibility and Prime Numbers",
    course_id="proofs_contest",
    unit_id="proofs_numbertheory",
    topic_id="proofs_divisibility",
    kind="definition",
    description="Divisibility rules, fundamental theorem of arithmetic",
    prerequisites=[],
    difficulty_min=2,
    difficulty_max=3,
    examples_latex=["$a | b$ means $\\exists k: b = ak$"],
    tags=["number_theory"]
))

register_concept(Concept(
    id="proofs.numbertheory.modular",
    name="Modular Arithmetic",
    course_id="proofs_contest",
    unit_id="proofs_numbertheory",
    topic_id="proofs_modular",
    kind="skill",
    description="Congruences, modular operations, applications",
    prerequisites=["proofs.numbertheory.divisibility"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$a \\equiv b \\pmod{n}$"],
    tags=["number_theory"]
))

# Combinatorics
register_concept(Concept(
    id="proofs.combinatorics.counting",
    name="Counting and Pigeonhole Principle",
    course_id="proofs_contest",
    unit_id="proofs_combinatorics",
    topic_id="proofs_counting",
    kind="skill",
    description="Advanced counting; pigeonhole principle; inclusion-exclusion",
    prerequisites=["probstat.combinatorics.combinations"],
    difficulty_min=3,
    difficulty_max=5,
    examples_latex=["Inclusion-exclusion principle"],
    tags=["combinatorics"]
))

register_concept(Concept(
    id="proofs.combinatorics.graph_theory",
    name="Basic Graph Theory",
    course_id="proofs_contest",
    unit_id="proofs_combinatorics",
    topic_id="proofs_graph_theory",
    kind="definition",
    description="Graphs, paths, cycles, colorings",
    prerequisites=["proofs.combinatorics.counting"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["Vertices, edges, degree"],
    tags=["graph_theory"]
))
