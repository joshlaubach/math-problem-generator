"""
viz/mistake_comparison.py — Side-by-side wrong vs correct comparison.
"""
from __future__ import annotations
from manim import *
from pipeline.viz.helpers import safe_tex


class MistakeComparisonScene(Scene):
    TITLE    = "Common Mistakes"
    MISTAKES: list[tuple[str, str, str, str]] = [
        # (wrong_latex, correct_latex, wrong_explanation, correct_explanation)
        (
            r"(x+2)^2 = x^2 + 4",
            r"(x+2)^2 = x^2 + 4x + 4",
            "Forgot the middle term",
            "Use FOIL: (x+2)(x+2)",
        ),
    ]

    def construct(self):
        title = Text(self.TITLE, font_size=34, color=RED)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait(1.0)

        for wrong_latex, correct_latex, wrong_exp, correct_exp in self.MISTAKES:
            self._show_mistake(wrong_latex, correct_latex, wrong_exp, correct_exp)
            self.play(FadeOut(*[m for m in self.mobjects if m is not title]))
            self.wait(0.3)

        self.play(FadeOut(*self.mobjects))
        self.wait(0.5)

    def _show_mistake(self, wrong_latex, correct_latex, wrong_exp, correct_exp):
        # Column labels
        wrong_lbl = Text("✗  Wrong", font_size=28, color=RED)
        wrong_lbl.move_to(LEFT * 3.3 + UP * 2.0)
        right_lbl = Text("✓  Correct", font_size=28, color=GREEN)
        right_lbl.move_to(RIGHT * 3.3 + UP * 2.0)
        divider = Line(UP * 2.5, DOWN * 2.8, color=GRAY_C, stroke_width=1.5)

        self.play(Write(wrong_lbl), Write(right_lbl), Create(divider))
        self.wait(0.5)

        # Wrong equation
        wrong_eq = MathTex(wrong_latex, font_size=36, color=RED)
        wrong_eq.scale_to_fit_width(min(wrong_eq.width, 5.5))
        wrong_eq.move_to(LEFT * 3.3 + UP * 0.8)
        wrong_desc = Text(wrong_exp, font_size=22, color=LIGHT_GRAY, line_spacing=1.3)
        wrong_desc.scale_to_fit_width(min(wrong_desc.width, 5.5))
        wrong_desc.next_to(wrong_eq, DOWN, buff=0.35)

        self.play(Write(wrong_eq))
        self.play(FadeIn(wrong_desc))
        self.wait(0.8)

        # Correct equation
        right_eq = MathTex(correct_latex, font_size=36, color=GREEN)
        right_eq.scale_to_fit_width(min(right_eq.width, 5.5))
        right_eq.move_to(RIGHT * 3.3 + UP * 0.8)
        right_desc = Text(correct_exp, font_size=22, color=LIGHT_GRAY, line_spacing=1.3)
        right_desc.scale_to_fit_width(min(right_desc.width, 5.5))
        right_desc.next_to(right_eq, DOWN, buff=0.35)

        self.play(Write(right_eq))
        self.play(FadeIn(right_desc))

        # Highlight the difference
        box = SurroundingRectangle(right_eq, color=GREEN, buff=0.15, stroke_width=2)
        self.play(Create(box))
        self.wait(1.8)


if __name__ == "__main__":
    pass
