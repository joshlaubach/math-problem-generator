"""
pipeline/stages — The 6 pipeline stages.

Each module exposes a single run() function.
"""
from pipeline.stages import s1_plan, s2_generate, s3_correct, s4_render, s5_audio, s6_assemble

__all__ = ["s1_plan", "s2_generate", "s3_correct", "s4_render", "s5_audio", "s6_assemble"]
