"""
viz/helpers.py — reusable Manim geometry utilities shared across visualization types.
"""
from __future__ import annotations
from manim import *


# ── Brand colors ──────────────────────────────────────────────────────────────

BRAND_CARAMEL = ManimColor("#c4976a")
BRAND_GREEN   = ManimColor("#2d6a4f")
BRAND_CREAM   = ManimColor("#fefcf9")


# ── Color-code parts of a MathTex ────────────────────────────────────────────

def color_tex_parts(mathtex: MathTex, part_colors: dict[str, str]) -> None:
    """Color named substrings of a MathTex object in-place."""
    for part, color in part_colors.items():
        try:
            mathtex.set_color_by_tex(part, color)
        except Exception:
            pass


# ── Safe-scaled MathTex factory ───────────────────────────────────────────────

def safe_tex(latex: str, max_width: float = 10.0, **kwargs) -> MathTex:
    """Create a MathTex that never exceeds max_width Manim units."""
    obj = MathTex(latex, **kwargs)
    if obj.width > max_width:
        obj.scale_to_fit_width(max_width)
    return obj


def safe_text(text: str, max_width: float = 11.0, font_size: int = 28, **kwargs) -> Text:
    """Create a Text object that never exceeds max_width Manim units."""
    obj = Text(text, font_size=font_size, **kwargs)
    if obj.width > max_width:
        obj.scale_to_fit_width(max_width)
    return obj


# ── Right triangle ────────────────────────────────────────────────────────────

def make_right_triangle(
    theta_deg: float = 30,
    leg_h: float = 2.0,
    hyp_color: str | ManimColor = GOLD,
    opp_color: str | ManimColor = BLUE,
    adj_color: str | ManimColor = GREEN,
    show_right_angle: bool = True,
) -> VGroup:
    """
    Return a labeled right triangle VGroup.
    The right angle is at the origin; adjacent leg goes right, opposite goes up.
    """
    import math
    theta_rad = math.radians(theta_deg)
    adj_len = leg_h / math.tan(theta_rad)
    hyp_len = leg_h / math.sin(theta_rad)

    A = np.array([0, 0, 0])            # right angle
    B = np.array([adj_len, 0, 0])      # base right
    C = np.array([0, leg_h, 0])        # top

    adj_line = Line(A, B, color=adj_color, stroke_width=4)
    opp_line = Line(A, C, color=opp_color, stroke_width=4)
    hyp_line = Line(B, C, color=hyp_color, stroke_width=4)

    group = VGroup(adj_line, opp_line, hyp_line)

    if show_right_angle:
        sq_size = 0.18
        right_sq = Polygon(
            A,
            A + RIGHT * sq_size,
            A + RIGHT * sq_size + UP * sq_size,
            A + UP * sq_size,
            color=WHITE, stroke_width=2,
        )
        group.add(right_sq)

    # Angle arc at B (the theta angle)
    angle_arc = Arc(
        radius=0.35,
        start_angle=PI - math.atan2(leg_h, adj_len),
        angle=math.atan2(leg_h, adj_len),
        arc_center=B,
        color=YELLOW,
    )
    theta_label = MathTex(r"\theta", font_size=24, color=YELLOW)
    theta_label.next_to(angle_arc, LEFT, buff=0.05)
    group.add(angle_arc, theta_label)

    return group


# ── Unit circle base ──────────────────────────────────────────────────────────

def make_unit_circle_base(radius: float = 2.2) -> VGroup:
    """
    Return the base unit circle: circle + axes + tick marks.
    Does NOT include the moving dot — add that in the scene.
    """
    axes = Axes(
        x_range=[-1.4, 1.4, 0.5],
        y_range=[-1.4, 1.4, 0.5],
        x_length=radius * 2 * 1.3,
        y_length=radius * 2 * 1.3,
        axis_config={"include_tip": True, "tip_length": 0.15, "stroke_width": 2},
        tips=False,
    )
    circle = Circle(radius=radius, color=WHITE, stroke_width=2)
    return VGroup(axes, circle)


# ── Standard axes ─────────────────────────────────────────────────────────────

def make_axes(
    x_range: list = [-5, 5, 1],
    y_range: list = [-4, 4, 1],
    x_length: float = 10,
    y_length: float = 6,
    color: str | ManimColor = WHITE,
) -> Axes:
    return Axes(
        x_range=x_range,
        y_range=y_range,
        x_length=x_length,
        y_length=y_length,
        axis_config={
            "include_tip": True,
            "tip_length": 0.2,
            "stroke_width": 2,
            "color": color,
        },
    )


# ── Brace label helper ────────────────────────────────────────────────────────

def labeled_brace(
    obj: Mobject,
    label_text: str,
    direction: np.ndarray = DOWN,
    font_size: int = 24,
    color: str | ManimColor = WHITE,
    buff: float = 0.1,
) -> VGroup:
    """Return a VGroup of (Brace, label) for a given mobject."""
    brace = Brace(obj, direction=direction, buff=buff, color=color)
    label = brace.get_text(label_text, font_size=font_size)
    label.set_color(color)
    return VGroup(brace, label)
