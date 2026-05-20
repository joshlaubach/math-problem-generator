from manim import *


class WorkedExampleScene(Scene):
    def construct(self):
        # ── Title ─────────────────────────────────────────────────────────────
        title = Text("Worked Example", font_size=36)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait("BEAT_1")

        # ── Step 1 ────────────────────────────────────────────────────────────
        step1 = MathTex(r"FILL_IN_STEP_1_EXPRESSION")
        step1.scale_to_fit_width(10)
        step1.move_to(UP * 1.2)
        self.play(Write(step1))
        self.wait("BEAT_2")

        # ── Step 2 ────────────────────────────────────────────────────────────
        step2 = MathTex(r"FILL_IN_STEP_2_EXPRESSION")
        step2.scale_to_fit_width(10)
        step2.move_to(UP * 1.2)
        self.play(TransformMatchingTex(step1, step2))
        self.wait("BEAT_3")

        # ── Step 3 ────────────────────────────────────────────────────────────
        step3 = MathTex(r"FILL_IN_STEP_3_EXPRESSION")
        step3.scale_to_fit_width(10)
        step3.move_to(UP * 1.2)
        self.play(TransformMatchingTex(step2, step3))
        self.wait("BEAT_4")

        # ── Supporting visual (optional) ──────────────────────────────────────
        # FILL_IN: If viz_params specifies a coordinate_plane, unit_circle, etc.,
        # add it here in the lower zone: y ∈ [-2.5, -0.2]
        # It should update in sync with the equation steps above.
        self.wait("BEAT_5")

        # ── Final answer highlight ─────────────────────────────────────────────
        answer_box = SurroundingRectangle(step3, color=GOLD, buff=0.15)
        self.play(Create(answer_box))
        self.wait("BEAT_6")

        self.play(FadeOut(*self.mobjects))
        self.wait(0.5)
