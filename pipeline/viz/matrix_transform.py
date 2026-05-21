"""
viz/matrix_transform.py — Matrix multiplication, row operations, and transformation display.
"""
from __future__ import annotations
import numpy as np
from manim import *
from pipeline.viz.helpers import BRAND_CARAMEL, BRAND_GREEN


class MatrixTransformScene(Scene):
    TITLE = "Matrix Multiplication"
    MODE  = "multiply"   # "multiply" | "row_ops" | "inverse"

    # For MODE="multiply": A @ B = C
    MATRIX_A = [[1, 2], [3, 4]]
    MATRIX_B = [[5, 6], [7, 8]]

    # For MODE="row_ops"
    AUGMENTED = [[2, 1, 5], [4, -1, 3]]
    ROW_OPS   = [r"R_2 \leftarrow R_2 - 2R_1"]

    def construct(self):
        title = Text(self.TITLE, font_size=32)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait(1.0)

        if self.MODE == "multiply":
            self._multiply()
        elif self.MODE == "row_ops":
            self._row_ops()
        elif self.MODE == "inverse":
            self._inverse()

        self.play(FadeOut(*self.mobjects))
        self.wait(0.5)

    # ------------------------------------------------------------------ #
    def _multiply(self):
        A = np.array(self.MATRIX_A)
        B = np.array(self.MATRIX_B)
        C = A @ B

        mat_a = Matrix(self.MATRIX_A, h_buff=1.2, v_buff=0.9)
        mat_b = Matrix(self.MATRIX_B, h_buff=1.2, v_buff=0.9)
        result = Matrix(C.tolist(), h_buff=1.2, v_buff=0.9)

        times = MathTex(r"\times", font_size=40)
        eq    = MathTex(r"=",      font_size=40)

        row = VGroup(mat_a, times, mat_b, eq, result)
        row.arrange(RIGHT, buff=0.5)
        row.scale_to_fit_width(min(row.width, 12.5))
        row.move_to(UP * 0.3)

        mat_a.set_color(BRAND_CARAMEL)
        mat_b.set_color(BRAND_GREEN)
        result.set_color(YELLOW)

        self.play(Write(mat_a), Write(mat_b))
        self.wait(0.8)
        self.play(Write(times), Write(eq))
        self.wait(0.3)

        # Highlight each output cell with its row × column source
        entries_a = mat_a.get_entries()
        entries_b = mat_b.get_entries()
        entries_c = []

        rows_a, cols_a = A.shape
        rows_b, cols_b = B.shape

        for i in range(rows_a):
            for j in range(cols_b):
                row_elems = VGroup(*[entries_a[i * cols_a + k] for k in range(cols_a)])
                col_elems = VGroup(*[entries_b[k * cols_b + j] for k in range(rows_b)])

                self.play(
                    row_elems.animate.set_color(YELLOW),
                    col_elems.animate.set_color(YELLOW),
                    run_time=0.4,
                )
                val = MathTex(str(int(C[i, j])), font_size=36, color=YELLOW)
                val.move_to(result.get_entries()[i * cols_b + j])
                entries_c.append(val)
                self.play(FadeIn(val, scale=1.3), run_time=0.35)
                self.play(
                    row_elems.animate.set_color(BRAND_CARAMEL),
                    col_elems.animate.set_color(BRAND_GREEN),
                    run_time=0.2,
                )

        # Show the completed result matrix brackets
        self.play(Write(result.get_brackets()))
        self.wait(1.5)

    # ------------------------------------------------------------------ #
    def _row_ops(self):
        rows = [list(map(str, r)) for r in self.AUGMENTED]
        mat  = Matrix(rows, h_buff=1.1, v_buff=0.9)
        mat.scale_to_fit_width(min(mat.width, 9.5))
        mat.move_to(UP * 0.5)

        self.play(Write(mat))
        self.wait(0.8)

        for i, op_tex in enumerate(self.ROW_OPS):
            op_lbl = MathTex(op_tex, font_size=30, color=BRAND_CARAMEL)
            op_lbl.to_edge(RIGHT, buff=0.5).shift(UP * (0.8 - i * 0.7))
            arrow = Arrow(op_lbl.get_left(), mat.get_right() + RIGHT * 0.1,
                          color=BRAND_CARAMEL, stroke_width=2, buff=0.15, tip_length=0.18)
            self.play(Write(op_lbl), Create(arrow))
            self.wait(1.0)

        self.wait(1.0)

    # ------------------------------------------------------------------ #
    def _inverse(self):
        A = np.array(self.MATRIX_A, dtype=float)
        try:
            inv = np.linalg.inv(A)
            inv_rows = [[f"{v:.2f}".rstrip('0').rstrip('.') for v in r] for r in inv]
        except np.linalg.LinAlgError:
            inv_rows = [["∞", "∞"], ["∞", "∞"]]

        mat_a   = Matrix(self.MATRIX_A, h_buff=1.2, v_buff=0.9)
        inv_mat = Matrix(inv_rows,       h_buff=1.4, v_buff=0.9)
        sup     = MathTex(r"^{-1}", font_size=36)
        eq      = MathTex(r"=",    font_size=40)

        sup.next_to(mat_a, UR, buff=0.05).shift(DOWN * 0.1)
        row = VGroup(VGroup(mat_a, sup), eq, inv_mat)
        row.arrange(RIGHT, buff=0.5)
        row.scale_to_fit_width(min(row.width, 11))
        row.move_to(ORIGIN)

        mat_a.set_color(BRAND_CARAMEL)
        inv_mat.set_color(YELLOW)

        self.play(Write(mat_a), Write(sup))
        self.wait(0.8)
        self.play(Write(eq), Write(inv_mat))
        self.wait(1.5)


if __name__ == "__main__":
    pass
