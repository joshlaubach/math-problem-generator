"""
viz/step_reveal.py — Sequential FadeIn of MathTex items with descriptions.
"""
from __future__ import annotations
from manim import *
from pipeline.viz.helpers import BRAND_CARAMEL, safe_tex


class StepRevealScene(Scene):
    TITLE = "Step by Step"
    STEPS: list[tuple[str, str]] = [
        (r"2x + 6 = 14",      "Start with the equation"),
        (r"2x = 8",           "Subtract 6 from both sides"),
        (r"x = 4",            "Divide both sides by 2"),
    ]

    def construct(self):
        title = Text(self.TITLE, font_size=34)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait(1.0)

        step_objects = []
        for i, (latex, desc) in enumerate(self.STEPS):
            eq = MathTex(latex, font_size=38)
            eq.scale_to_fit_width(min(eq.width, 10))
            desc_txt = Text(desc, font_size=24, color=LIGHT_GRAY)
            desc_txt.scale_to_fit_width(min(desc_txt.width, 10))

            y_pos = 1.5 - i * 1.8
            eq.move_to(UP * y_pos + LEFT * 1.5)
            desc_txt.move_to(UP * (y_pos - 0.5) + LEFT * 1.5)

            step_num = MathTex(f"{i+1}.", font_size=28, color=BRAND_CARAMEL)
            step_num.next_to(eq, LEFT, buff=0.3)

            self.play(FadeIn(step_num, eq, shift=RIGHT * 0.3), run_time=0.6)
            self.play(FadeIn(desc_txt, shift=RIGHT * 0.2), run_time=0.4)
            self.wait(1.5)
            step_objects.extend([step_num, eq, desc_txt])

        # Box the final answer
        final_eq = step_objects[-2]
        box = SurroundingRectangle(final_eq, color=GOLD, buff=0.15, stroke_width=2.5)
        self.play(Create(box))
        self.wait(1.5)

        self.play(FadeOut(*self.mobjects))
        self.wait(0.5)


if __name__ == "__main__":
    pass
