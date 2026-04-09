"""Generate SVG charts for the README."""

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data" / "benchmarks.json"
CHARTS_DIR = ROOT / "assets"


def generate_timeline_svg(benchmarks):
    """Bar chart: benchmarks published per quarter."""
    quarters = Counter()
    for b in benchmarks:
        pub = b.get("published", "")
        if len(pub) >= 7:
            year = pub[:4]
            month = int(pub[5:7])
            q = (month - 1) // 3 + 1
            quarters[f"{year} Q{q}"] += 1

    # Filter to 2023+
    items = [(k, v) for k, v in sorted(quarters.items()) if k >= "2023"]
    if not items:
        return

    max_val = max(v for _, v in items)
    bar_w = 36
    gap = 4
    chart_w = len(items) * (bar_w + gap) + 60
    chart_h = 220
    bar_area_h = 160
    top_pad = 20
    bottom_pad = 40

    bars = []
    labels = []
    for i, (label, count) in enumerate(items):
        x = 50 + i * (bar_w + gap)
        h = (count / max_val) * bar_area_h
        y = top_pad + bar_area_h - h

        bars.append(
            f'<rect x="{x}" y="{y}" width="{bar_w}" height="{h}" '
            f'fill="#6366f1" rx="3"/>'
        )
        bars.append(
            f'<text x="{x + bar_w/2}" y="{y - 5}" text-anchor="middle" '
            f'font-size="10" fill="#64748b">{count}</text>'
        )
        # Label every other quarter to avoid crowding
        if i % 2 == 0 or i == len(items) - 1:
            labels.append(
                f'<text x="{x + bar_w/2}" y="{top_pad + bar_area_h + 16}" '
                f'text-anchor="middle" font-size="9" fill="#64748b" '
                f'transform="rotate(-45 {x + bar_w/2} {top_pad + bar_area_h + 16})">'
                f'{label}</text>'
            )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {chart_w} {chart_h}" width="{chart_w}" height="{chart_h}">
  <style>text {{ font-family: -apple-system, sans-serif; }}</style>
  <text x="{chart_w/2}" y="14" text-anchor="middle" font-size="13" font-weight="600" fill="#1e293b">New VLM Benchmarks by Quarter</text>
  <line x1="50" y1="{top_pad + bar_area_h}" x2="{chart_w - 10}" y2="{top_pad + bar_area_h}" stroke="#e2e8f0" stroke-width="1"/>
  {"".join(bars)}
  {"".join(labels)}
</svg>"""

    CHARTS_DIR.mkdir(exist_ok=True)
    (CHARTS_DIR / "timeline.svg").write_text(svg)
    print(f"Generated timeline.svg")


def generate_category_svg(benchmarks):
    """Horizontal bar chart: top categories."""
    cats = Counter(b.get("category", "other") for b in benchmarks)
    # Top 15, exclude "other"
    items = [(k, v) for k, v in cats.most_common() if k != "other"][:15]

    labels_map = {
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
    }

    max_val = max(v for _, v in items)
    row_h = 24
    label_w = 160
    bar_max_w = 300
    chart_w = label_w + bar_max_w + 60
    chart_h = len(items) * row_h + 40

    rows = []
    for i, (cat, count) in enumerate(items):
        y = 30 + i * row_h
        w = (count / max_val) * bar_max_w
        label = labels_map.get(cat, cat)

        rows.append(
            f'<text x="{label_w - 8}" y="{y + 14}" text-anchor="end" '
            f'font-size="11" fill="#475569">{label}</text>'
        )
        rows.append(
            f'<rect x="{label_w}" y="{y + 2}" width="{w}" height="{row_h - 6}" '
            f'fill="#6366f1" rx="3"/>'
        )
        rows.append(
            f'<text x="{label_w + w + 6}" y="{y + 14}" '
            f'font-size="10" fill="#64748b">{count}</text>'
        )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {chart_w} {chart_h}" width="{chart_w}" height="{chart_h}">
  <style>text {{ font-family: -apple-system, sans-serif; }}</style>
  <text x="{chart_w/2}" y="18" text-anchor="middle" font-size="13" font-weight="600" fill="#1e293b">Benchmarks by Category</text>
  {"".join(rows)}
</svg>"""

    CHARTS_DIR.mkdir(exist_ok=True)
    (CHARTS_DIR / "categories.svg").write_text(svg)
    print(f"Generated categories.svg")


def main():
    benchmarks = json.loads(DATA.read_text())
    generate_timeline_svg(benchmarks)
    generate_category_svg(benchmarks)


if __name__ == "__main__":
    main()
