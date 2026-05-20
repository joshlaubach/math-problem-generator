"""
viz/number_line.py — Number line with interval shading and arrows.
"""
from __future__ import annotations
from manim import *
from pipeline.viz.helpers import BRAND_CARAMEL


class NumberLineScene(Scene):
    TITLE      = "Solving an Inequality"
    INEQUALITY = r"2x - 3 > 5"
    SOLUTION   = r"x > 4"
    CRITICAL_POINTS: list[tuple[float, bool]] = [(4, False)]  # (value, is_closed)
    SHADE_RIGHT = True   # shade to the right of last critical point
    SHADE_LEFT  = False
    X_RANGE    = [-1, 8]

    def construct(self):
        title = Text(self.TITLE, font_size=32)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait(1.0)

        # Equation → solution transform
        ineq = MathTex(self.INEQUALITY, font_size=40)
        ineq.move_to(UP * 1.8)
        self.play(Write(ineq))
        self.wait(1.0)

        sol = MathTex(self.SOLUTION, font_size=40, color=BRAND_CARAMEL)
        sol.move_to(UP * 1.8)
        self.play(TransformMatchingTex(ineq, sol))
        self.wait(1.0)

        # Number line
        nl = NumberLine(
            x_range=[self.X_RANGE[0], self.X_RANGE[1], 1],
            length=10,
            include_numbers=True,
            include_tip=True,
            tip_length=0.2,
            font_size=24,
        )
        nl.move_to(DOWN * 0.5)
        self.play(Create(nl))
        self.wait(0.5)

        # Critical points
        for val, is_closed in self.CRITICAL_POINTS:
            pt = nl.n2p(val)
            if is_closed:
                dot = Dot(pt, color=BRAND_CARAMEL, radius=0.12)
            else:
                dot = Circle(radius=0.12, color=BRAND_CARAMEL, stroke_width=3)
                dot.move_to(pt)
            self.play(Create(dot))

        # Shading
        if self.CRITICAL_POINTS:
            crit_val = self.CRITICAL_POINTS[-1][0]
            if self.SHADE_RIGHT:
                arrow = Arrow(
                    nl.n2p(crit_val),
                    nl.n2p(min(crit_val + 3, self.X_RANGE[1] - 0.3)),
                    color=BRAND_CARAMEL, stroke_width=5, buff=0, tip_length=0.25,
                )
                self.play(Create(arrow))
            if self.SHADE_LEFT:
                arrow = Arrow(
                    nl.n2p(crit_val),
                    nl.n2p(max(crit_val - 3, self.X_RANGE[0] + 0.3)),
                    color=BRAND_CARAMEL, stroke_width=5, buff=0, tip_length=0.25,
                )
                self.play(Create(arrow))

        self.wait(1.5)
        self.play(FadeOut(*self.mobjects))
        self.wait(0.5)


if __name__ == "__main__":
    pass
