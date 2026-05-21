"""
viz/probability_tree.py — Animated probability tree diagram.
"""
from __future__ import annotations
import numpy as np
from manim import *
from pipeline.viz.helpers import BRAND_CARAMEL, BRAND_GREEN


# Node: (label, probability_label)
# Tree described as a list of levels; each level is a list of nodes
# Edges automatically connect parent (index // 2 for binary) to children


class ProbabilityTreeScene(Scene):
    TITLE = "Probability Tree"

    # Each entry: (parent_index_in_prev_level, node_label, edge_label, color)
    # Level 0 is the root (just one node)
    ROOT_LABEL = "Start"
    LEVELS: list[list[tuple[int, str, str, str]]] = [
        # Level 1 — children of root (parent=0)
        [(0, "H", r"\tfrac{1}{2}", BRAND_CARAMEL), (0, "T", r"\tfrac{1}{2}", BRAND_GREEN)],
        # Level 2 — children of H (parent=0) and T (parent=1)
        [(0, "HH", r"\tfrac{1}{2}", BRAND_CARAMEL), (0, "HT", r"\tfrac{1}{2}", BRAND_GREEN),
         (1, "TH", r"\tfrac{1}{2}", BRAND_CARAMEL), (1, "TT", r"\tfrac{1}{2}", BRAND_GREEN)],
    ]
    # Final outcomes with probabilities (shown at right)
    OUTCOMES: list[tuple[str, str]] = [
        ("HH", r"\tfrac{1}{4}"), ("HT", r"\tfrac{1}{4}"),
        ("TH", r"\tfrac{1}{4}"), ("TT", r"\tfrac{1}{4}"),
    ]

    def construct(self):
        title = Text(self.TITLE, font_size=32)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait(1.0)

        self._draw_tree()

        self.play(FadeOut(*self.mobjects))
        self.wait(0.5)

    def _draw_tree(self):
        # Layout parameters
        x_start  = -4.5   # shifted right to centre the tree on canvas
        x_step   = 2.6
        node_r   = 0.28

        # Build positions per level
        all_positions: list[list[np.ndarray]] = []

        # Root
        root_pos = np.array([x_start, 0.0, 0])
        all_positions.append([root_pos])

        for lvl_idx, level in enumerate(self.LEVELS):
            # Collect unique parents
            parents = sorted(set(n[0] for n in level))
            # Space children evenly within vertical span
            n_nodes = len(level)
            total_height = min(3.5, 1.2 * n_nodes)
            ys = np.linspace(total_height / 2, -total_height / 2, n_nodes)
            x = x_start + x_step * (lvl_idx + 1)
            positions = [np.array([x, y, 0]) for y in ys]
            all_positions.append(positions)

        # Draw root node
        root_dot  = Circle(radius=node_r, color=WHITE, fill_color=WHITE,
                            fill_opacity=0.15, stroke_width=2)
        root_dot.move_to(root_pos)
        root_lbl  = Text(self.ROOT_LABEL, font_size=20).move_to(root_pos)
        self.play(Create(root_dot), Write(root_lbl))

        prev_nodes = [root_dot]
        prev_pos   = [root_pos]

        for lvl_idx, level in enumerate(self.LEVELS):
            cur_pos   = all_positions[lvl_idx + 1]
            cur_nodes = []

            anims_dots  = []
            anims_lbls  = []
            anims_edges = []
            anims_elbl  = []

            for node_idx, (parent_idx, node_label, edge_label, color) in enumerate(level):
                pos   = cur_pos[node_idx]
                p_pos = prev_pos[parent_idx]

                # Edge
                edge = Line(p_pos, pos, color=GRAY_C, stroke_width=1.5)
                anims_edges.append(Create(edge))

                # Edge probability label (use MathTex so LaTeX fractions render)
                mid = (p_pos + pos) / 2
                perp = np.array([-(pos - p_pos)[1], (pos - p_pos)[0], 0])
                norm = np.linalg.norm(perp)
                if norm > 0:
                    perp = perp / norm * 0.32
                e_lbl = MathTex(edge_label, font_size=20, color=color).move_to(mid + perp)
                anims_elbl.append(Write(e_lbl))

                # Node circle
                dot = Circle(radius=node_r, color=color, fill_color=color,
                              fill_opacity=0.15, stroke_width=2)
                dot.move_to(pos)
                anims_dots.append(Create(dot))

                # Node label
                n_lbl = Text(node_label, font_size=20, color=color).move_to(pos)
                anims_lbls.append(Write(n_lbl))
                cur_nodes.append(dot)

            self.play(*anims_edges, run_time=0.6)
            self.play(*anims_elbl, run_time=0.4)
            self.play(*anims_dots, *anims_lbls, run_time=0.5)
            self.wait(0.5)

            prev_pos   = cur_pos
            prev_nodes = cur_nodes

        # Outcomes column
        if self.OUTCOMES:
            x_out = all_positions[-1][0][0] + 1.8
            n = len(self.OUTCOMES)
            ys = np.linspace(1.8, -1.8, n) if n > 1 else [0.0]
            outcome_grp = VGroup()
            for i, (label, prob) in enumerate(self.OUTCOMES):
                y = ys[i] if n > 1 else 0.0
                lbl = MathTex(f"P = {prob}", font_size=24, color=YELLOW)
                lbl.move_to(np.array([x_out, y, 0]))
                outcome_grp.add(lbl)
            outcome_grp.scale_to_fit_height(min(outcome_grp.height, 6.5))
            self.play(Write(outcome_grp), run_time=0.8)

        self.wait(1.5)


if __name__ == "__main__":
    pass
