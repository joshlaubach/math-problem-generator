"""
viz/threed_vectors.py — 3D vector addition / cross product visualization.
"""
from __future__ import annotations
import numpy as np
from manim import *
from pipeline.viz.helpers import BRAND_CARAMEL, BRAND_GREEN


class ThreeDVectorsScene(ThreeDScene):
    TITLE     = "Vectors in 3D"
    VECTOR_A  = [2, 1, 0]
    VECTOR_B  = [0, 2, 2]
    MODE      = "add"    # "add" | "cross"

    def construct(self):
        self.set_camera_orientation(phi=65 * DEGREES, theta=-50 * DEGREES)

        axes = ThreeDAxes(
            x_range=[-1, 5, 1], y_range=[-1, 5, 1], z_range=[-1, 4, 1],
            x_length=6, y_length=6, z_length=5,
            axis_config={"stroke_width": 2, "include_tip": True, "tip_length": 0.18},
        )
        x_lbl = axes.get_x_axis_label("x")
        y_lbl = axes.get_y_axis_label("y")
        z_lbl = axes.get_z_axis_label("z")
        self.play(Create(axes), Write(x_lbl), Write(y_lbl), Write(z_lbl))
        self.wait(0.8)

        origin = axes.c2p(0, 0, 0)
        a_end  = axes.c2p(*self.VECTOR_A)
        b_end  = axes.c2p(*self.VECTOR_B)

        vec_a = Arrow3D(start=origin, end=a_end,
                        color=BRAND_CARAMEL, thickness=0.03, height=0.22)
        vec_b = Arrow3D(start=origin, end=b_end,
                        color=BRAND_GREEN,   thickness=0.03, height=0.22)

        a_lbl = Text("a", font_size=26, color=BRAND_CARAMEL)
        b_lbl = Text("b", font_size=26, color=BRAND_GREEN)
        a_lbl.move_to(np.array(axes.c2p(*[v * 0.5 for v in self.VECTOR_A])) + OUT * 0.3)
        b_lbl.move_to(np.array(axes.c2p(*[v * 0.5 for v in self.VECTOR_B])) + OUT * 0.3)
        self.add_fixed_orientation_mobjects(a_lbl, b_lbl)

        self.play(Create(vec_a), Create(vec_b))
        self.play(Write(a_lbl), Write(b_lbl))
        self.wait(0.8)

        if self.MODE == "add":
            # Tip-to-tail: draw b starting from tip of a
            ax, ay, az = self.VECTOR_A
            bx, by, bz = self.VECTOR_B
            sum_vec_coords = [ax + bx, ay + by, az + bz]
            b_shifted_end = axes.c2p(*sum_vec_coords)

            vec_b2 = Arrow3D(start=a_end, end=b_shifted_end,
                             color=BRAND_GREEN, thickness=0.02, height=0.18)
            self.play(Create(vec_b2))

            vec_r = Arrow3D(start=origin, end=b_shifted_end,
                            color=YELLOW, thickness=0.04, height=0.25)
            r_lbl = Text("a+b", font_size=24, color=YELLOW)
            r_lbl.move_to(np.array(axes.c2p(*[v * 0.5 for v in sum_vec_coords])) + OUT * 0.3)
            self.add_fixed_orientation_mobjects(r_lbl)
            self.play(Create(vec_r), Write(r_lbl))

        elif self.MODE == "cross":
            a = np.array(self.VECTOR_A, dtype=float)
            b = np.array(self.VECTOR_B, dtype=float)
            cross = np.cross(a, b)
            cross_end = axes.c2p(*cross.tolist())
            vec_c = Arrow3D(start=origin, end=cross_end,
                            color=YELLOW, thickness=0.04, height=0.25)
            c_lbl = Text("a×b", font_size=24, color=YELLOW)
            c_lbl.move_to(np.array(axes.c2p(*cross.tolist())) + OUT * 0.3)
            self.add_fixed_orientation_mobjects(c_lbl)
            self.play(Create(vec_c), Write(c_lbl))

        self.begin_ambient_camera_rotation(rate=0.22)
        self.wait(3.5)
        self.stop_ambient_camera_rotation()
        self.wait(0.5)


if __name__ == "__main__":
    pass
