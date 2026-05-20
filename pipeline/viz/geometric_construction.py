"""
viz/geometric_construction.py

Conic section geometric constructions: focus, directrix, distance annotations.
"""
from __future__ import annotations
import numpy as np
from manim import *
from pipeline.viz.helpers import BRAND_CARAMEL, BRAND_GREEN


class ParabolaConstructionScene(Scene):
    """Shows parabola as locus: distance to focus = distance to directrix."""

    P = 1.5   # distance from vertex to focus (and vertex to directrix)

    def construct(self):
        title = Text("Parabola: Focus and Directrix", font_size=32)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait(1.2)

        p = self.P
        axes = Axes(
            x_range=[-1, 6, 1], y_range=[-3.5, 3.5, 1],
            x_length=8, y_length=6,
            axis_config={"stroke_width": 1.5, "color": GRAY, "include_tip": True, "tip_length": 0.15},
            tips=False,
        ).move_to(DOWN * 0.2 + RIGHT * 0.5)
        self.play(Create(axes))

        # Directrix line: x = -p
        directrix_x = axes.c2p(-p, 0)[0]
        directrix = DashedLine(
            [directrix_x, axes.c2p(0, -3.2)[1], 0],
            [directrix_x, axes.c2p(0,  3.2)[1], 0],
            color=RED, stroke_width=2, dash_length=0.15,
        )
        dir_label = MathTex(r"x = -p", font_size=22, color=RED)
        dir_label.next_to([directrix_x, axes.c2p(0, 3.2)[1], 0], UP, buff=0.1)
        self.play(Create(directrix), Write(dir_label))

        # Focus
        focus_pt = axes.c2p(p, 0)
        focus = Dot(focus_pt, color=YELLOW, radius=0.1)
        focus_lbl = MathTex(r"F(p,0)", font_size=22, color=YELLOW)
        focus_lbl.next_to(focus, DOWN, buff=0.15)
        self.play(Create(focus), Write(focus_lbl))
        self.wait(1.0)

        # Parabola curve: y² = 4px → x = y²/(4p)
        parabola = axes.plot_parametric_curve(
            lambda t: np.array([t**2 / (4*p), t, 0]),
            t_range=[-3.2, 3.2],
            color=BRAND_CARAMEL, stroke_width=3,
        )
        self.play(Create(parabola))
        self.wait(1.0)

        # Moving point showing the equal-distance property
        t_tracker = ValueTracker(2.0)

        def get_point_on_parabola():
            t = t_tracker.get_value()
            return axes.c2p(t**2 / (4*p), t)

        def get_focus_line():
            pt = get_point_on_parabola()
            return Line(pt, focus_pt, color=BRAND_GREEN, stroke_width=2)

        def get_directrix_line():
            pt = get_point_on_parabola()
            nearest_on_dir = [directrix_x, pt[1], 0]
            return Line(pt, nearest_on_dir, color=RED, stroke_width=2)

        def get_point_dot():
            return Dot(get_point_on_parabola(), color=WHITE, radius=0.09)

        p_dot = always_redraw(get_point_dot)
        f_line = always_redraw(get_focus_line)
        d_line = always_redraw(get_directrix_line)

        equal_label = MathTex(r"d_1 = d_2", font_size=26, color=WHITE)
        equal_label.to_edge(RIGHT, buff=0.4).shift(UP * 1.5)

        self.add(p_dot, f_line, d_line)
        self.play(Write(equal_label))
        self.wait(0.8)

        # Sweep the point
        self.play(t_tracker.animate.set_value(-2.5), run_time=3.0, rate_func=smooth)
        self.play(t_tracker.animate.set_value(2.8),  run_time=3.0, rate_func=smooth)
        self.wait(1.5)

        # Label p
        vertex_pt = axes.c2p(0, 0)
        p_brace = DoubleArrow(vertex_pt, focus_pt, color=YELLOW,
                              stroke_width=2, buff=0, tip_length=0.15)
        p_brace.shift(DOWN * 0.4)
        p_lbl = MathTex("p", font_size=24, color=YELLOW).next_to(p_brace, DOWN, buff=0.1)
        self.play(Create(p_brace), Write(p_lbl))
        self.wait(1.5)

        self.play(FadeOut(*self.mobjects))
        self.wait(0.5)


class EllipseConstructionScene(Scene):
    """Shows ellipse with labeled a, b, c and eccentricity."""

    A = 3.0   # semi-major axis
    B = 2.0   # semi-minor axis

    def construct(self):
        import math
        title = Text("Ellipse: Anatomy", font_size=32)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait(1.0)

        a, b = self.A, self.B
        c = math.sqrt(a**2 - b**2)
        ecc = c / a

        axes = Axes(
            x_range=[-a-0.5, a+0.5, 1], y_range=[-b-0.5, b+0.5, 1],
            x_length=9, y_length=6,
            axis_config={"stroke_width": 1.5, "color": GRAY},
            tips=False,
        ).move_to(DOWN * 0.2)
        self.play(Create(axes))

        ellipse = axes.plot_parametric_curve(
            lambda t: np.array([a * np.cos(t), b * np.sin(t), 0]),
            t_range=[0, 2*PI], color=BRAND_CARAMEL, stroke_width=3,
        )
        self.play(Create(ellipse))
        self.wait(0.8)

        # Foci
        f1 = Dot(axes.c2p( c, 0), color=YELLOW, radius=0.09)
        f2 = Dot(axes.c2p(-c, 0), color=YELLOW, radius=0.09)
        f1_lbl = MathTex(r"F_1", font_size=20, color=YELLOW).next_to(f1, DOWN, buff=0.1)
        f2_lbl = MathTex(r"F_2", font_size=20, color=YELLOW).next_to(f2, DOWN, buff=0.1)
        self.play(FadeIn(f1, f2), Write(f1_lbl), Write(f2_lbl))

        # a label (semi-major)
        a_line = DoubleArrow(axes.c2p(0, 0), axes.c2p(a, 0),
                             color=BRAND_GREEN, stroke_width=2, buff=0, tip_length=0.15)
        a_line.shift(DOWN * 0.35)
        a_lbl = MathTex("a", font_size=24, color=BRAND_GREEN).next_to(a_line, DOWN, buff=0.1)

        # b label (semi-minor)
        b_line = DoubleArrow(axes.c2p(0, 0), axes.c2p(0, b),
                             color=BLUE, stroke_width=2, buff=0, tip_length=0.15)
        b_line.shift(LEFT * 0.35)
        b_lbl = MathTex("b", font_size=24, color=BLUE).next_to(b_line, LEFT, buff=0.1)

        # c label
        c_line = DoubleArrow(axes.c2p(0, 0), axes.c2p(c, 0),
                             color=RED, stroke_width=2, buff=0, tip_length=0.15)
        c_line.shift(UP * 0.35)
        c_lbl = MathTex("c", font_size=24, color=RED).next_to(c_line, UP, buff=0.1)

        self.play(Create(a_line), Write(a_lbl))
        self.wait(0.7)
        self.play(Create(b_line), Write(b_lbl))
        self.wait(0.7)
        self.play(Create(c_line), Write(c_lbl))
        self.wait(0.8)

        # Eccentricity
        ecc_label = MathTex(rf"e = \dfrac{{c}}{{a}} = {ecc:.3f}", font_size=28)
        ecc_label.to_edge(RIGHT, buff=0.5).shift(UP * 2.0)
        self.play(Write(ecc_label))
        self.wait(1.5)

        self.play(FadeOut(*self.mobjects))
        self.wait(0.5)


if __name__ == "__main__":
    pass
