"""Linear Algebra concept map."""
from concepts import Concept, register_concept

# Vectors and Vector Spaces
register_concept(Concept(
    id="linalg.vectors.operations",
    name="Vector Operations and Norms",
    course_id="linear_algebra",
    unit_id="linalg_vectors",
    topic_id="linalg_vector_basics",
    kind="definition",
    description="Vector addition, scalar multiplication, dot product, norms",
    prerequisites=[],
    difficulty_min=2,
    difficulty_max=3,
    examples_latex=["$\\|\\vec{v}\\| = \\sqrt{v_1^2 + v_2^2 + \\ldots + v_n^2}$"],
    tags=["vectors"]
))

register_concept(Concept(
    id="linalg.vectors.linear_combination",
    name="Linear Combinations and Span",
    course_id="linear_algebra",
    unit_id="linalg_vectors",
    topic_id="linalg_vector_basics",
    kind="definition",
    description="Linear combinations; span of vectors",
    prerequisites=["linalg.vectors.operations"],
    difficulty_min=2,
    difficulty_max=3,
    examples_latex=["$c_1\\vec{v}_1 + c_2\\vec{v}_2 + \\ldots + c_n\\vec{v}_n$"],
    tags=["vectors"]
))

register_concept(Concept(
    id="linalg.vectors.linear_independence",
    name="Linear Independence and Dependence",
    course_id="linear_algebra",
    unit_id="linalg_vectors",
    topic_id="linalg_vector_basics",
    kind="definition",
    description="Linear independence; basis identification",
    prerequisites=["linalg.vectors.linear_combination"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["Linearly independent if only trivial solution to $c_1\\vec{v}_1 + \\ldots = \\vec{0}$"],
    tags=["vectors"]
))

register_concept(Concept(
    id="linalg.vectors.subspaces",
    name="Subspaces",
    course_id="linear_algebra",
    unit_id="linalg_vectors",
    topic_id="linalg_subspaces",
    kind="definition",
    description="Subspace axioms; column space and null space",
    prerequisites=["linalg.vectors.linear_independence"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["Col(A), Nul(A)"],
    tags=["subspaces"]
))

# Matrices
register_concept(Concept(
    id="linalg.matrices.operations",
    name="Matrix Operations",
    course_id="linear_algebra",
    unit_id="linalg_matrices",
    topic_id="linalg_matrix_ops",
    kind="skill",
    description="Matrix addition, multiplication, transpose",
    prerequisites=[],
    difficulty_min=2,
    difficulty_max=3,
    examples_latex=["$AB \\neq BA$ in general"],
    tags=["matrices"]
))

register_concept(Concept(
    id="linalg.matrices.determinant",
    name="Determinants",
    course_id="linear_algebra",
    unit_id="linalg_matrices",
    topic_id="linalg_determinants",
    kind="skill",
    description="Computing determinants; properties and applications",
    prerequisites=["linalg.matrices.operations"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$\\det(A) = ad - bc$ for $2 \\times 2$ matrix"],
    tags=["determinants"]
))

register_concept(Concept(
    id="linalg.matrices.inverse",
    name="Matrix Inverse",
    course_id="linear_algebra",
    unit_id="linalg_matrices",
    topic_id="linalg_inverse",
    kind="skill",
    description="Computing and using matrix inverse",
    prerequisites=["linalg.matrices.determinant"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$A^{-1}A = I$"],
    tags=["matrices"]
))

# Systems of Linear Equations
register_concept(Concept(
    id="linalg.systems.elimination",
    name="Gaussian Elimination and Row Reduction",
    course_id="linear_algebra",
    unit_id="linalg_systems",
    topic_id="linalg_gauss_elimination",
    kind="skill",
    description="Row reduction; RREF; solving systems",
    prerequisites=["linalg.matrices.operations"],
    difficulty_min=2,
    difficulty_max=3,
    examples_latex=["Row operations", "RREF"],
    tags=["systems"]
))

register_concept(Concept(
    id="linalg.systems.rank_nullity",
    name="Rank, Nullity, and the Rank-Nullity Theorem",
    course_id="linear_algebra",
    unit_id="linalg_systems",
    topic_id="linalg_rank_nullity",
    kind="definition",
    description="Rank and nullity of a matrix; rank-nullity theorem",
    prerequisites=["linalg.systems.elimination", "linalg.vectors.subspaces"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$\\text{rank}(A) + \\text{nullity}(A) = n$"],
    tags=["rank_nullity"]
))

# Eigenvalues and Eigenvectors
register_concept(Concept(
    id="linalg.eigen.characteristic_polynomial",
    name="Characteristic Polynomial",
    course_id="linear_algebra",
    unit_id="linalg_eigenvalues",
    topic_id="linalg_characteristic_poly",
    kind="definition",
    description="Finding eigenvalues; characteristic polynomial",
    prerequisites=["linalg.matrices.inverse"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$\\det(A - \\lambda I) = 0$"],
    tags=["eigenvalues"]
))

register_concept(Concept(
    id="linalg.eigen.eigenvectors",
    name="Eigenvectors and Eigenspaces",
    course_id="linear_algebra",
    unit_id="linalg_eigenvalues",
    topic_id="linalg_characteristic_poly",
    kind="definition",
    description="Finding eigenvectors; eigenspaces",
    prerequisites=["linalg.eigen.characteristic_polynomial"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["$(A - \\lambda I)\\vec{v} = \\vec{0}$"],
    tags=["eigenvectors"]
))

register_concept(Concept(
    id="linalg.eigen.diagonalization",
    name="Diagonalization",
    course_id="linear_algebra",
    unit_id="linalg_eigenvalues",
    topic_id="linalg_diagonalization",
    kind="skill",
    description="Diagonalizing matrices; similarity transformations",
    prerequisites=["linalg.eigen.eigenvectors"],
    difficulty_min=4,
    difficulty_max=5,
    examples_latex=["$A = PDP^{-1}$"],
    tags=["diagonalization"]
))
