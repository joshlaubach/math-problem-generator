"""
viz/threed_axes.py — 3D coordinate axes with labeled point and optional vector.
"""
from __future__ import annotations
import numpy as np
from manim import *
from pipeline.viz.helpers import BRAND_CARAMEL, BRAND_GREEN


class ThreeDAxesScene(ThreeDScene):
    TITLE        = "3D Coordinate System"
    POINT        = [2, 3, 2]       # (x, y, z) to plot
    POINT_LABEL  = "P(2, 3, 2)"
    SHOW_VECTOR  = True            # draw vector from origin to POINT
    ROTATE_SCENE = True            # orbit the camera

    def construct(self):
        # Camera angle
        self.set_camera_orientation(phi=70 * DEGREES, theta=-60 * DEGREES)

        axes = ThreeDAxes(
            x_range=[-1, 5, 1], y_range=[-1, 5, 1], z_range=[-1, 4, 1],
            x_length=7, y_length=7, z_length=5,
            axis_config={"stroke_width": 2, "include_tip": True, "tip_length": 0.2},
        )

        # Axis labels
        x_lbl = axes.get_x_axis_label("x", direction=RIGHT)
        y_lbl = axes.get_y_axis_label("y", direction=UP)
        z_lbl = axes.get_z_axis_label("z", direction=OUT)

        self.play(Create(axes), Write(x_lbl), Write(y_lbl), Write(z_lbl))
        self.wait(1.0)

        # Dashed projection lines to axes
        px, py, pz = self.POINT
        origin = axes.c2p(0, 0, 0)
        point  = axes.c2p(px, py, pz)
        proj_x = axes.c2p(px, 0,  0)
        proj_y = axes.c2p(0,  py, 0)
        proj_z = axes.c2p(0,  0,  pz)
        proj_xy = axes.c2p(px, py, 0)

        projections = VGroup(
            DashedLine(point,   proj_xy, stroke_width=1.5, color=GRAY_A, dash_length=0.1),
            DashedLine(proj_xy, proj_x,  stroke_width=1.5, color=GRAY_A, dash_length=0.1),
            DashedLine(proj_xy, proj_y,  stroke_width=1.5, color=GRAY_A, dash_length=0.1),
        )
        self.play(Create(projections))

        # The point itself
        dot = Dot3D(point, color=BRAND_CARAMEL, radius=0.1)
        self.play(Create(dot))

        # Label (always face camera in 3D)
        lbl = Text(self.POINT_LABEL, font_size=24, color=BRAND_CARAMEL)
        lbl.next_to(dot, OUT + RIGHT, buff=0.15)
        self.add_fixed_orientation_mobjects(lbl)
        self.play(Write(lbl))
        self.wait(0.5)

        # Vector
        if self.SHOW_VECTOR:
            vec = Arrow3D(
                start=origin, end=point,
                color=BRAND_GREEN, thickness=0.03, height=0.25,
            )
            self.play(Create(vec))
            self.wait(0.5)

        # Orbit
        if self.ROTATE_SCENE:
            self.begin_ambient_camera_rotation(rate=0.25)
            self.wait(4.0)
            self.stop_ambient_camera_rotation()

        self.wait(0.5)


if __name__ == "__main__":
    pass
