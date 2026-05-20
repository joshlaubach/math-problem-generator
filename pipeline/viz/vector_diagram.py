"""
viz/vector_diagram.py — Vector addition and component breakdown.
"""
from __future__ import annotations
import numpy as np
from manim import *
from pipeline.viz.helpers import BRAND_CARAMEL, BRAND_GREEN


class VectorDiagramScene(Scene):
    TITLE    = "Vectors in the Plane"
    VECTOR_A = [3, 1]
    VECTOR_B = [1, 2]
    SHOW_ADDITION = True

    def construct(self):
        title = Text(self.TITLE, font_size=32)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait(1.0)

        axes = Axes(
            x_range=[-1, 6, 1], y_range=[-1, 5, 1],
            x_length=8, y_length=6,
            axis_config={"stroke_width": 2, "include_tip": True, "tip_length": 0.15},
            tips=False,
        ).move_to(DOWN * 0.3 + LEFT * 0.5)
        self.play(Create(axes))

        origin = axes.c2p(0, 0)
        ax, ay = self.VECTOR_A
        bx, by = self.VECTOR_B

        # Vector A
        a_end = axes.c2p(ax, ay)
        vec_a = Arrow(origin, a_end, color=BRAND_CARAMEL, stroke_width=3,
                      buff=0, tip_length=0.2)
        a_lbl = MathTex(r"\vec{a}", font_size=28, color=BRAND_CARAMEL)
        a_lbl.next_to(vec_a.get_center(), UP + LEFT, buff=0.1)

        # Components of A
        ax_line = DashedLine(origin, axes.c2p(ax, 0), color=BRAND_CARAMEL,
                             stroke_width=1.5, dash_length=0.1)
        ay_line = DashedLine(axes.c2p(ax, 0), a_end, color=BRAND_CARAMEL,
                             stroke_width=1.5, dash_length=0.1)
        ax_lbl = MathTex(str(ax), font_size=22, color=BRAND_CARAMEL)
        ax_lbl.next_to(axes.c2p(ax/2, 0), DOWN, buff=0.15)
        ay_lbl = MathTex(str(ay), font_size=22, color=BRAND_CARAMEL)
        ay_lbl.next_to(axes.c2p(ax, ay/2), RIGHT, buff=0.1)

        self.play(Create(vec_a), Write(a_lbl))
        self.play(Create(ax_line), Create(ay_line), Write(ax_lbl), Write(ay_lbl))
        self.wait(1.0)

        # Component notation
        comp_a = MathTex(rf"\vec{{a}} = \langle {ax}, {ay} \rangle", font_size=28, color=BRAND_CARAMEL)
        comp_a.to_edge(RIGHT, buff=0.5).shift(UP * 1.5)
        self.play(Write(comp_a))
        self.wait(0.8)

        if self.SHOW_ADDITION:
            # Vector B (starting from tip of A — tip-to-tail)
            b_start = a_end
            b_end = axes.c2p(ax + bx, ay + by)
            vec_b = Arrow(b_start, b_end, color=BRAND_GREEN, stroke_width=3,
                          buff=0, tip_length=0.2)
            b_lbl = MathTex(r"\vec{b}", font_size=28, color=BRAND_GREEN)
            b_lbl.next_to(vec_b.get_center(), RIGHT, buff=0.1)

            self.play(Create(vec_b), Write(b_lbl))
            self.wait(0.6)

            # Resultant
            result_end = b_end
            vec_r = Arrow(origin, result_end, color=YELLOW, stroke_width=3,
                          buff=0, tip_length=0.2)
            r_lbl = MathTex(r"\vec{a}+\vec{b}", font_size=26, color=YELLOW)
            r_lbl.next_to(vec_r.get_center(), DOWN + RIGHT, buff=0.1)

            self.play(Create(vec_r), Write(r_lbl))

            sum_note = MathTex(
                rf"\vec{{a}}+\vec{{b}} = \langle {ax+bx}, {ay+by} \rangle",
                font_size=26, color=YELLOW,
            )
            sum_note.to_edge(RIGHT, buff=0.5).shift(UP * 0.5)
            self.play(Write(sum_note))
            self.wait(1.5)

        self.play(FadeOut(*self.mobjects))
        self.wait(0.5)


if __name__ == "__main__":
    pass
