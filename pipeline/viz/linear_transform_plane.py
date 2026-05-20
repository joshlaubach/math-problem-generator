"""
viz/linear_transform_plane.py

Applies a 2x2 matrix transformation to the coordinate plane (NumberPlane).
Grid lines deform, showing geometric effect of the transformation.
Used for: conic rotation, linear algebra matrix effects.
"""
from __future__ import annotations
import numpy as np
from manim import *
from pipeline.viz.helpers import BRAND_CARAMEL


class LinearTransformPlaneScene(Scene):
    """Applies a rotation matrix to the coordinate plane."""

    MATRIX      = [[0, -1], [1, 0]]   # 90° rotation by default
    TITLE       = "Linear Transformation"
    MATRIX_LABEL = r"\begin{pmatrix}0 & -1\\1 & 0\end{pmatrix}"
    ANGLE_DEG   = 90

    def construct(self):
        title = Text(self.TITLE, font_size=32)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait(1.0)

        plane = NumberPlane(
            x_range=[-6, 6, 1], y_range=[-4, 4, 1],
            background_line_style={"stroke_color": BLUE_E, "stroke_width": 1, "stroke_opacity": 0.6},
            axis_config={"stroke_width": 2},
        )
        self.play(Create(plane), run_time=1.5)
        self.wait(0.8)

        # Matrix display
        mat = Matrix(self.MATRIX, element_to_mobject_config={"font_size": 28})
        mat.to_edge(RIGHT, buff=0.5).to_edge(UP, buff=0.8)
        mat_label = Text("T =", font_size=26).next_to(mat, LEFT, buff=0.2)
        self.play(Write(mat_label), Write(mat))
        self.wait(0.8)

        # Apply transformation
        matrix_3x3 = np.array([
            [self.MATRIX[0][0], self.MATRIX[0][1], 0],
            [self.MATRIX[1][0], self.MATRIX[1][1], 0],
            [0,                 0,                 1],
        ], dtype=float)

        self.play(
            plane.animate.apply_matrix(matrix_3x3),
            run_time=2.5,
            rate_func=smooth,
        )
        self.wait(1.5)

        note = Text(f"Rotated {self.ANGLE_DEG}°", font_size=26, color=YELLOW)
        note.to_edge(LEFT, buff=0.5).to_edge(DOWN, buff=0.6)
        self.play(Write(note))
        self.wait(1.5)

        self.play(FadeOut(*self.mobjects))
        self.wait(0.5)


class ConicRotationScene(Scene):
    """Shows a conic section being rotated via matrix transformation."""

    CONIC_TYPE  = "ellipse"   # "ellipse" | "parabola" | "hyperbola"
    ANGLE_DEG   = 45

    def construct(self):
        import math
        theta = math.radians(self.ANGLE_DEG)
        title = Text(f"Rotating the {self.CONIC_TYPE.title()}", font_size=30)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait(1.0)

        axes = Axes(
            x_range=[-5, 5, 1], y_range=[-4, 4, 1],
            x_length=9, y_length=7,
            axis_config={"stroke_width": 1.5, "color": GRAY},
            tips=False,
        ).move_to(DOWN * 0.2)
        self.play(Create(axes))

        # Original conic
        if self.CONIC_TYPE == "ellipse":
            conic = axes.plot_parametric_curve(
                lambda t: np.array([3 * np.cos(t), 1.5 * np.sin(t), 0]),
                t_range=[0, 2*PI], color=BRAND_CARAMEL, stroke_width=3,
            )
        elif self.CONIC_TYPE == "parabola":
            conic = axes.plot(lambda x: x**2 / 3 - 2,
                              x_range=[-3, 3], color=BRAND_CARAMEL, stroke_width=3)
        else:  # hyperbola
            c1 = axes.plot_parametric_curve(
                lambda t: np.array([2 * np.cosh(t), 1.5 * np.sinh(t), 0]),
                t_range=[-1.5, 1.5], color=BRAND_CARAMEL, stroke_width=3,
            )
            c2 = axes.plot_parametric_curve(
                lambda t: np.array([-2 * np.cosh(t), 1.5 * np.sinh(t), 0]),
                t_range=[-1.5, 1.5], color=BRAND_CARAMEL, stroke_width=3,
            )
            conic = VGroup(c1, c2)

        original_label = Text("Original", font_size=22, color=BRAND_CARAMEL)
        original_label.to_edge(LEFT, buff=0.3).shift(UP * 0.5)
        self.play(Create(conic), Write(original_label))
        self.wait(1.0)

        # Rotation matrix
        R = np.array([
            [math.cos(theta), -math.sin(theta), 0],
            [math.sin(theta),  math.cos(theta), 0],
            [0,                0,               1],
        ])
        rot_mat_display = MathTex(
            rf"R = \begin{{pmatrix}}\cos{self.ANGLE_DEG}° & -\sin{self.ANGLE_DEG}°\\"
            rf"\sin{self.ANGLE_DEG}° & \cos{self.ANGLE_DEG}°\end{{pmatrix}}",
            font_size=22,
        )
        rot_mat_display.to_edge(RIGHT, buff=0.3).shift(UP * 1.5)
        self.play(Write(rot_mat_display))
        self.wait(0.8)

        # Rotate
        rotated = conic.copy().set_color(YELLOW).set_opacity(0.8)
        self.play(
            rotated.animate.apply_matrix(R[:2, :2]),
            run_time=2.0, rate_func=smooth,
        )
        rotated_label = Text(f"Rotated {self.ANGLE_DEG}°", font_size=22, color=YELLOW)
        rotated_label.to_edge(RIGHT, buff=0.3).shift(DOWN * 1.0)
        self.play(Write(rotated_label))
        self.wait(1.5)

        self.play(FadeOut(*self.mobjects))
        self.wait(0.5)


if __name__ == "__main__":
    pass
