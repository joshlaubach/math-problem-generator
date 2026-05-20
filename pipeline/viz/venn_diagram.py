"""
viz/venn_diagram.py — Two- or three-set Venn diagram with labeled regions.
"""
from __future__ import annotations
from manim import *
from pipeline.viz.helpers import BRAND_CARAMEL, BRAND_GREEN


class VennDiagramScene(Scene):
    TITLE   = "Set Operations"
    SET_A   = "A"
    SET_B   = "B"
    LABEL_A = "Odd"
    LABEL_B = "Prime"
    # Items that appear in each region (strings)
    ONLY_A       = ["1", "9", "15"]
    INTERSECTION = ["3", "5", "7"]
    ONLY_B       = ["2", "11", "13"]
    HIGHLIGHT    = "intersection"   # "A" | "B" | "intersection" | "union" | None
    # Union label shown bottom-right
    RESULT_TEX   = r"A \cap B = \{3,5,7\}"

    def construct(self):
        title = Text(self.TITLE, font_size=32)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait(1.0)

        self._draw_venn()

        self.play(FadeOut(*self.mobjects))
        self.wait(0.5)

    def _draw_venn(self):
        r = 1.6
        sep = 1.2   # half-distance between centres

        centre_a = LEFT  * sep
        centre_b = RIGHT * sep

        circle_a = Circle(radius=r, color=BRAND_CARAMEL, stroke_width=2.5,
                          fill_opacity=0.0)
        circle_a.move_to(centre_a)
        circle_b = Circle(radius=r, color=BRAND_GREEN, stroke_width=2.5,
                          fill_opacity=0.0)
        circle_b.move_to(centre_b)

        # Highlight before drawing
        if self.HIGHLIGHT == "intersection":
            # Draw filled intersection using Intersection
            hl = Intersection(circle_a, circle_b,
                               color=YELLOW, fill_opacity=0.35, stroke_width=0)
        elif self.HIGHLIGHT == "A":
            hl = Difference(circle_a, circle_b,
                            color=BRAND_CARAMEL, fill_opacity=0.4, stroke_width=0)
        elif self.HIGHLIGHT == "B":
            hl = Difference(circle_b, circle_a,
                            color=BRAND_GREEN, fill_opacity=0.4, stroke_width=0)
        elif self.HIGHLIGHT == "union":
            hl = Union(circle_a, circle_b,
                       color=YELLOW, fill_opacity=0.25, stroke_width=0)
        else:
            hl = None

        if hl is not None:
            self.play(FadeIn(hl))

        self.play(Create(circle_a), Create(circle_b))

        # Set name labels (outside each circle)
        lbl_a = Text(self.SET_A, font_size=32, color=BRAND_CARAMEL)
        lbl_a.next_to(circle_a, UP + LEFT, buff=0.1)
        lbl_b = Text(self.SET_B, font_size=32, color=BRAND_GREEN)
        lbl_b.next_to(circle_b, UP + RIGHT, buff=0.1)

        desc_a = Text(self.LABEL_A, font_size=22, color=BRAND_CARAMEL)
        desc_a.next_to(lbl_a, DOWN, buff=0.05)
        desc_b = Text(self.LABEL_B, font_size=22, color=BRAND_GREEN)
        desc_b.next_to(lbl_b, DOWN, buff=0.05)

        self.play(Write(lbl_a), Write(lbl_b), Write(desc_a), Write(desc_b))
        self.wait(0.5)

        # Region content
        def _place_items(items: list[str], center, color):
            if not items:
                return
            grp = VGroup(*[Text(s, font_size=22, color=color) for s in items])
            grp.arrange(DOWN, buff=0.18)
            grp.move_to(center)
            grp.scale_to_fit_height(min(grp.height, 2.0))
            self.play(Write(grp), run_time=0.5)

        only_a_center  = centre_a + LEFT  * (sep * 0.55)
        inter_center   = ORIGIN
        only_b_center  = centre_b + RIGHT * (sep * 0.55)

        _place_items(self.ONLY_A,       only_a_center,  BRAND_CARAMEL)
        _place_items(self.INTERSECTION, inter_center,   YELLOW)
        _place_items(self.ONLY_B,       only_b_center,  BRAND_GREEN)
        self.wait(0.8)

        if self.RESULT_TEX:
            result = MathTex(self.RESULT_TEX, font_size=30, color=YELLOW)
            result.to_edge(DOWN, buff=0.4)
            self.play(Write(result))
            self.wait(1.5)


if __name__ == "__main__":
    pass
