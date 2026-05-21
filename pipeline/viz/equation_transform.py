"""
viz/equation_transform.py

Step-by-step algebraic manipulation using TransformMatchingTex.
Each step fades/transforms into the next with color highlighting.
"""
from __future__ import annotations
from manim import *
from pipeline.viz.helpers import BRAND_CARAMEL, safe_tex


class EquationTransformScene(Scene):
    """
    Animates a sequence of equation steps.
    Override STEPS with (latex_string, description_string) tuples.
    """
    TITLE = "Worked Example"
    STEPS: list[tuple[str, str]] = [
        (r"x^2 - 3x + 2 = 0",               "Start with the quadratic equation"),
        (r"(x - 1)(x - 2) = 0",              "Factor the left side"),
        (r"x - 1 = 0 \quad \text{or} \quad x - 2 = 0", "Set each factor equal to zero"),
        (r"x = 1 \quad \text{or} \quad x = 2",          "Solve each equation"),
    ]
    HIGHLIGHT_COLORS: dict[str, str] = {}  # e.g. {"x": YELLOW, "2": RED}

    def construct(self):
        title = Text(self.TITLE, font_size=34)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait(1.0)

        prev_eq = None
        desc_obj = None

        for i, (latex, desc) in enumerate(self.STEPS):
            eq = MathTex(latex, font_size=40)
            eq.scale_to_fit_width(min(eq.width, 10.5))
            eq.move_to(UP * 0.8)

            # Apply highlight colors if specified
            for part, color in self.HIGHLIGHT_COLORS.items():
                try:
                    eq.set_color_by_tex(part, color)
                except Exception:
                    pass

            # Description text below equation
            new_desc = Text(desc, font_size=26, color=LIGHT_GRAY)
            new_desc.scale_to_fit_width(min(new_desc.width, 11))
            new_desc.move_to(DOWN * 0.8)

            if prev_eq is None:
                self.play(Write(eq))
            else:
                self.play(
                    TransformMatchingTex(prev_eq, eq),
                    run_time=1.0,
                )

            if desc_obj is None:
                self.play(FadeIn(new_desc))
            else:
                self.play(Transform(desc_obj, new_desc))

            # Step number indicator
            step_num = Text(f"Step {i + 1}", font_size=20, color=GRAY)
            step_num.to_edge(LEFT, buff=0.3).to_edge(UP, buff=0.8)
            self.play(FadeIn(step_num, shift=RIGHT * 0.2), run_time=0.3)

            self.wait(1.8)
            self.play(FadeOut(step_num), run_time=0.2)

            prev_eq = eq
            desc_obj = new_desc

        # Final answer highlight
        if prev_eq is not None:
            box = SurroundingRectangle(prev_eq, color=GOLD, buff=0.2, stroke_width=2.5)
            self.play(Create(box))
            self.wait(1.5)

        self.play(FadeOut(*self.mobjects))
        self.wait(0.5)


if __name__ == "__main__":
    pass
