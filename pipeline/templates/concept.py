from manim import *


class ConceptScene(Scene):
    def construct(self):
        # ── Title ─────────────────────────────────────────────────────────────
        title = Text("FILL_IN_CONCEPT_TITLE", font_size=36)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait("BEAT_1")

        # ── Plain-English definition ──────────────────────────────────────────
        definition = Text(
            "FILL_IN_PLAIN_ENGLISH_DEFINITION",
            font_size=28,
            line_spacing=1.4,
        )
        definition.scale_to_fit_width(11)
        definition.move_to(UP * 1.5)
        self.play(FadeIn(definition))
        self.wait("BEAT_2")

        # ── Formal definition / key equation ─────────────────────────────────
        formal = MathTex(r"FILL_IN_FORMAL_DEFINITION", font_size=36)
        formal.scale_to_fit_width(10)
        formal.move_to(ORIGIN)
        self.play(Write(formal))
        self.wait("BEAT_3")

        # ── Anatomy: label the parts ──────────────────────────────────────────
        # FILL_IN: Add Brace + Text labels for each named component.
        # Example:
        #   brace_slope = Brace(formal[0][2:4], DOWN)
        #   label_slope = brace_slope.get_text("slope", font_size=24)
        #   self.play(Create(brace_slope), Write(label_slope))
        self.wait("BEAT_4")

        # ── Supporting visualization ──────────────────────────────────────────
        # FILL_IN: Add the visualization from viz_params (if applicable).
        # Position it in the lower content zone: y ∈ [-2.5, -0.5]
        self.wait("BEAT_5")

        self.play(FadeOut(*self.mobjects))
        self.wait(0.5)
