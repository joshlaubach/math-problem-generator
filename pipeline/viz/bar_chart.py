"""
viz/bar_chart.py — Animated bar/histogram chart for discrete data.
"""
from __future__ import annotations
from manim import *
from pipeline.viz.helpers import BRAND_CARAMEL, BRAND_GREEN


class BarChartScene(Scene):
    TITLE      = "Data Distribution"
    VALUES     = [3, 7, 5, 9, 4, 6]
    X_LABELS   = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    Y_LABEL    = "Count"
    BAR_COLORS = None   # None = alternating BRAND_CARAMEL / BRAND_GREEN
    SHOW_VALUES = True

    def construct(self):
        title = Text(self.TITLE, font_size=32)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait(1.0)

        colors = self.BAR_COLORS
        if colors is None:
            colors = [BRAND_CARAMEL if i % 2 == 0 else BRAND_GREEN
                      for i in range(len(self.VALUES))]

        chart = BarChart(
            values=self.VALUES,
            bar_names=self.X_LABELS,
            y_range=[0, max(self.VALUES) + 2, 2],
            y_length=4.5,
            x_length=min(1.0 * len(self.VALUES) + 2.0, 11.0),
            bar_colors=colors,
            bar_stroke_width=0,
            bar_fill_opacity=0.85,
        )
        chart.scale_to_fit_width(min(chart.width, 11.5))
        chart.move_to(DOWN * 0.2)

        y_lbl = Text(self.Y_LABEL, font_size=22, color=WHITE)
        y_lbl.rotate(PI / 2)
        y_lbl.next_to(chart, LEFT, buff=0.3)

        self.play(Create(chart), run_time=1.5)
        self.play(Write(y_lbl))
        self.wait(0.5)

        if self.SHOW_VALUES:
            val_labels = VGroup()
            for bar, val in zip(chart.bars, self.VALUES):
                lbl = Text(str(val), font_size=22, color=WHITE)
                lbl.next_to(bar, UP, buff=0.12)
                val_labels.add(lbl)
            self.play(Write(val_labels), run_time=0.8)

        self.wait(1.5)
        self.play(FadeOut(*self.mobjects))
        self.wait(0.5)


if __name__ == "__main__":
    pass
