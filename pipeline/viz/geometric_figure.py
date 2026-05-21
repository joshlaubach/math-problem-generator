"""
viz/geometric_figure.py — Geometric shapes with labeled sides, angles, and area.
"""
from __future__ import annotations
import numpy as np
from manim import *
from pipeline.viz.helpers import BRAND_CARAMEL, BRAND_GREEN


class GeometricFigureScene(Scene):
    TITLE        = "Geometry of the Right Triangle"
    SHAPE        = "right_triangle"   # "right_triangle" | "rectangle" | "circle" | "general_triangle"
    SIDE_LABELS  = ["a = 3", "b = 4", "c = 5"]   # "" to skip
    ANGLE_LABELS = ["37°", "53°", "90°"]          # "" to skip
    AREA_TEX     = r"\text{Area} = \tfrac{1}{2}(3)(4) = 6"
    HIGHLIGHT_HYPOTENUSE = True

    def construct(self):
        title = Text(self.TITLE, font_size=32)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait(1.0)

        if self.SHAPE == "right_triangle":
            self._right_triangle()
        elif self.SHAPE == "rectangle":
            self._rectangle()
        elif self.SHAPE == "circle":
            self._circle()
        elif self.SHAPE == "general_triangle":
            self._general_triangle()

        self.play(FadeOut(*self.mobjects))
        self.wait(0.5)

    # ------------------------------------------------------------------ #
    def _right_triangle(self):
        # Build triangle centred on screen
        w, h = 4.5, 3.2
        A = np.array([-w / 2,  -h / 2, 0])   # right-angle vertex
        B = np.array([ w / 2,  -h / 2, 0])   # bottom-right
        C = np.array([-w / 2,   h / 2, 0])   # top-left

        # Shift centroid to slightly below centre so title has room
        centroid = (A + B + C) / 3
        shift = np.array([0.4, -0.1, 0]) - centroid
        A += shift; B += shift; C += shift

        poly = Polygon(A, B, C,
                       fill_color=BRAND_CARAMEL, fill_opacity=0.15,
                       stroke_color=WHITE, stroke_width=2.5)
        self.play(Create(poly))
        self.wait(0.5)

        # Right-angle mark at A
        ra_size = 0.22
        ra = VGroup(
            Line(A + RIGHT * ra_size, A + RIGHT * ra_size + UP * ra_size, stroke_width=2),
            Line(A + UP * ra_size,    A + RIGHT * ra_size + UP * ra_size, stroke_width=2),
        )
        self.play(Create(ra))

        # Side labels
        mid_AB = (A + B) / 2
        mid_BC = (B + C) / 2
        mid_AC = (A + C) / 2
        positions = [mid_AB + DOWN * 0.35, mid_BC + RIGHT * 0.42, mid_AC + LEFT * 0.42]
        labels_list = self.SIDE_LABELS[:3]

        side_lbls = VGroup()
        for txt, pos in zip(labels_list, positions):
            if txt:
                lbl = Text(txt, font_size=26, color=BRAND_CARAMEL)
                lbl.move_to(pos)
                side_lbls.add(lbl)

        if self.HIGHLIGHT_HYPOTENUSE and len(labels_list) >= 3:
            hyp = Line(B, C, color=GOLD, stroke_width=4)
            self.play(Create(hyp))

        self.play(Write(side_lbls))
        self.wait(0.8)

        # Angle labels — skip the 90° text since the square mark already signals it
        angle_data = [
            # (vertex, neighbour1, neighbour2, label_text)
            (B, A, C, self.ANGLE_LABELS[0] if len(self.ANGLE_LABELS) > 0 else ""),  # bottom-right
            (C, A, B, self.ANGLE_LABELS[1] if len(self.ANGLE_LABELS) > 1 else ""),  # top-left
            # 90° at A is shown by the square mark; only add text if explicitly given
            # and place it safely inside the triangle, away from the mark
        ]
        angle_lbls = VGroup()
        for vertex, p1, p2, lbl_txt in angle_data:
            if not lbl_txt:
                continue
            lbl = Text(lbl_txt, font_size=22, color=BRAND_GREEN)
            # Point inside the triangle from this vertex
            interior = (A + B + C) / 3
            direction = interior - vertex
            norm = np.linalg.norm(direction)
            if norm > 0:
                direction = direction / norm * 0.5
            lbl.move_to(vertex + direction)
            angle_lbls.add(lbl)

        self.play(Write(angle_lbls))
        self.wait(1.0)

        # Area note
        if self.AREA_TEX:
            area = MathTex(self.AREA_TEX, font_size=28, color=YELLOW)
            area.to_edge(RIGHT, buff=0.4).shift(UP * 0.5)
            box = SurroundingRectangle(area, color=YELLOW, buff=0.15, stroke_width=1.5)
            self.play(Write(area), Create(box))
            self.wait(1.5)

    # ------------------------------------------------------------------ #
    def _rectangle(self):
        w, h = 5.0, 3.0
        rect = Rectangle(width=w, height=h,
                         fill_color=BRAND_GREEN, fill_opacity=0.12,
                         stroke_color=WHITE, stroke_width=2.5)
        self.play(Create(rect))
        self.wait(0.5)

        lbls = self.SIDE_LABELS
        if len(lbls) >= 2:
            t_w = Text(lbls[0], font_size=28, color=BRAND_CARAMEL)
            t_w.next_to(rect, DOWN, buff=0.3)
            t_h = Text(lbls[1], font_size=28, color=BRAND_CARAMEL)
            t_h.next_to(rect, RIGHT, buff=0.3)
            self.play(Write(t_w), Write(t_h))
            self.wait(0.8)

        if self.AREA_TEX:
            area = MathTex(self.AREA_TEX, font_size=30, color=YELLOW)
            area.move_to(DOWN * 2.5)
            self.play(Write(area))
            self.wait(1.5)

    # ------------------------------------------------------------------ #
    def _circle(self):
        circ = Circle(radius=2.0,
                      fill_color=BRAND_CARAMEL, fill_opacity=0.12,
                      stroke_color=WHITE, stroke_width=2.5)
        self.play(Create(circ))

        center_dot = Dot(ORIGIN, color=WHITE, radius=0.06)
        self.play(Create(center_dot))

        # Radius line + label
        radius_line = Line(ORIGIN, RIGHT * 2.0, color=BRAND_GREEN, stroke_width=2.5)
        self.play(Create(radius_line))

        if self.SIDE_LABELS:
            r_lbl = Text(self.SIDE_LABELS[0], font_size=28, color=BRAND_GREEN)
            r_lbl.next_to(radius_line, UP, buff=0.15)
            self.play(Write(r_lbl))

        self.wait(0.8)
        if self.AREA_TEX:
            area = MathTex(self.AREA_TEX, font_size=30, color=YELLOW)
            area.move_to(DOWN * 2.8)
            self.play(Write(area))
            self.wait(1.5)

    # ------------------------------------------------------------------ #
    def _general_triangle(self):
        A = np.array([-2.5, -1.5, 0])
        B = np.array([ 2.5, -1.5, 0])
        C = np.array([ 0.5,  1.8, 0])

        poly = Polygon(A, B, C,
                       fill_color=BRAND_GREEN, fill_opacity=0.12,
                       stroke_color=WHITE, stroke_width=2.5)
        self.play(Create(poly))
        self.wait(0.5)

        mids = [(A + B) / 2 + DOWN * 0.35,
                (B + C) / 2 + RIGHT * 0.4,
                (A + C) / 2 + LEFT * 0.4]

        side_lbls = VGroup()
        for txt, pos in zip(self.SIDE_LABELS, mids):
            if txt:
                lbl = Text(txt, font_size=26, color=BRAND_CARAMEL)
                lbl.move_to(pos)
                side_lbls.add(lbl)
        self.play(Write(side_lbls))
        self.wait(1.0)

        if self.AREA_TEX:
            area = MathTex(self.AREA_TEX, font_size=28, color=YELLOW)
            area.move_to(DOWN * 2.8)
            self.play(Write(area))
            self.wait(1.5)


if __name__ == "__main__":
    pass
