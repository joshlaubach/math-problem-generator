"""
viz/unit_circle.py

Exports: UnitCircleScene (base class) — used directly or as a foundation.

Renders a unit circle with a tracing dot, angle arc, and live sin/cos labels.
"""
from __future__ import annotations
from manim import *
import numpy as np
from pipeline.viz.helpers import BRAND_CARAMEL, BRAND_GREEN, make_axes


class UnitCircleScene(Scene):
    """
    Animates a point tracing around the unit circle.
    Configurable via class attributes — subclass and override.
    """
    RADIUS          = 2.2
    START_ANGLE_DEG = 0
    END_ANGLE_DEG   = 360
    HIGHLIGHT_DEGS  = [0, 30, 45, 60, 90, 120, 135, 150, 180, 210, 225, 240, 270, 300, 315, 330]
    SHOW_SIN_COS    = True
    TITLE_TEXT      = "The Unit Circle"

    def construct(self):
        R = self.RADIUS

        # ── Title ─────────────────────────────────────────────────────────────
        title = Text(self.TITLE_TEXT, font_size=34)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait(1.5)

        # ── Circle + axes ─────────────────────────────────────────────────────
        axes = Axes(
            x_range=[-1.5, 1.5, 0.5],
            y_range=[-1.5, 1.5, 0.5],
            x_length=R * 2.6,
            y_length=R * 2.6,
            axis_config={"include_tip": True, "tip_length": 0.15, "stroke_width": 2},
            tips=False,
        )
        axes.move_to(ORIGIN + LEFT * 0.5)

        circle = Circle(radius=R, color=WHITE, stroke_width=2)
        circle.move_to(axes.get_origin())

        # Unit labels
        one_x = MathTex("1", font_size=22).next_to(axes.get_origin() + RIGHT * R, DOWN, buff=0.1)
        one_y = MathTex("1", font_size=22).next_to(axes.get_origin() + UP * R, LEFT, buff=0.1)

        self.play(Create(axes), Create(circle), Write(one_x), Write(one_y))
        self.wait(1.5)

        # ── Angle tracker ─────────────────────────────────────────────────────
        angle_tracker = ValueTracker(0)
        origin = axes.get_origin()

        def dot_pos():
            a = angle_tracker.get_value()
            return origin + np.array([R * np.cos(a), R * np.sin(a), 0])

        dot = always_redraw(lambda: Dot(dot_pos(), color=YELLOW, radius=0.1))
        radius_line = always_redraw(
            lambda: Line(origin, dot_pos(), color=YELLOW, stroke_width=2)
        )
        angle_arc = always_redraw(
            lambda: Arc(
                radius=0.45,
                start_angle=0,
                angle=max(0.02, angle_tracker.get_value()),
                arc_center=origin,
                color=YELLOW,
                stroke_width=2,
            )
        )

        self.play(Create(dot), Create(radius_line), Create(angle_arc))

        # ── sin/cos projection lines ──────────────────────────────────────────
        if self.SHOW_SIN_COS:
            cos_line = always_redraw(
                lambda: DashedLine(
                    origin + RIGHT * R * np.cos(angle_tracker.get_value()),
                    dot_pos() + UP * 1e-4,   # 1e-4 prevents zero-length at 0°
                    color=BRAND_GREEN, stroke_width=2, dash_length=0.1,
                )
            )
            sin_line = always_redraw(
                lambda: DashedLine(
                    origin,
                    origin + RIGHT * R * np.cos(angle_tracker.get_value()) + RIGHT * 1e-4,
                    color=BRAND_CARAMEL, stroke_width=2, dash_length=0.1,
                )
            )

            cos_label = MathTex(r"\cos\theta", font_size=22, color=BRAND_CARAMEL)
            cos_label.add_updater(
                lambda m: m.next_to(
                    origin + RIGHT * R * np.cos(angle_tracker.get_value()) / 2,
                    DOWN, buff=0.15,
                )
            )
            sin_label = MathTex(r"\sin\theta", font_size=22, color=BRAND_GREEN)
            sin_label.add_updater(
                lambda m: m.next_to(
                    origin + RIGHT * R * np.cos(angle_tracker.get_value()) + UP * R * np.sin(angle_tracker.get_value()) / 2,
                    RIGHT, buff=0.12,
                )
            )
            self.add(cos_line, sin_line, cos_label, sin_label)

        # ── Sweep to 90° showing the geometry ────────────────────────────────
        self.play(
            angle_tracker.animate.set_value(PI / 2),
            run_time=2.5,
            rate_func=smooth,
        )
        self.wait(1.5)

        # ── Highlight standard positions ──────────────────────────────────────
        for deg in [30, 45, 60]:
            rad = np.radians(deg)
            pos = origin + np.array([R * np.cos(rad), R * np.sin(rad), 0])
            flash = Dot(pos, color=YELLOW, radius=0.08)
            coord = MathTex(
                rf"({np.cos(rad):.3f},\,{np.sin(rad):.3f})",
                font_size=18,
            )
            coord.next_to(pos, UR, buff=0.1)
            self.play(
                FadeIn(flash), Write(coord),
                angle_tracker.animate.set_value(rad),
                run_time=0.8,
            )
        self.wait(1.5)

        # ── Full rotation ─────────────────────────────────────────────────────
        self.play(
            angle_tracker.animate.set_value(2 * PI),
            run_time=4,
            rate_func=linear,
        )
        self.wait(1.5)

        self.play(FadeOut(*self.mobjects))
        self.wait(0.5)


if __name__ == "__main__":
    # Test render: manim -ql pipeline/viz/unit_circle.py UnitCircleScene
    pass
