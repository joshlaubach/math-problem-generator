"""
Lesson Writer agent — offline only, never called during student sessions.

Called by: apps/api/scripts/lesson_writer_run.py (Phase 11)

Generates MDX lesson content for a given (course, unit) pair:
  - Prose explanation of the unit concept
  - 2-3 worked examples in KaTeX display math
  - Key formulas in display math with labels
  - "Common mistakes" section
  - "Connections" section linking to adjacent topics
  - <VideoLinks /> component reference (fetches from video_links table)

Writes to: content/[course-slug]/[unit-slug]/notes.mdx
"""

from __future__ import annotations

from pathlib import Path


async def write_lesson(
    course_slug: str,
    unit_slug: str,
    unit_title: str,
    topics: list[dict],
    honors_topics: list[dict],
    special_topics: list[dict],
    output_dir: Path,
) -> Path:
    """
    Generate MDX lesson content and write to disk.

    Args:
        course_slug: URL-safe course identifier (e.g. 'algebra-1')
        unit_slug: URL-safe unit identifier (e.g. 'unit-01-real-numbers')
        unit_title: Human-readable unit title
        topics: list of topic dicts for this unit
        honors_topics: list of honors-flagged topic dicts
        special_topics: list of special-flagged topic dicts
        output_dir: Root content directory (e.g. Path('content/'))

    Returns:
        Path to the written MDX file.

    Phase 11: implement using Claude (claude-sonnet-4-6) with house-style prompt prefix
    from apps/api/prompts/lesson_style.md.
    """
    raise NotImplementedError(
        "lesson_writer.write_lesson — implement in Phase 11"
    )
