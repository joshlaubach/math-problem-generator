"""
viz/angle_sweep.py

Animates an angle opening from 0 to a target value.
Shows degree label, radian label, reference angle, and quadrant.
"""
from __future__ import annotations
import numpy as np
from manim import *
from pipeline.viz.helpers import BRAND_CARAMEL


class AngleSweepScene(Scene):
    END_DEG     = 135
    RADIUS      = 2.0
    SHOW_REF    = True   # show reference angle
    SHOW_RADIAN = True   # show radian equivalent

    def construct(self):
        title = Text("Angles and Their Measure", font_size=32)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait(1.0)

        # Axes
        origin = DOWN * 0.2
        h = Arrow(origin + LEFT * 3, origin + RIGHT * 3,
                  stroke_width=2, buff=0, color=GRAY, tip_length=0.15)
        v = Arrow(origin + DOWN * 2.8, origin + UP * 2.8,
                  stroke_width=2, buff=0, color=GRAY, tip_length=0.15)
        self.play(Create(h), Create(v))

        # Quadrant labels
        quads = VGroup(
            Text("I",   font_size=20, color=GRAY).move_to(origin + RIGHT * 1.8 + UP * 1.5),
            Text("II",  font_size=20, color=GRAY).move_to(origin + LEFT  * 1.8 + UP * 1.5),
            Text("III", font_size=20, color=GRAY).move_to(origin + LEFT  * 1.8 + DOWN * 1.5),
            Text("IV",  font_size=20, color=GRAY).move_to(origin + RIGHT * 1.8 + DOWN * 1.5),
        )
        self.play(FadeIn(quads))
        self.wait(0.8)

        # Angle tracker
        angle_t = ValueTracker(0.01)
        R = self.RADIUS

        def terminal_pt():
            a = angle_t.get_value()
            return origin + np.array([R * np.cos(a), R * np.sin(a), 0])

        terminal_ray = always_redraw(
            lambda: Arrow(origin, terminal_pt(), color=YELLOW,
                          stroke_width=3, buff=0, tip_length=0.2)
        )
        angle_arc = always_redraw(
            lambda: Arc(radius=0.5, start_angle=0, angle=angle_t.get_value(),
                        arc_center=origin, color=YELLOW, stroke_width=2.5)
        )
        deg_label = always_redraw(
            lambda: MathTex(f"{np.degrees(angle_t.get_value()):.0f}°", font_size=26, color=YELLOW)
                    .next_to(origin + RIGHT * 0.7 + UP * 0.5, RIGHT, buff=0.05)
        )

        initial_ray = Arrow(origin, origin + RIGHT * R, color=WHITE,
                            stroke_width=2, buff=0, tip_length=0.15)
        self.play(Create(initial_ray))
        self.add(terminal_ray, angle_arc, deg_label)
        self.wait(0.5)

        # Sweep to target
        target_rad = np.radians(self.END_DEG)
        self.play(
            angle_t.animate.set_value(target_rad),
            run_time=2.5,
            rate_func=smooth,
        )
        self.wait(1.2)

        # Radian label
        if self.SHOW_RADIAN:
            rad_val = target_rad
            # Format as fraction of pi if clean
            frac = rad_val / PI
            if abs(frac - round(frac * 4) / 4) < 0.01:
                numer = round(frac * 4)
                denom = 4
                from math import gcd
                g = gcd(abs(numer), denom)
                numer //= g; denom //= g
                if denom == 1:
                    rad_str = rf"{numer}\pi"
                elif numer == 1:
                    rad_str = rf"\dfrac{{\pi}}{{{denom}}}"
                elif numer == -1:
                    rad_str = rf"-\dfrac{{\pi}}{{{denom}}}"
                else:
                    rad_str = rf"\dfrac{{{numer}\pi}}{{{denom}}}"
            else:
                rad_str = rf"{rad_val:.3f}"
            rad_label = MathTex(rad_str + r"\text{ rad}", font_size=26, color=BRAND_CARAMEL)
            rad_label.to_edge(RIGHT, buff=0.5).shift(UP * 1.0)
            self.play(Write(rad_label))
            self.wait(1.0)

        # Reference angle
        if self.SHOW_REF and self.END_DEG > 90:
            ref_deg = 180 - self.END_DEG if self.END_DEG <= 180 else (
                self.END_DEG - 180 if self.END_DEG <= 270 else 360 - self.END_DEG)
            ref_rad = np.radians(ref_deg)
            pt = terminal_pt()
            x_axis_pt = np.array([pt[0], origin[1], 0])
            ref_line = DashedLine(pt, x_axis_pt, color=RED, stroke_width=2, dash_length=0.1)
            ref_arc = Arc(radius=0.35, start_angle=PI - ref_rad, angle=ref_rad,
                          arc_center=x_axis_pt, color=RED, stroke_width=2)
            ref_label = MathTex(f"{ref_deg}°", font_size=22, color=RED)
            ref_label.next_to(ref_arc, UP + LEFT, buff=0.05)
            self.play(Create(ref_line), Create(ref_arc), Write(ref_label))
            self.wait(1.5)

        self.play(FadeOut(*self.mobjects))
        self.wait(0.5)


if __name__ == "__main__":
    pass
