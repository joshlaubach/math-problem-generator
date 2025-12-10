"""Geometry concept map."""
from concepts import Concept, register_concept

# Foundations
register_concept(Concept(
    id="geo.foundations.points_lines_angles",
    name="Points, Lines, and Angles",
    course_id="geometry",
    unit_id="geo_foundations",
    topic_id="geo_points_lines",
    kind="definition",
    description="Basic geometric objects and definitions",
    prerequisites=[],
    difficulty_min=1,
    difficulty_max=2,
    examples_latex=["$\\angle ABC$", "Collinear points"],
    tags=["foundations"]
))

register_concept(Concept(
    id="geo.foundations.angle_pairs",
    name="Angle Pair Relationships",
    course_id="geometry",
    unit_id="geo_foundations",
    topic_id="geo_angle_relationships",
    kind="definition",
    description="Complementary, supplementary, vertical angles",
    prerequisites=["geo.foundations.points_lines_angles"],
    difficulty_min=1,
    difficulty_max=2,
    examples_latex=["Vertical angles are congruent"],
    tags=["angles"]
))

register_concept(Concept(
    id="geo.foundations.parallel_lines",
    name="Parallel Lines and Transversals",
    course_id="geometry",
    unit_id="geo_foundations",
    topic_id="geo_angle_relationships",
    kind="skill",
    description="Corresponding angles, alternate interior angles",
    prerequisites=["geo.foundations.angle_pairs"],
    difficulty_min=2,
    difficulty_max=3,
    examples_latex=["Corresponding angles are equal"],
    tags=["parallel", "angles"]
))

# Triangles
register_concept(Concept(
    id="geo.triangles.triangle_types",
    name="Triangle Classification",
    course_id="geometry",
    unit_id="geo_triangles",
    topic_id="geo_triangle_congruence",
    kind="definition",
    description="Classification by sides and angles",
    prerequisites=["geo.foundations.points_lines_angles"],
    difficulty_min=1,
    difficulty_max=2,
    examples_latex=["Equilateral, isoceles, scalene"],
    tags=["triangles"]
))

register_concept(Concept(
    id="geo.triangles.congruence_postulates",
    name="Congruence Postulates (SSS, SAS, ASA)",
    course_id="geometry",
    unit_id="geo_triangles",
    topic_id="geo_triangle_congruence",
    kind="definition",
    description="Criteria for triangle congruence",
    prerequisites=["geo.triangles.triangle_types"],
    difficulty_min=2,
    difficulty_max=3,
    examples_latex=["SAS \\Rightarrow \\text{congruent}"],
    tags=["congruence"]
))

register_concept(Concept(
    id="geo.triangles.similarity_ratios",
    name="Triangle Similarity and Ratios",
    course_id="geometry",
    unit_id="geo_triangles",
    topic_id="geo_triangle_similarity",
    kind="definition",
    description="AA, SSS, SAS similarity; proportional sides",
    prerequisites=["geo.triangles.congruence_postulates", "prealg.ratios.proportions"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["\\text{AA} \\Rightarrow \\text{similar}"],
    tags=["similarity"]
))

register_concept(Concept(
    id="geo.triangles.pythagorean",
    name="Pythagorean Theorem and Applications",
    course_id="geometry",
    unit_id="geo_triangles",
    topic_id="geo_triangle_properties",
    kind="skill",
    description="Pythagorean theorem; 45-45-90 and 30-60-90 triangles",
    prerequisites=["geo.triangles.triangle_types"],
    difficulty_min=2,
    difficulty_max=3,
    examples_latex=["$a^2 + b^2 = c^2$"],
    tags=["pythagorean"]
))

register_concept(Concept(
    id="geo.triangles.altitude_median",
    name="Altitude, Median, and Other Segments",
    course_id="geometry",
    unit_id="geo_triangles",
    topic_id="geo_triangle_properties",
    kind="definition",
    description="Properties of special segments in triangles",
    prerequisites=["geo.triangles.congruence_postulates"],
    difficulty_min=2,
    difficulty_max=3,
    examples_latex=["Median divides triangle into equal areas"],
    tags=["triangles"]
))

# Polygons and Quadrilaterals
register_concept(Concept(
    id="geo.polygons.quad_types",
    name="Quadrilateral Types and Properties",
    course_id="geometry",
    unit_id="geo_polygons",
    topic_id="geo_quad_properties",
    kind="definition",
    description="Parallelograms, rectangles, rhombi, squares, trapezoids",
    prerequisites=["geo.foundations.parallel_lines"],
    difficulty_min=2,
    difficulty_max=3,
    examples_latex=["Opposite sides parallel \\Rightarrow parallelogram"],
    tags=["quadrilaterals"]
))

register_concept(Concept(
    id="geo.polygons.area_perimeter",
    name="Area and Perimeter of Polygons",
    course_id="geometry",
    unit_id="geo_polygons",
    topic_id="geo_area_perimeter",
    kind="skill",
    description="Calculating area and perimeter of various polygons",
    prerequisites=["geo.triangles.pythagorean", "geo.polygons.quad_types"],
    difficulty_min=2,
    difficulty_max=4,
    examples_latex=["$A = \\frac{1}{2}bh$", "$A = bh$"],
    tags=["area", "measurement"]
))

# Circles
register_concept(Concept(
    id="geo.circles.definitions",
    name="Circle Definitions and Properties",
    course_id="geometry",
    unit_id="geo_circles",
    topic_id="geo_circle_basics",
    kind="definition",
    description="Radius, diameter, circumference, π",
    prerequisites=["geo.foundations.points_lines_angles"],
    difficulty_min=2,
    difficulty_max=3,
    examples_latex=["$C = 2\\pi r$", "$A = \\pi r^2$"],
    tags=["circles"]
))

register_concept(Concept(
    id="geo.circles.inscribed_angles",
    name="Inscribed Angles and Arcs",
    course_id="geometry",
    unit_id="geo_circles",
    topic_id="geo_circle_angles",
    kind="definition",
    description="Angle relationships in circles",
    prerequisites=["geo.circles.definitions"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["Inscribed angle = \\frac{1}{2} \\text{central angle}"],
    tags=["circles", "angles"]
))

register_concept(Concept(
    id="geo.circles.chord_properties",
    name="Chord Properties and Tangents",
    course_id="geometry",
    unit_id="geo_circles",
    topic_id="geo_arc_chord",
    kind="definition",
    description="Perpendicular bisector of chord; tangent properties",
    prerequisites=["geo.circles.inscribed_angles"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["Tangent \\perp radius"],
    tags=["circles"]
))

# Coordinate Geometry
register_concept(Concept(
    id="geo.coordinate.distance_midpoint",
    name="Distance and Midpoint Formulas",
    course_id="geometry",
    unit_id="geo_coordinate",
    topic_id="geo_coord_distance",
    kind="skill",
    description="Using distance and midpoint formulas",
    prerequisites=["geo.triangles.pythagorean", "alg1.linear_func.slope_from_two_points"],
    difficulty_min=2,
    difficulty_max=3,
    examples_latex=["$d = \\sqrt{(x_2-x_1)^2 + (y_2-y_1)^2}$"],
    tags=["coordinate"]
))

register_concept(Concept(
    id="geo.coordinate.equations_circles",
    name="Equations of Lines and Circles",
    course_id="geometry",
    unit_id="geo_coordinate",
    topic_id="geo_coord_slope",
    kind="skill",
    description="Writing equations on the coordinate plane",
    prerequisites=["geo.coordinate.distance_midpoint", "alg1.linear_func.slope_intercept"],
    difficulty_min=2,
    difficulty_max=4,
    examples_latex=["$(x-h)^2 + (y-k)^2 = r^2$"],
    tags=["coordinate"]
))

# Transformations
register_concept(Concept(
    id="geo.transformations.translations",
    name="Translations",
    course_id="geometry",
    unit_id="geo_transformations",
    topic_id="geo_translations",
    kind="definition",
    description="Rigid transformations; translations preserve distance",
    prerequisites=["geo.coordinate.distance_midpoint"],
    difficulty_min=2,
    difficulty_max=3,
    examples_latex=["(x,y) \\rightarrow (x+h, y+k)"],
    tags=["transformations"]
))

register_concept(Concept(
    id="geo.transformations.reflections",
    name="Reflections",
    course_id="geometry",
    unit_id="geo_transformations",
    topic_id="geo_reflections",
    kind="definition",
    description="Reflection across lines; symmetry",
    prerequisites=["geo.transformations.translations"],
    difficulty_min=2,
    difficulty_max=3,
    examples_latex=["Reflect across y-axis: (x,y) \\rightarrow (-x,y)"],
    tags=["transformations"]
))

register_concept(Concept(
    id="geo.transformations.rotations",
    name="Rotations and Similarity Transformations",
    course_id="geometry",
    unit_id="geo_transformations",
    topic_id="geo_rotations",
    kind="definition",
    description="Rotations; dilations and scaling",
    prerequisites=["geo.transformations.reflections"],
    difficulty_min=3,
    difficulty_max=4,
    examples_latex=["Rotate 90° about origin"],
    tags=["transformations"]
))
