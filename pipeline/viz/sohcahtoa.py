"""
viz/sohcahtoa.py — SOHCAHTOA right-triangle trig ratio animation.

Scene 1: Build the triangle with color-coded sides
Scene 2: Reveal each ratio (SOH, CAH, TOA) one at a time
Scene 3: ValueTracker sweeps theta — ratios update live
Scene 4: Similar triangles — ratios independent of size
"""
from __future__ import annotations
import math
import numpy as np
from manim import *
from pipeline.viz.helpers import BRAND_CARAMEL, BRAND_GREEN, safe_tex


HYP_COLOR = GOLD
OPP_COLOR = BLUE
ADJ_COLOR = GREEN


class SOHCAHTOAScene(Scene):
    THETA_DEG    = 35
    TRIANGLE_SCALE = 1.8   # base leg length in Manim units

    def construct(self):
        # ── Title ─────────────────────────────────────────────────────────────
        title = Text("SOH-CAH-TOA", font_size=36, color=YELLOW)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait(1.5)

        # ── Scene 1: Build the triangle ───────────────────────────────────────
        triangle_group = self._build_triangle(self.THETA_DEG, self.TRIANGLE_SCALE)
        triangle_group.move_to(LEFT * 2.5 + DOWN * 0.3)
        self.play(Create(triangle_group))
        self.wait(1.5)

        # ── Scene 2: Reveal each ratio ────────────────────────────────────────
        ratio_group = self._build_ratios()
        ratio_group.move_to(RIGHT * 2.8 + UP * 0.5)

        for i, (chunk, formula) in enumerate(zip(
            [ratio_group[0], ratio_group[2], ratio_group[4]],
            [ratio_group[1], ratio_group[3], ratio_group[5]],
        )):
            self.play(FadeIn(chunk), Write(formula))
            self.wait(1.5)

        # ── Scene 3: Sweep theta ──────────────────────────────────────────────
        self.play(FadeOut(triangle_group, ratio_group, title))
        self._sweep_theta_scene()

        # ── Scene 4: Similar triangles ────────────────────────────────────────
        self._similar_triangles_scene()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_triangle(self, theta_deg: float, scale: float) -> VGroup:
        theta = math.radians(theta_deg)
        adj = scale
        opp = adj * math.tan(theta)

        A = np.array([0, 0, 0])       # right angle
        B = np.array([adj, 0, 0])     # base
        C = np.array([0, opp, 0])     # top

        adj_line = Line(A, B, color=ADJ_COLOR, stroke_width=4)
        opp_line = Line(A, C, color=OPP_COLOR, stroke_width=4)
        hyp_line = Line(B, C, color=HYP_COLOR, stroke_width=4)

        # Right angle marker
        sq = 0.16
        right_marker = Polygon(A, A+RIGHT*sq, A+RIGHT*sq+UP*sq, A+UP*sq,
                                color=WHITE, stroke_width=2, fill_opacity=0)

        # Angle arc at B
        arc = Arc(radius=0.3, start_angle=PI - math.atan2(opp, adj),
                  angle=math.atan2(opp, adj), arc_center=B, color=YELLOW)
        theta_lbl = MathTex(r"\theta", font_size=22, color=YELLOW)
        theta_lbl.next_to(arc, LEFT + UP, buff=0.02)

        # Side labels
        adj_lbl = Text("adj", font_size=20, color=ADJ_COLOR)
        adj_lbl.next_to(Line(A, B), DOWN, buff=0.12)
        opp_lbl = Text("opp", font_size=20, color=OPP_COLOR)
        opp_lbl.next_to(Line(A, C), LEFT, buff=0.12)
        hyp_lbl = Text("hyp", font_size=20, color=HYP_COLOR)
        hyp_lbl.next_to(Line(B, C), RIGHT + UP, buff=0.08)

        return VGroup(adj_line, opp_line, hyp_line, right_marker,
                      arc, theta_lbl, adj_lbl, opp_lbl, hyp_lbl)

    def _build_ratios(self) -> VGroup:
        """Return alternating (mnemonic chunk, formula) pairs stacked vertically."""
        soh_chunk = Text("SOH", font_size=30, color=YELLOW)
        soh_form  = MathTex(r"\sin\theta = \dfrac{\text{opp}}{\text{hyp}}", font_size=28)
        soh_form[0][4:7].set_color(OPP_COLOR)
        soh_form[0][8:].set_color(HYP_COLOR)

        cah_chunk = Text("CAH", font_size=30, color=YELLOW)
        cah_form  = MathTex(r"\cos\theta = \dfrac{\text{adj}}{\text{hyp}}", font_size=28)
        cah_form[0][4:7].set_color(ADJ_COLOR)
        cah_form[0][8:].set_color(HYP_COLOR)

        toa_chunk = Text("TOA", font_size=30, color=YELLOW)
        toa_form  = MathTex(r"\tan\theta = \dfrac{\text{opp}}{\text{adj}}", font_size=28)
        toa_form[0][4:7].set_color(OPP_COLOR)
        toa_form[0][8:].set_color(ADJ_COLOR)

        group = VGroup(soh_chunk, soh_form, cah_chunk, cah_form, toa_chunk, toa_form)
        group.arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        return group

    def _sweep_theta_scene(self):
        """ValueTracker sweeps theta 15°→75°; all three ratios update live."""
        title2 = Text("How ratios change with θ", font_size=30)
        title2.to_edge(UP, buff=0.3)
        self.play(Write(title2))

        theta = ValueTracker(math.radians(15))

        # Build updatable triangle
        def get_triangle():
            t = theta.get_value()
            adj = 2.0
            opp = adj * math.tan(t)
            opp = min(opp, 3.2)  # clamp to safe zone
            A = np.array([0, 0, 0])
            B = np.array([adj, 0, 0])
            C = np.array([0, opp, 0])
            lines = VGroup(
                Line(A, B, color=ADJ_COLOR, stroke_width=3),
                Line(A, C, color=OPP_COLOR, stroke_width=3),
                Line(B, C, color=HYP_COLOR, stroke_width=3),
            )
            lines.shift(LEFT * 3.5 + DOWN * 1.5)
            return lines

        tri = always_redraw(get_triangle)
        self.add(tri)

        # Live decimal readouts
        sin_val = always_redraw(
            lambda: DecimalNumber(math.sin(theta.get_value()), num_decimal_places=3,
                                  font_size=28, color=OPP_COLOR)
                    .next_to(RIGHT * 1.5 + UP * 1.2, RIGHT, buff=0)
        )
        cos_val = always_redraw(
            lambda: DecimalNumber(math.cos(theta.get_value()), num_decimal_places=3,
                                  font_size=28, color=ADJ_COLOR)
                    .next_to(RIGHT * 1.5 + UP * 0.3, RIGHT, buff=0)
        )
        tan_val = always_redraw(
            lambda: DecimalNumber(min(math.tan(theta.get_value()), 9.99),
                                  num_decimal_places=3, font_size=28, color=YELLOW)
                    .next_to(RIGHT * 1.5 + DOWN * 0.6, RIGHT, buff=0)
        )

        sin_lbl = MathTex(r"\sin\theta =", font_size=28, color=OPP_COLOR).next_to(RIGHT * 0.2 + UP * 1.2, RIGHT, buff=0)
        cos_lbl = MathTex(r"\cos\theta =", font_size=28, color=ADJ_COLOR).next_to(RIGHT * 0.2 + UP * 0.3, RIGHT, buff=0)
        tan_lbl = MathTex(r"\tan\theta =", font_size=28, color=YELLOW).next_to(RIGHT * 0.2 + DOWN * 0.6, RIGHT, buff=0)
        self.add(sin_lbl, cos_lbl, tan_lbl, sin_val, cos_val, tan_val)

        self.play(
            theta.animate.set_value(math.radians(75)),
            run_time=4.0,
            rate_func=linear,
        )
        self.wait(1.5)
        self.play(FadeOut(*self.mobjects))
        self.wait(0.3)

    def _similar_triangles_scene(self):
        """Three similar triangles — same theta, different sizes, same ratios."""
        title3 = Text("Same angle → same ratios, any size", font_size=28)
        title3.to_edge(UP, buff=0.3)
        self.play(Write(title3))

        sizes = [0.9, 1.4, 2.0]
        theta = math.radians(self.THETA_DEG)
        positions = [LEFT * 4 + DOWN * 1.5, LEFT * 1.0 + DOWN * 0.8, RIGHT * 2.5 + DOWN * 0.3]

        for size, pos in zip(sizes, positions):
            t = self._build_triangle(self.THETA_DEG, size)
            t.move_to(pos)
            self.play(Create(t), run_time=0.6)

        self.wait(1.5)

        sin_note = MathTex(
            r"\sin\theta = \tfrac{\text{opp}}{\text{hyp}} \approx "
            + f"{math.sin(theta):.3f}",
            font_size=26, color=OPP_COLOR,
        )
        sin_note.to_edge(DOWN, buff=0.5)
        self.play(Write(sin_note))
        self.wait(1.5)
        self.play(FadeOut(*self.mobjects))
        self.wait(0.5)


if __name__ == "__main__":
    pass
