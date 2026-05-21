from manim import *


class SummaryScene(Scene):
    def construct(self):
        # ── Title ─────────────────────────────────────────────────────────────
        title = Text("Summary", font_size=36)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait("BEAT_1")

        # ── Key concept recap ─────────────────────────────────────────────────
        concept_label = Text("Key Idea:", font_size=28, color=GOLD)
        concept_label.move_to(UP * 2.0 + LEFT * 4)

        key_eq = MathTex(r"FILL_IN_KEY_EQUATION")
        key_eq.scale_to_fit_width(9)
        key_eq.move_to(UP * 1.2)

        self.play(FadeIn(concept_label), Write(key_eq))
        self.wait("BEAT_2")

        # ── What to remember ─────────────────────────────────────────────────
        remember = VGroup(
            Text("• FILL_IN_POINT_1", font_size=26),
            Text("• FILL_IN_POINT_2", font_size=26),
            Text("• FILL_IN_POINT_3", font_size=26),
        )
        remember.arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        remember.scale_to_fit_width(10)
        remember.move_to(DOWN * 0.8)

        for line in remember:
            self.play(FadeIn(line, shift=RIGHT * 0.3))
            self.wait(0.4)
        self.wait("BEAT_3")

        # ── Closing visual ────────────────────────────────────────────────────
        # FILL_IN: A clean, static version of the main visualization from the
        # worked example — the "final answer" visual state.
        self.wait("BEAT_4")

        self.play(FadeOut(*self.mobjects))
        self.wait(0.5)
