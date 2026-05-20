from manim import *


class CommonMistakesScene(Scene):
    def construct(self):
        # ── Title ─────────────────────────────────────────────────────────────
        title = Text("Common Mistakes", font_size=36, color=RED)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait("BEAT_1")

        # ── Mistake 1: Wrong vs Right ─────────────────────────────────────────
        wrong_label = Text("✗ Wrong", font_size=26, color=RED)
        wrong_label.move_to(LEFT * 3.2 + UP * 1.8)

        right_label = Text("✓ Correct", font_size=26, color=GREEN)
        right_label.move_to(RIGHT * 3.2 + UP * 1.8)

        divider = Line(UP * 2.5, DOWN * 2.5, color=GRAY)
        divider.move_to(ORIGIN)

        self.play(
            FadeIn(wrong_label),
            FadeIn(right_label),
            Create(divider),
        )
        self.wait("BEAT_2")

        # ── Wrong version ─────────────────────────────────────────────────────
        wrong_eq = MathTex(r"FILL_IN_WRONG_EXPRESSION", color=RED)
        wrong_eq.scale_to_fit_width(5)
        wrong_eq.move_to(LEFT * 3.2 + UP * 0.5)
        self.play(Write(wrong_eq))
        self.wait("BEAT_3")

        # ── Correct version ───────────────────────────────────────────────────
        right_eq = MathTex(r"FILL_IN_CORRECT_EXPRESSION", color=GREEN)
        right_eq.scale_to_fit_width(5)
        right_eq.move_to(RIGHT * 3.2 + UP * 0.5)
        self.play(Write(right_eq))
        self.wait("BEAT_4")

        # ── Explanation text ──────────────────────────────────────────────────
        explanation = Text(
            "FILL_IN_MISTAKE_EXPLANATION",
            font_size=24,
            line_spacing=1.3,
        )
        explanation.scale_to_fit_width(11)
        explanation.to_edge(DOWN, buff=0.6)
        self.play(FadeIn(explanation))
        self.wait("BEAT_5")

        # ── Additional mistakes (repeat pattern for each) ─────────────────────
        # FILL_IN: If there are more mistakes, fade out and repeat the pattern above.

        self.play(FadeOut(*self.mobjects))
        self.wait(0.5)
