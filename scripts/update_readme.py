"""Regenerate README stats from benchmarks.json."""

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data" / "benchmarks.json"
README = ROOT / "README.md"

CATEGORY_LABELS = {
    "general_multimodal": "General Multimodal",
    "visual_reasoning": "Visual Reasoning",
    "video_understanding": "Video Understanding",
    "medical": "Medical",
    "safety_bias": "Safety & Bias",
    "egocentric_embodied": "Egocentric & Embodied",
    "spatial_3d": "Spatial & 3D",
    "math_science": "Math & Science",
    "document_ocr": "Document & OCR",
    "gui_web_agent": "GUI & Web Agents",
    "audio_visual": "Audio-Visual",
    "geospatial": "Geospatial",
    "hallucination": "Hallucination",
    "temporal_reasoning": "Temporal Reasoning",
    "grounding_localization": "Grounding & Localization",
    "chart_figure": "Chart & Figure",
    "long_video": "Long Video",
    "quality_aesthetics": "Quality & Aesthetics",
    "multi_image": "Multi-Image",
    "video_hallucination": "Video Hallucination",
    "streaming_video": "Streaming Video",
    "other": "Other",
}


def main():
    benchmarks = json.loads(DATA.read_text())
    total = len(benchmarks)
    cats = Counter(b.get("category", "other") for b in benchmarks)

    # Build table rows sorted by count
    rows = []
    for cat, count in cats.most_common():
        label = CATEGORY_LABELS.get(cat, cat)
        rows.append(f"| {label} | {count} |")
    table = "\n".join(rows)

    readme = README.read_text()

    # Update total count in first line
    import re
    readme = re.sub(
        r'\*\*[\d,]+ benchmarks\*\*',
        f'**{total:,} benchmarks**',
        readme,
    )

    # Update category table
    start = readme.index("| Category | Count |")
    end = readme.index("\n\n", start)
    new_table = f"| Category | Count |\n|----------|-------|\n{table}"
    readme = readme[:start] + new_table + readme[end:]

    README.write_text(readme)
    print(f"README updated: {total} benchmarks, {len(cats)} categories")


if __name__ == "__main__":
    main()
