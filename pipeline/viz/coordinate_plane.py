"""
viz/coordinate_plane.py — function graphing with Axes.
"""
from __future__ import annotations
import numpy as np
from manim import *
from pipeline.viz.helpers import BRAND_CARAMEL, BRAND_GREEN


class CoordinatePlaneScene(Scene):
    TITLE     = "Graphing a Function"
    FUNC_LATEX = r"f(x) = x^2 - 2x - 3"
    FUNC       = staticmethod(lambda x: x**2 - 2*x - 3)
    X_RANGE    = [-2, 4, 1]
    Y_RANGE    = [-5, 5, 1]
    HIGHLIGHT_ROOTS: list[float] = [-1, 3]
    HIGHLIGHT_VERTEX: tuple[float, float] | None = (1, -4)

    def construct(self):
        title = Text(self.TITLE, font_size=32)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait(1.0)

        axes = Axes(
            x_range=self.X_RANGE, y_range=self.Y_RANGE,
            x_length=9, y_length=5.8,
            axis_config={"stroke_width": 2, "include_tip": True, "tip_length": 0.15},
            tips=False,
        ).move_to(DOWN * 0.3)
        x_label = axes.get_x_axis_label("x")
        y_label = axes.get_y_axis_label("y")
        self.play(Create(axes), Write(x_label), Write(y_label))
        self.wait(0.5)

        graph = axes.plot(self.FUNC, color=BRAND_CARAMEL, stroke_width=3)
        graph_label = MathTex(self.FUNC_LATEX, font_size=26, color=BRAND_CARAMEL)
        graph_label.to_edge(RIGHT, buff=0.4).shift(UP * 2.0)
        self.play(Create(graph), Write(graph_label))
        self.wait(1.0)

        # Highlight roots
        for rx in self.HIGHLIGHT_ROOTS:
            dot = Dot(axes.c2p(rx, 0), color=YELLOW, radius=0.1)
            lbl = MathTex(f"x={rx}", font_size=22, color=YELLOW)
            lbl.next_to(dot, UP, buff=0.15)
            self.play(FadeIn(dot), Write(lbl))
        self.wait(0.8)

        # Highlight vertex
        if self.HIGHLIGHT_VERTEX:
            vx, vy = self.HIGHLIGHT_VERTEX
            v_dot = Dot(axes.c2p(vx, vy), color=BRAND_GREEN, radius=0.1)
            v_lbl = MathTex(f"({vx},{vy})", font_size=22, color=BRAND_GREEN)
            v_lbl.next_to(v_dot, DOWN + RIGHT, buff=0.1)
            self.play(FadeIn(v_dot), Write(v_lbl))
        self.wait(1.5)

        self.play(FadeOut(*self.mobjects))
        self.wait(0.5)


if __name__ == "__main__":
    pass
