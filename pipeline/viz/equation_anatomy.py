"""
viz/equation_anatomy.py — Labels parts of a formula with braces.
"""
from __future__ import annotations
from manim import *
from pipeline.viz.helpers import BRAND_CARAMEL, BRAND_GREEN


class EquationAnatomyScene(Scene):
    TITLE      = "Anatomy of the Equation"
    EQUATION   = r"y = mx + b"
    # EQUATION_TOKENS — split into separate MathTex args for exact part selection.
    # Each labeled part must be a distinct token in this list.
    EQUATION_TOKENS = [r"y", r"=", r"m", r"x", r"+", r"b"]
    PARTS: list[tuple[str, str, str, str]] = [
        # (tex_token_to_match, label_text, brace_direction, color)
        # Tip: label only well-separated parts to avoid overlap.
        ("m", "slope",       "UP",   "#4a90d9"),
        ("b", "y-intercept", "DOWN", "#c4976a"),
    ]

    def construct(self):
        title = Text(self.TITLE, font_size=32)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait(1.0)

        # Build MathTex with each token as a separate arg so indexing is exact
        # EQUATION is split into tokens at spaces; override by setting EQUATION_TOKENS
        tokens = getattr(self, "EQUATION_TOKENS", self.EQUATION.split())
        eq = MathTex(*tokens, font_size=52)
        eq.scale_to_fit_width(min(eq.width, 9))
        eq.move_to(UP * 0.5)
        self.play(Write(eq))
        self.wait(1.0)

        DIR_MAP = {"UP": UP, "DOWN": DOWN, "LEFT": LEFT, "RIGHT": RIGHT}

        for tex_part, label_text, direction_str, color in self.PARTS:
            direction = DIR_MAP.get(direction_str, DOWN)

            # Find the submobject(s) whose source contains tex_part
            matched = eq.get_parts_by_tex(tex_part)
            if not matched:
                continue

            # Use the first match; if multiple, wrap in VGroup
            part = matched[0] if len(matched) == 1 else VGroup(*matched)
            part.set_color(color)

            brace = Brace(part, direction=direction, buff=0.08, color=color)
            lbl = Text(label_text, font_size=24, color=color)
            brace.put_at_tip(lbl, buff=0.12)

            self.play(Create(brace), Write(lbl))
            self.wait(1.2)

        self.wait(1.5)
        self.play(FadeOut(*self.mobjects))
        self.wait(0.5)


if __name__ == "__main__":
    pass
