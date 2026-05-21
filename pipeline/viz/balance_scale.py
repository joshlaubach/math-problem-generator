"""
viz/balance_scale.py — Balance-scale metaphor for equation solving.
"""
from __future__ import annotations
from manim import *
from pipeline.viz.helpers import BRAND_CARAMEL, BRAND_GREEN


class BalanceScaleScene(Scene):
    TITLE  = "Balancing an Equation"
    # Each step: (left_tex, right_tex, operation_note)
    STEPS: list[tuple[str, str, str]] = [
        (r"2x + 6",  r"14",   ""),
        (r"2x",      r"8",    r"\text{subtract } 6 \text{ from both sides}"),
        (r"x",       r"4",    r"\text{divide both sides by } 2"),
    ]
    TILT_WRONG = False   # animate an unbalanced tilt before final balance

    _BEAM_W = 6.0
    _BEAM_Y = -0.6
    _PAN_W  = 2.2
    _PAN_H  = 0.18
    _PIVOT_Y = -1.1

    def construct(self):
        title = Text(self.TITLE, font_size=32)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait(1.0)

        self._draw_steps()

        self.play(FadeOut(*self.mobjects))
        self.wait(0.5)

    def _draw_steps(self):
        for i, (left_tex, right_tex, note) in enumerate(self.STEPS):
            self._show_step(left_tex, right_tex, note, i)
            if i < len(self.STEPS) - 1:
                self.play(FadeOut(*[m for m in self.mobjects
                                    if m not in self._title_group()]))
                self.wait(0.3)

    def _title_group(self):
        # Title mobject lives at index 0 — we preserve it across steps
        return []

    def _show_step(self, left_tex, right_tex, note, step_idx):
        by = self._BEAM_Y
        bw = self._BEAM_W
        pw = self._PAN_W
        ph = self._PAN_H
        piv_y = self._PIVOT_Y

        # Pivot triangle
        pivot = Triangle(fill_color=GRAY_C, fill_opacity=1, stroke_width=0)
        pivot.scale(0.3)
        pivot.move_to(DOWN * abs(piv_y))

        # Beam
        beam = Rectangle(width=bw, height=0.12, color=WHITE,
                          fill_color=WHITE, fill_opacity=1)
        beam.move_to(DOWN * abs(by))

        # Pans
        pan_l = Rectangle(width=pw, height=ph, color=BRAND_CARAMEL,
                           fill_color=BRAND_CARAMEL, fill_opacity=0.7)
        pan_l.move_to(LEFT * (bw / 2 - pw / 2) + DOWN * (abs(by) - 0.4))

        pan_r = Rectangle(width=pw, height=ph, color=BRAND_GREEN,
                           fill_color=BRAND_GREEN, fill_opacity=0.7)
        pan_r.move_to(RIGHT * (bw / 2 - pw / 2) + DOWN * (abs(by) - 0.4))

        # Strings from beam ends to pans
        str_l = Line(
            LEFT * (bw / 2) + DOWN * abs(by),
            LEFT * (bw / 2 - pw / 2) + DOWN * (abs(by) - 0.4),
            stroke_width=1.5, color=GRAY_A,
        )
        str_r = Line(
            RIGHT * (bw / 2) + DOWN * abs(by),
            RIGHT * (bw / 2 - pw / 2) + DOWN * (abs(by) - 0.4),
            stroke_width=1.5, color=GRAY_A,
        )

        scale_grp = VGroup(pivot, beam, pan_l, pan_r, str_l, str_r)
        self.play(FadeIn(scale_grp))
        self.wait(0.3)

        # Expressions on pans
        left_expr = MathTex(left_tex, font_size=34, color=BRAND_CARAMEL)
        left_expr.next_to(pan_l, UP, buff=0.3)

        right_expr = MathTex(right_tex, font_size=34, color=BRAND_GREEN)
        right_expr.next_to(pan_r, UP, buff=0.3)

        eq_sign = MathTex("=", font_size=36, color=WHITE)
        eq_sign.move_to(UP * 0.2)

        self.play(Write(left_expr), Write(right_expr), Write(eq_sign))
        self.wait(0.8)

        # Tilt animation on first step if requested
        if self.TILT_WRONG and step_idx == 0:
            self.play(scale_grp.animate.rotate(0.12, about_point=DOWN * abs(piv_y)),
                      run_time=0.6)
            self.play(scale_grp.animate.rotate(-0.12, about_point=DOWN * abs(piv_y)),
                      run_time=0.6)

        # Operation note
        if note:
            op_lbl = MathTex(note, font_size=26, color=YELLOW)
            op_lbl.to_edge(RIGHT, buff=0.4).shift(UP * 0.5)
            arrow_l = Arrow(op_lbl.get_left() + LEFT * 0.1,
                            left_expr.get_right() + RIGHT * 0.1,
                            color=YELLOW, stroke_width=1.5, buff=0.15, tip_length=0.15)
            arrow_r = Arrow(op_lbl.get_left() + LEFT * 0.1,
                            right_expr.get_right() + RIGHT * 0.1,
                            color=YELLOW, stroke_width=1.5, buff=0.15, tip_length=0.15)
            self.play(Write(op_lbl))
            self.play(Create(arrow_l), Create(arrow_r))
            self.wait(1.0)

        # Final step: gold box on answer
        if step_idx == len(self.STEPS) - 1:
            box = SurroundingRectangle(right_expr, color=GOLD, buff=0.15, stroke_width=2.5)
            self.play(Create(box))
        self.wait(1.2)


if __name__ == "__main__":
    pass
