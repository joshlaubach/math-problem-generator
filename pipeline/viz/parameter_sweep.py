"""
viz/parameter_sweep.py

Generic parameter sweep: ValueTracker animates one variable,
always_redraw re-renders the shape continuously.

Primary use: conic eccentricity sweep (circle → ellipse → parabola → hyperbola),
function family sweeps, etc.
"""
from __future__ import annotations
import numpy as np
from manim import *
from pipeline.viz.helpers import BRAND_CARAMEL, safe_tex


class ConicEccentricitySweepScene(Scene):
    """Sweeps eccentricity from 0 → 2 showing conic type transformations."""

    def construct(self):
        title = Text("Eccentricity and Conic Sections", font_size=32)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait(1.2)

        axes = Axes(
            x_range=[-5, 5, 1], y_range=[-4, 4, 1],
            x_length=8, y_length=6,
            axis_config={"stroke_width": 1.5, "color": GRAY, "include_tip": True, "tip_length": 0.15},
            tips=False,
        ).move_to(DOWN * 0.3)

        self.play(Create(axes))

        e = ValueTracker(0.0)

        # Focus and directrix (for the focus-directrix definition)
        focus_x = 1.0  # fixed focus at (1, 0)

        def get_conic():
            ev = e.get_value()
            points = []
            # Use focus-directrix definition: distance to focus / distance to directrix = e
            # For e < 1: ellipse, e = 1: parabola, e > 1: hyperbola
            # Parametric: for ellipse/circle use standard form
            if ev < 0.01:  # circle
                pts = [axes.c2p(2 * np.cos(t), 2 * np.sin(t)) for t in np.linspace(0, 2*PI, 120)]
                curve = VMobject(color=BRAND_CARAMEL, stroke_width=3)
                curve.set_points_smoothly(pts)
                return curve
            elif ev < 0.99:  # ellipse
                a = 1.0 / (1 - ev**2) if ev < 1 else 2.0
                b = a * np.sqrt(abs(1 - ev**2))
                a = min(a, 4.5)
                b = min(b, 3.5)
                pts = [axes.c2p(a * np.cos(t), b * np.sin(t)) for t in np.linspace(0, 2*PI, 120)]
                curve = VMobject(color=BRAND_CARAMEL, stroke_width=3)
                curve.set_points_smoothly(pts)
                return curve
            elif ev < 1.01:  # parabola
                pts = [axes.c2p(t**2 / 4 - 1, t) for t in np.linspace(-3.5, 3.5, 120)]
                curve = VMobject(color=YELLOW, stroke_width=3)
                curve.set_points_smoothly(pts)
                return curve
            else:  # hyperbola
                scale = min(ev * 0.8, 2.5)
                pts_upper = [axes.c2p(scale * np.cosh(t), scale * 0.8 * np.sinh(t))
                             for t in np.linspace(-2, 2, 80)]
                pts_lower = [axes.c2p(-scale * np.cosh(t), scale * 0.8 * np.sinh(t))
                             for t in np.linspace(-2, 2, 80)]
                c1 = VMobject(color=RED, stroke_width=3).set_points_smoothly(pts_upper)
                c2 = VMobject(color=RED, stroke_width=3).set_points_smoothly(pts_lower)
                return VGroup(c1, c2)

        def get_label():
            ev = e.get_value()
            if ev < 0.05:
                name = "Circle"
            elif ev < 0.99:
                name = "Ellipse"
            elif ev < 1.01:
                name = "Parabola"
            else:
                name = "Hyperbola"
            txt = VGroup(
                MathTex(f"e = {ev:.2f}", font_size=28, color=WHITE),
                Text(name, font_size=26, color=YELLOW),
            ).arrange(DOWN, buff=0.15)
            txt.move_to(RIGHT * 4.5 + UP * 2.5)
            return txt

        conic = always_redraw(get_conic)
        label = always_redraw(get_label)

        # Focus dot
        focus_dot = Dot(axes.c2p(focus_x, 0), color=WHITE, radius=0.07)
        focus_lbl = Text("F", font_size=20).next_to(focus_dot, DOWN, buff=0.1)

        self.add(conic, label, focus_dot, focus_lbl)
        self.wait(1.0)

        # Sweep: circle → ellipse
        self.play(e.animate.set_value(0.6), run_time=2.0, rate_func=smooth)
        self.wait(1.0)

        # → near-parabola
        self.play(e.animate.set_value(0.95), run_time=1.5, rate_func=smooth)
        self.wait(0.8)

        # → parabola
        self.play(e.animate.set_value(1.0), run_time=0.8, rate_func=smooth)
        self.wait(1.2)

        # → hyperbola
        self.play(e.animate.set_value(1.6), run_time=1.5, rate_func=smooth)
        self.wait(1.5)

        self.play(FadeOut(*self.mobjects))
        self.wait(0.5)


class FunctionFamilySweepScene(Scene):
    """Generic function family: y = a*f(x) with ValueTracker on a."""

    FUNC_LATEX  = r"y = a \cdot x^2"
    FUNC        = staticmethod(lambda x, a: a * x**2)
    PARAM_NAME  = "a"
    PARAM_START = 0.2
    PARAM_END   = 3.0
    X_RANGE     = [-4, 4, 1]
    Y_RANGE     = [-1, 9, 2]

    def construct(self):
        title = MathTex(self.FUNC_LATEX, font_size=34)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait(1.2)

        axes = Axes(
            x_range=self.X_RANGE, y_range=self.Y_RANGE,
            x_length=9, y_length=5.5,
            axis_config={"stroke_width": 2, "include_tip": True, "tip_length": 0.15},
            tips=False,
        ).move_to(DOWN * 0.5)
        self.play(Create(axes))

        param = ValueTracker(self.PARAM_START)
        fn = self.FUNC

        def get_curve():
            a = param.get_value()
            return axes.plot(lambda x: fn(x, a), color=BRAND_CARAMEL, stroke_width=3)

        def get_param_label():
            a = param.get_value()
            return MathTex(f"{self.PARAM_NAME} = {a:.2f}", font_size=28) \
                   .move_to(RIGHT * 4.5 + UP * 2.5)

        self.add(always_redraw(get_curve), always_redraw(get_param_label))

        self.play(param.animate.set_value(self.PARAM_END), run_time=4.0, rate_func=smooth)
        self.wait(1.5)
        self.play(FadeOut(*self.mobjects))
        self.wait(0.5)


if __name__ == "__main__":
    pass
