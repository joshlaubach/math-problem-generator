from manim import *


class HookScene(Scene):
    def construct(self):
        # ── Title card ────────────────────────────────────────────────────────
        title = Text("FILL_IN_TOPIC_NAME", font_size=36)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait("BEAT_1")

        # ── Opening visual ────────────────────────────────────────────────────
        # FILL_IN: Create the opening visualization relevant to this topic.
        # Use the appropriate viz type from the plan (coordinate_plane, unit_circle, etc.)
        # Place it in the content zone: y ∈ [-2.5, 2.5]
        opening_visual = FILL_IN_VISUALIZATION
        self.play(Create(opening_visual))
        self.wait("BEAT_2")

        # ── Hook question ─────────────────────────────────────────────────────
        # FILL_IN: The central question from the hook field.
        # Use Text, not MathTex, so it reads naturally.
        question = Text(
            "FILL_IN_QUESTION",
            font_size=28,
            color=YELLOW,
        )
        question.to_edge(DOWN, buff=0.5)
        self.play(FadeIn(question))
        self.wait("BEAT_3")

        # ── Fade to end ───────────────────────────────────────────────────────
        self.play(FadeOut(VGroup(title, opening_visual, question)))
        self.wait("BEAT_4")
