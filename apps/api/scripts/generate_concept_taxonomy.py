"""
Generate concept_taxonomy.json from all *_concepts.py registries.

Run from apps/api/:
    python scripts/generate_concept_taxonomy.py

Output: apps/api/data/concept_taxonomy.json
Format:
    {
      "alg1": [{"id": "...", "label": "...", "description": "...", "course_id": "..."}],
      ...
    }
"""

import sys
import json
from pathlib import Path

# Ensure apps/api is on the path
API_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(API_DIR))

# Import all concept registries to populate the global CONCEPTS dict
import importlib, glob as _glob

_concept_files = sorted(_glob.glob(str(API_DIR / "*_concepts.py")))
for _path in _concept_files:
    _module_name = Path(_path).stem
    try:
        importlib.import_module(_module_name)
    except Exception as e:
        print(f"  WARN: could not import {_module_name}: {e}")

from concepts import CONCEPTS


def _normalise_label(name: str, description: str) -> str:
    """
    Produce a 3–6 word misconception label from a concept name + description.

    We derive the label by taking the description (which usually describes what
    students DO), trimming it to a short verb phrase, and lower-casing it.
    Falls back to concept name if description is too long or empty.
    """
    # Use description if it's short enough for a label
    desc = description.strip()
    words = desc.split()
    if 3 <= len(words) <= 8:
        # Trim to 6 words
        label = " ".join(words[:6]).rstrip(".,;:").lower()
    else:
        # Fall back to name
        label = name.lower()
    return label


def main() -> None:
    taxonomy: dict[str, list[dict]] = {}

    for concept_id, concept in CONCEPTS.items():
        course = concept.course_id or "unknown"
        if course not in taxonomy:
            taxonomy[course] = []

        label = _normalise_label(concept.name, concept.description)
        taxonomy[course].append(
            {
                "id": concept_id,
                "label": label,
                "name": concept.name,
                "description": concept.description,
                "course_id": course,
                "unit_id": concept.unit_id,
                "topic_id": concept.topic_id,
                "tags": concept.tags,
            }
        )

    # Sort within each course by id for stable output
    for course in taxonomy:
        taxonomy[course].sort(key=lambda c: c["id"])

    output_path = API_DIR / "data" / "concept_taxonomy.json"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(json.dumps(taxonomy, indent=2, ensure_ascii=True))

    total = sum(len(v) for v in taxonomy.values())
    print(f"[OK] Wrote {total} concepts across {len(taxonomy)} courses -> {output_path}")
    for course, items in sorted(taxonomy.items()):
        print(f"     {course}: {len(items)} concepts")


if __name__ == "__main__":
    main()
