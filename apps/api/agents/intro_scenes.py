"""
Pre-authored intro diagrams for the whiteboard.

Each value is a GeometryElement[] (see WhiteboardPlot.tsx for the type definition).
Emitted once per topic per session at the first Demonstrate entry (Phase 1.7).

Coordinate conventions: standard math (x right, y up). The renderer auto-scales.
"""

INTRO_SCENES: dict[str, list[dict]] = {

    # ── Pre-Algebra ───────────────────────────────────────────────────────────

    "pa_002": [  # The Number Line
        {"kind": "segment", "x1": -4, "y1": 0, "x2": 4, "y2": 0},
        {"kind": "point", "x": -3, "y": 0, "label": "−3"},
        {"kind": "point", "x": -2, "y": 0, "label": "−2"},
        {"kind": "point", "x": -1, "y": 0, "label": "−1"},
        {"kind": "point", "x":  0, "y": 0, "label": "0"},
        {"kind": "point", "x":  1, "y": 0, "label": "1"},
        {"kind": "point", "x":  2, "y": 0, "label": "2"},
        {"kind": "point", "x":  3, "y": 0, "label": "3"},
        {"kind": "vector", "x": 3.5, "y": 0, "dx": 0.5, "dy": 0},
        {"kind": "vector", "x": -3.5, "y": 0, "dx": -0.5, "dy": 0},
    ],

    "pa_031": [  # Classifying Angles
        # Acute ~45°
        {"kind": "angle", "vertex": [-5, 0], "ray1": [-4, 0], "ray2": [-4.3, 1], "label": "acute < 90°"},
        # Right 90°
        {"kind": "angle", "vertex": [0, 0], "ray1": [1, 0], "ray2": [0, 1], "label": "right = 90°"},
        # Obtuse ~135°
        {"kind": "angle", "vertex": [5, 0], "ray1": [6, 0], "ray2": [4.3, 1], "label": "obtuse > 90°"},
    ],

    "pa_032": [  # Angle Relationships — vertical angles via two intersecting lines
        {"kind": "segment", "x1": -3, "y1": -2, "x2": 3, "y2": 2},
        {"kind": "segment", "x1": -3, "y1": 2, "x2": 3, "y2": -2},
        {"kind": "point", "x": 0, "y": 0},
        {"kind": "angle", "vertex": [0, 0], "ray1": [2, 1.3], "ray2": [2, -1.3], "label": "vertical"},
        {"kind": "angle", "vertex": [0, 0], "ray1": [-2, -1.3], "ray2": [-2, 1.3], "label": "vertical"},
    ],

    "pa_033": [  # Classifying Triangles
        # Equilateral (left)
        {"kind": "polygon", "points": [[-5, 0], [-3.5, 2.6], [-2, 0]], "label": "equilateral"},
        # Right (right)
        {"kind": "polygon", "points": [[2, 0], [2, 3], [5, 0]], "label": "right"},
        {"kind": "angle", "vertex": [2, 0], "ray1": [2, 1], "ray2": [3, 0], "label": "90°"},
    ],

    "pa_035": [  # Perimeter and Area of Basic Shapes — labeled rectangle
        {"kind": "polygon", "points": [[0, 0], [4, 0], [4, 2], [0, 2]]},
        {"kind": "segment", "x1": 0, "y1": 0, "x2": 4, "y2": 0, "label": "length"},
        {"kind": "segment", "x1": 4, "y1": 0, "x2": 4, "y2": 2, "label": "width"},
        {"kind": "point", "x": 2, "y": 1, "label": "A = l × w"},
    ],

    "pa_036": [  # Introduction to the Coordinate Plane
        # Axes
        {"kind": "segment", "x1": -4, "y1": 0, "x2": 4, "y2": 0, "label": "x"},
        {"kind": "segment", "x1": 0, "y1": -3, "x2": 0, "y2": 3, "label": "y"},
        # Points in each quadrant
        {"kind": "point", "x": 2, "y": 2, "label": "(2,2) QI"},
        {"kind": "point", "x": -2, "y": 2, "label": "(−2,2) QII"},
        {"kind": "point", "x": -2, "y": -2, "label": "(−2,−2) QIII"},
        {"kind": "point", "x": 2, "y": -2, "label": "(2,−2) QIV"},
        {"kind": "point", "x": 0, "y": 0, "label": "origin"},
    ],

    # ── Algebra I ─────────────────────────────────────────────────────────────

    "a1_014": [  # The Coordinate Plane and Plotting Points
        {"kind": "segment", "x1": -4, "y1": 0, "x2": 4, "y2": 0, "label": "x-axis"},
        {"kind": "segment", "x1": 0, "y1": -3, "x2": 0, "y2": 3, "label": "y-axis"},
        {"kind": "point", "x": 3, "y": 2, "label": "(3, 2)"},
        {"kind": "point", "x": -2, "y": 1, "label": "(−2, 1)"},
        {"kind": "segment", "x1": 0, "y1": 0, "x2": 3, "y2": 0},
        {"kind": "segment", "x1": 3, "y1": 0, "x2": 3, "y2": 2},
    ],

    "a1_018": [  # Slope and Rate of Change
        # Axes
        {"kind": "segment", "x1": -1, "y1": 0, "x2": 5, "y2": 0, "label": "x"},
        {"kind": "segment", "x1": 0, "y1": -1, "x2": 0, "y2": 5, "label": "y"},
        # Two points on the line
        {"kind": "point", "x": 0, "y": 0, "label": "A"},
        {"kind": "point", "x": 4, "y": 3, "label": "B"},
        # The line
        {"kind": "segment", "x1": 0, "y1": 0, "x2": 4, "y2": 3},
        # Rise and run legs
        {"kind": "segment", "x1": 4, "y1": 0, "x2": 4, "y2": 3, "label": "rise = 3"},
        {"kind": "segment", "x1": 0, "y1": 0, "x2": 4, "y2": 0, "label": "run = 4"},
        {"kind": "point", "x": 2.5, "y": 1.8, "label": "slope = 3/4"},
    ],

    "a1_025": [  # Parallel and Perpendicular Lines
        # Two parallel lines (same slope)
        {"kind": "segment", "x1": -3, "y1": -0.5, "x2": 3, "y2": 2.5, "label": "parallel"},
        {"kind": "segment", "x1": -3, "y1": -2.5, "x2": 3, "y2": 0.5, "label": "parallel"},
        # Perpendicular pair (right side)
        {"kind": "segment", "x1": 5, "y1": -2, "x2": 5, "y2": 2, "label": ""},
        {"kind": "segment", "x1": 3, "y1": 0, "x2": 7, "y2": 0, "label": ""},
        {"kind": "angle", "vertex": [5, 0], "ray1": [6, 0], "ray2": [5, 1], "label": "⊥"},
    ],

    "a1_049": [  # Introduction to Parabolas — axis of symmetry + vertex
        # Axis of symmetry
        {"kind": "segment", "x1": 2, "y1": -1, "x2": 2, "y2": 5, "label": "axis x = 2"},
        # Vertex
        {"kind": "point", "x": 2, "y": 1, "label": "vertex"},
        # Parabola arms (approximated with two line segments each side)
        {"kind": "segment", "x1": 0, "y1": 5, "x2": 2, "y2": 1},
        {"kind": "segment", "x1": 2, "y1": 1, "x2": 4, "y2": 5},
        # Symmetric points
        {"kind": "point", "x": 0, "y": 5, "label": ""},
        {"kind": "point", "x": 4, "y": 5, "label": ""},
        {"kind": "segment", "x1": 0, "y1": 5, "x2": 4, "y2": 5, "label": "symmetric"},
    ],

    "a1_066": [  # The Pythagorean Theorem
        # Right triangle with sides 3, 4, 5
        {"kind": "segment", "x1": 0, "y1": 0, "x2": 3, "y2": 0, "label": "a"},
        {"kind": "segment", "x1": 3, "y1": 0, "x2": 3, "y2": 4, "label": "b"},
        {"kind": "segment", "x1": 0, "y1": 0, "x2": 3, "y2": 4, "label": "c"},
        # Right angle at (3,0)
        {"kind": "angle", "vertex": [3, 0], "ray1": [2, 0], "ray2": [3, 1], "label": "90°"},
        {"kind": "point", "x": 1.8, "y": 2.5, "label": "a²+b²=c²"},
    ],

    "a1_067": [  # Distance and Midpoint Formulas
        {"kind": "point", "x": 0, "y": 0, "label": "A(0,0)"},
        {"kind": "point", "x": 4, "y": 3, "label": "B(4,3)"},
        {"kind": "segment", "x1": 0, "y1": 0, "x2": 4, "y2": 3, "label": "d"},
        # Midpoint
        {"kind": "point", "x": 2, "y": 1.5, "label": "M(2, 1.5)"},
        # Reference legs
        {"kind": "segment", "x1": 0, "y1": 0, "x2": 4, "y2": 0},
        {"kind": "segment", "x1": 4, "y1": 0, "x2": 4, "y2": 3},
    ],

    # ── Geometry ──────────────────────────────────────────────────────────────

    "geo_005": [  # Classifying Angles and Angle Pairs — complementary + supplementary
        # Complementary (90° total, left)
        {"kind": "angle", "vertex": [-4, 0], "ray1": [-3, 0], "ray2": [-4, 1], "label": "90°"},
        {"kind": "angle", "vertex": [-4, 0], "ray1": [-3.3, 0.7], "ray2": [-4, 1], "label": ""},
        {"kind": "segment", "x1": -4, "y1": 0, "x2": -3, "y2": 0},
        {"kind": "segment", "x1": -4, "y1": 0, "x2": -4, "y2": 1},
        {"kind": "point", "x": -3.3, "y": -0.4, "label": "complementary"},
        # Supplementary (180° total, right)
        {"kind": "segment", "x1": 2, "y1": 0, "x2": 6, "y2": 0},
        {"kind": "segment", "x1": 4, "y1": 0, "x2": 4, "y2": 2},
        {"kind": "angle", "vertex": [4, 0], "ray1": [4, 1], "ray2": [3, 0], "label": ""},
        {"kind": "angle", "vertex": [4, 0], "ray1": [5, 0], "ray2": [4, 1], "label": ""},
        {"kind": "point", "x": 4, "y": -0.4, "label": "supplementary = 180°"},
    ],

    "geo_016": [  # Parallel Lines and Angle Pairs
        # Two parallel lines cut by a transversal
        {"kind": "segment", "x1": -3, "y1": 2, "x2": 3, "y2": 2, "label": "ℓ₁"},
        {"kind": "segment", "x1": -3, "y1": -1, "x2": 3, "y2": -1, "label": "ℓ₂"},
        {"kind": "segment", "x1": -1, "y1": -2.5, "x2": 1, "y2": 3.5, "label": "t"},
        # Alternate interior angles
        {"kind": "point", "x": -0.3, "y": 1.3, "label": "↔ alt. interior"},
        {"kind": "point", "x": 0.3, "y": -0.2, "label": "↔ alt. interior"},
    ],

    "geo_028": [  # Triangle Angle Sum Theorem
        {"kind": "polygon", "points": [[0, 0], [5, 0], [2, 3.5]]},
        {"kind": "angle", "vertex": [0, 0], "ray1": [1, 0], "ray2": [0.4, 0.7], "label": "α"},
        {"kind": "angle", "vertex": [5, 0], "ray1": [4, 0], "ray2": [4.6, 0.7], "label": "β"},
        {"kind": "angle", "vertex": [2, 3.5], "ray1": [1.5, 2.7], "ray2": [2.5, 2.7], "label": "γ"},
        {"kind": "point", "x": 2.5, "y": 1.5, "label": "α+β+γ = 180°"},
    ],

    "geo_034": [  # Isosceles and Equilateral Triangles
        # Isosceles (left)
        {"kind": "segment", "x1": -5, "y1": 0, "x2": -3, "y2": 0},
        {"kind": "segment", "x1": -5, "y1": 0, "x2": -4, "y2": 3, "label": "equal"},
        {"kind": "segment", "x1": -3, "y1": 0, "x2": -4, "y2": 3, "label": "equal"},
        {"kind": "point", "x": -4, "y": -0.5, "label": "isosceles"},
        # Equilateral (right)
        {"kind": "polygon", "points": [[2, 0], [5, 0], [3.5, 2.6]], "label": "equilateral"},
        {"kind": "point", "x": 3.5, "y": -0.5, "label": "all sides equal"},
    ],

    "geo_048": [  # Similar Polygons — two similar triangles
        # Smaller triangle
        {"kind": "polygon", "points": [[0, 0], [2, 0], [1, 1.5]], "label": "△ABC"},
        # Larger similar triangle (scaled by 1.5)
        {"kind": "polygon", "points": [[3.5, 0], [6.5, 0], [5, 2.25]], "label": "△DEF"},
        {"kind": "point", "x": 1, "y": -0.5, "label": "scale 1"},
        {"kind": "point", "x": 5, "y": -0.5, "label": "scale 1.5"},
        {"kind": "point", "x": 3, "y": 1, "label": "∼ (similar)"},
    ],

    "geo_054": [  # Special Right Triangles — 45-45-90
        # 45-45-90 (left)
        {"kind": "segment", "x1": -5, "y1": 0, "x2": -3, "y2": 0, "label": "1"},
        {"kind": "segment", "x1": -3, "y1": 0, "x2": -3, "y2": 2, "label": "1"},
        {"kind": "segment", "x1": -5, "y1": 0, "x2": -3, "y2": 2, "label": "√2"},
        {"kind": "angle", "vertex": [-3, 0], "ray1": [-4, 0], "ray2": [-3, 1], "label": "90°"},
        {"kind": "angle", "vertex": [-5, 0], "ray1": [-4, 0], "ray2": [-4, 1], "label": "45°"},
        {"kind": "angle", "vertex": [-3, 2], "ray1": [-4, 1.5], "ray2": [-3, 1], "label": "45°"},
        # 30-60-90 (right)
        {"kind": "segment", "x1": 1, "y1": 0, "x2": 4, "y2": 0, "label": "1"},
        {"kind": "segment", "x1": 4, "y1": 0, "x2": 4, "y2": 3.46, "label": "√3"},
        {"kind": "segment", "x1": 1, "y1": 0, "x2": 4, "y2": 3.46, "label": "2"},
        {"kind": "angle", "vertex": [4, 0], "ray1": [3, 0], "ray2": [4, 1], "label": "90°"},
        {"kind": "angle", "vertex": [1, 0], "ray1": [2, 0], "ray2": [1.5, 1], "label": "30°"},
        {"kind": "angle", "vertex": [4, 3.46], "ray1": [3.5, 2.5], "ray2": [4, 2.5], "label": "60°"},
    ],

    "geo_055": [  # Introduction to Trigonometric Ratios
        # Right triangle with opposite, adjacent, hypotenuse
        {"kind": "segment", "x1": 0, "y1": 0, "x2": 4, "y2": 0, "label": "adjacent"},
        {"kind": "segment", "x1": 4, "y1": 0, "x2": 4, "y2": 3, "label": "opposite"},
        {"kind": "segment", "x1": 0, "y1": 0, "x2": 4, "y2": 3, "label": "hypotenuse"},
        {"kind": "angle", "vertex": [0, 0], "ray1": [1, 0], "ray2": [0.8, 0.6], "label": "θ"},
        {"kind": "angle", "vertex": [4, 0], "ray1": [3, 0], "ray2": [4, 1], "label": "90°"},
        {"kind": "point", "x": 1.5, "y": -0.5, "label": "sin θ = opp/hyp"},
    ],

    "geo_069": [  # Area and Circumference of Circles
        {"kind": "circle", "cx": 0, "cy": 0, "r": 3},
        {"kind": "segment", "x1": 0, "y1": 0, "x2": 3, "y2": 0, "label": "r"},
        {"kind": "point", "x": 0, "y": 0, "label": "center"},
        {"kind": "point", "x": 0, "y": -3.8, "label": "C = 2πr"},
        {"kind": "point", "x": 0, "y": -4.6, "label": "A = πr²"},
    ],

    "geo_060": [  # Lines and Segments in Circles
        {"kind": "circle", "cx": 0, "cy": 0, "r": 3},
        # Diameter
        {"kind": "segment", "x1": -3, "y1": 0, "x2": 3, "y2": 0, "label": "diameter"},
        # Chord (not through center)
        {"kind": "segment", "x1": -2, "y1": 2.23, "x2": 2, "y2": 2.23, "label": "chord"},
        # Radius
        {"kind": "segment", "x1": 0, "y1": 0, "x2": 0, "y2": 3, "label": "radius"},
        {"kind": "point", "x": 0, "y": 0, "label": "O"},
    ],
}
