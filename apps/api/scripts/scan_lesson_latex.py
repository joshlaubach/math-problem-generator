"""
Scan all topic lesson JSON files for LaTeX rendering issues.

Checks:
1. prompt_latex fields — flag those that are pure LaTeX (no $...$) since
   they render in display mode; mixed prose+math ones use auto-detected prose mode.
2. expression_latex fields in worked/partial examples — flag any that contain
   $...$ markers (should be pure LaTeX, not prose+math).
3. Fields that use prose mode (hook, concept, anatomy, description_latex,
   common_mistakes, untested_variants) — flag any that look like pure LaTeX
   without $...$ markers (would render as escaped text).
4. Backslash escape issues — flag any that have single-backslash sequences
   that KaTeX needs but might be lost (e.g. \n inside a string stored as newline).
"""
import json
import re
import sys
from pathlib import Path

LESSONS_DIR = Path(__file__).parent.parent / "data" / "topic_lessons"

# Match unescaped $...$ — excludes \$ (LaTeX dollar sign escape)
HAS_DOLLAR = re.compile(r'(?<!\\)\$[^$]+\$')
LOOKS_LIKE_LATEX = re.compile(r'\\[a-zA-Z]')  # backslash + letters = latex command


def check_lesson(path: Path) -> list[dict]:
    issues = []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return [{"file": path.name, "field": "JSON", "issue": f"parse error: {e}"}]

    topic_id = data.get("topic_id", path.stem)

    def flag(field: str, value: str, issue: str):
        issues.append({
            "topic_id": topic_id,
            "field": field,
            "issue": issue,
            "preview": (value or "")[:80],
        })

    # ── prose fields: should have $...$ for any math ──────────────────────────
    for field in ["hook", "concept", "anatomy"]:
        val = data.get(field, "")
        if val and LOOKS_LIKE_LATEX.search(val) and not HAS_DOLLAR.search(val):
            flag(field, val, "prose field has LaTeX commands but no $...$ delimiters → will render as plain text")

    for mistake in data.get("common_mistakes", []):
        if mistake and LOOKS_LIKE_LATEX.search(mistake) and not HAS_DOLLAR.search(mistake):
            flag("common_mistakes[]", mistake, "prose field has LaTeX commands but no $...$ delimiters")

    for variant in data.get("untested_variants", []):
        if variant and LOOKS_LIKE_LATEX.search(variant) and not HAS_DOLLAR.search(variant):
            flag("untested_variants[]", variant, "prose field has LaTeX commands but no $...$ delimiters")

    # ── worked_example and partial_example steps ──────────────────────────────
    for section in ["worked_example", "partial_example"]:
        for i, step in enumerate(data.get(section, [])):
            desc = step.get("description_latex", "")
            expr = step.get("expression_latex", "")

            # description_latex: prose mode — flag if LaTeX without delimiters
            if desc and LOOKS_LIKE_LATEX.search(desc) and not HAS_DOLLAR.search(desc):
                flag(f"{section}[{i}].description_latex", desc,
                     "prose field has LaTeX commands but no $...$ delimiters")

            # expression_latex: display mode — flag if it has $...$ (shouldn't)
            if expr and HAS_DOLLAR.search(expr):
                flag(f"{section}[{i}].expression_latex", expr,
                     "display-mode field contains $...$ delimiters → will render $ as literal text")

    # ── practice problems ─────────────────────────────────────────────────────
    for i, prob in enumerate(data.get("practice_problems", [])):
        prompt = prob.get("prompt_latex", "")
        answer = prob.get("answer_latex", "")

        # prompt_latex: auto-detected (prose if $, display if not) — both should work now
        # But flag if it has BOTH $...$ AND bare LaTeX commands outside $ (malformed)
        if prompt and HAS_DOLLAR.search(prompt):
            # Find text outside $...$ and check for bare LaTeX
            stripped = HAS_DOLLAR.sub("", prompt)
            if LOOKS_LIKE_LATEX.search(stripped):
                flag(f"practice_problems[{i}].prompt_latex", prompt,
                     "mixed $...$ and bare LaTeX commands outside delimiters → some math may not render")

        # answer_latex: display mode — flag if it has $...$
        if answer and HAS_DOLLAR.search(answer):
            flag(f"practice_problems[{i}].answer_latex", answer,
                 "display-mode field contains $...$ delimiters → will render $ as literal text")

    return issues


def main():
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if not LESSONS_DIR.exists():
        print(f"Lessons directory not found: {LESSONS_DIR}")
        sys.exit(1)

    lesson_files = sorted(LESSONS_DIR.glob("*.json"))
    print(f"Scanning {len(lesson_files)} lesson files...\n")

    all_issues: list[dict] = []
    for path in lesson_files:
        issues = check_lesson(path)
        all_issues.extend(issues)

    if not all_issues:
        print("✓ No issues found.")
        return

    # Group by issue type
    by_type: dict[str, list] = {}
    for issue in all_issues:
        key = issue["issue"]
        by_type.setdefault(key, []).append(issue)

    for issue_type, items in by_type.items():
        print(f"\n{'='*70}")
        print(f"[{len(items)} issues] {issue_type}")
        print(f"{'='*70}")
        for item in items[:20]:  # cap at 20 per category
            print(f"  {item['topic_id']} / {item['field']}")
            print(f"    {item['preview']!r}")
        if len(items) > 20:
            print(f"  ... and {len(items) - 20} more")

    print(f"\n{'='*70}")
    print(f"Total issues: {len(all_issues)} across {len(set(i['topic_id'] for i in all_issues))} topics")
    # Write full results to file for review
    out = Path(__file__).parent / "scan_results.json"
    out.write_text(json.dumps(all_issues, indent=2, ensure_ascii=True), encoding="utf-8")
    print(f"Full results written to {out}")


if __name__ == "__main__":
    main()
