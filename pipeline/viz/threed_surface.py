"""
viz/threed_surface.py — 3D surface plot with color gradient.
"""
from __future__ import annotations
import numpy as np
from manim import *
from pipeline.viz.helpers import BRAND_CARAMEL, BRAND_GREEN


class ThreeDSurfaceScene(ThreeDScene):
    TITLE      = "3D Surface"
    FUNC_TEX   = r"z = \sin(x)\cos(y)"
    U_RANGE    = [-3.0, 3.0]
    V_RANGE    = [-3.0, 3.0]
    RESOLUTION = (30, 30)
    ROTATE_SCENE = True

    @staticmethod
    def _default_func(u, v):
        return np.array([u, v, np.sin(u) * np.cos(v)])

    FUNC = None   # set to a callable (u,v)->np.array([x,y,z]) or leave None for default

    def construct(self):
        self.set_camera_orientation(phi=60 * DEGREES, theta=-60 * DEGREES)

        axes = ThreeDAxes(
            x_range=[self.U_RANGE[0], self.U_RANGE[1], 1],
            y_range=[self.V_RANGE[0], self.V_RANGE[1], 1],
            z_range=[-1.5, 1.5, 0.5],
            x_length=7, y_length=7, z_length=5,
            axis_config={"stroke_width": 1.5, "include_tip": True, "tip_length": 0.18},
        )
        self.play(Create(axes))
        self.wait(0.5)

        func = self.FUNC or self._default_func

        surface = Surface(
            func,
            u_range=self.U_RANGE,
            v_range=self.V_RANGE,
            resolution=self.RESOLUTION,
            fill_opacity=0.8,
            stroke_width=0,
            checkerboard_colors=[BRAND_CARAMEL, BRAND_GREEN],
        )
        self.play(Create(surface), run_time=1.5)

        # Function label (fixed in frame)
        if self.FUNC_TEX:
            lbl = MathTex(self.FUNC_TEX, font_size=28, color=YELLOW)
            self.add_fixed_in_frame_mobjects(lbl)
            lbl.to_corner(UL, buff=0.4)
            self.play(Write(lbl))

        self.wait(0.5)

        if self.ROTATE_SCENE:
            self.begin_ambient_camera_rotation(rate=0.3)
            self.wait(5.0)
            self.stop_ambient_camera_rotation()

        self.wait(0.5)


if __name__ == "__main__":
    pass
