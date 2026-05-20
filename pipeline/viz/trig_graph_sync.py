"""
viz/trig_graph_sync.py

Unit circle (left) + sin/cos/tan wave (right) synchronized.
As the angle sweeps, the wave draws in real time.
"""
from __future__ import annotations
import numpy as np
from manim import *
from pipeline.viz.helpers import BRAND_CARAMEL, BRAND_GREEN


class TrigGraphSyncScene(Scene):
    FUNCTION   = "sin"   # "sin" | "cos" | "tan"
    RADIUS     = 1.6
    WAVE_COLOR = BRAND_GREEN

    def construct(self):
        func_name = self.FUNCTION
        wave_color = BRAND_CARAMEL if func_name == "cos" else BRAND_GREEN

        title = Text(f"Where does the {func_name} curve come from?", font_size=30)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait(1.5)

        R = self.RADIUS
        # ── Left side: unit circle ─────────────────────────────────────────────
        circle_center = LEFT * 3.8 + DOWN * 0.2
        circle = Circle(radius=R, color=WHITE, stroke_width=2)
        circle.move_to(circle_center)

        h_axis = Arrow(circle_center + LEFT * (R + 0.3), circle_center + RIGHT * (R + 0.3),
                       stroke_width=2, color=GRAY, buff=0, tip_length=0.15)
        v_axis = Arrow(circle_center + DOWN * (R + 0.3), circle_center + UP * (R + 0.3),
                       stroke_width=2, color=GRAY, buff=0, tip_length=0.15)
        x_lbl = Text("x", font_size=18, color=GRAY).next_to(h_axis, RIGHT, buff=0.05)
        y_lbl = Text("y", font_size=18, color=GRAY).next_to(v_axis, UP, buff=0.05)

        self.play(Create(circle), Create(h_axis), Create(v_axis), Write(x_lbl), Write(y_lbl))

        # ── Right side: wave axes ──────────────────────────────────────────────
        wave_axes = Axes(
            x_range=[0, 2 * PI, PI / 2],
            y_range=[-1.4, 1.4, 0.5],
            x_length=5.8,
            y_length=3.2,
            axis_config={"stroke_width": 2, "include_tip": True, "tip_length": 0.15},
            tips=False,
        )
        wave_axes.move_to(RIGHT * 2.0 + DOWN * 0.2)

        x_axis_labels = VGroup(
            MathTex(r"\frac{\pi}{2}", font_size=18).next_to(wave_axes.c2p(PI/2, 0), DOWN, buff=0.15),
            MathTex(r"\pi",           font_size=18).next_to(wave_axes.c2p(PI,   0), DOWN, buff=0.15),
            MathTex(r"\frac{3\pi}{2}",font_size=18).next_to(wave_axes.c2p(3*PI/2,0),DOWN, buff=0.15),
            MathTex(r"2\pi",          font_size=18).next_to(wave_axes.c2p(2*PI, 0), DOWN, buff=0.15),
        )
        self.play(Create(wave_axes), Write(x_axis_labels))
        self.wait(1.0)

        # ── Angle tracker ──────────────────────────────────────────────────────
        angle = ValueTracker(0.001)

        def circle_dot():
            a = angle.get_value()
            return Dot(circle_center + np.array([R * np.cos(a), R * np.sin(a), 0]),
                       color=YELLOW, radius=0.09)

        def radius_line():
            a = angle.get_value()
            return Line(circle_center,
                        circle_center + np.array([R * np.cos(a), R * np.sin(a), 0]),
                        color=YELLOW, stroke_width=2)

        def projection_line():
            a = angle.get_value()
            if func_name == "sin":
                pt_on_circle = circle_center + np.array([R * np.cos(a), R * np.sin(a), 0])
                pt_on_axis   = circle_center + np.array([R * np.cos(a), 0, 0])
                return DashedLine(pt_on_circle, pt_on_axis, color=wave_color,
                                  stroke_width=1.5, dash_length=0.08)
            else:
                pt_on_circle = circle_center + np.array([R * np.cos(a), R * np.sin(a), 0])
                pt_on_axis   = circle_center + np.array([0, R * np.sin(a), 0])
                return DashedLine(pt_on_circle, pt_on_axis, color=wave_color,
                                  stroke_width=1.5, dash_length=0.08)

        def wave_dot():
            a = angle.get_value()
            val = np.sin(a) if func_name == "sin" else np.cos(a)
            return Dot(wave_axes.c2p(a, val), color=wave_color, radius=0.07)

        circ_dot = always_redraw(circle_dot)
        rad_line = always_redraw(radius_line)
        proj_line = always_redraw(projection_line)
        w_dot = always_redraw(wave_dot)

        # Traced wave path
        wave_path = VMobject(color=wave_color, stroke_width=2.5)
        wave_path.set_points_as_corners([wave_axes.c2p(0, 0), wave_axes.c2p(0, 0)])

        def update_wave(mob):
            a = angle.get_value()
            if func_name == "sin":
                points = [wave_axes.c2p(t, np.sin(t)) for t in np.linspace(0.001, a, max(2, int(a * 30)))]
            else:
                points = [wave_axes.c2p(t, np.cos(t)) for t in np.linspace(0.001, a, max(2, int(a * 30)))]
            if len(points) >= 2:
                mob.set_points_smoothly(points)

        wave_path.add_updater(update_wave)

        self.add(circ_dot, rad_line, proj_line, w_dot, wave_path)
        self.wait(0.5)

        # ── Sweep full rotation ────────────────────────────────────────────────
        self.play(
            angle.animate.set_value(2 * PI - 0.01),
            run_time=6.0,
            rate_func=linear,
        )
        self.wait(1.5)

        # ── Label the completed wave ───────────────────────────────────────────
        wave_label = MathTex(rf"y = \{func_name}(\theta)", font_size=28, color=wave_color)
        wave_label.next_to(wave_axes, DOWN, buff=0.3)
        self.play(Write(wave_label))
        self.wait(1.5)

        self.play(FadeOut(*self.mobjects))
        self.wait(0.5)


if __name__ == "__main__":
    pass
