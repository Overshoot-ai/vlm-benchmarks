"""Generate hand-drawn style charts for the README using xkcd mode."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data" / "benchmarks.json"
ASSETS = ROOT / "assets"

bg_color = '#FFFEF2'
text_dark = '#2C2C2C'
text_mid = '#666666'

pastel_colors = [
    '#FF6B6B', '#FFA07A', '#FFD93D', '#6BCB77', '#4D96FF',
    '#9B59B6', '#FF85A1', '#FFC75F', '#45B7D1', '#96CEB4',
    '#D4A574', '#A8E6CF', '#FFB7B2', '#B5EAD7', '#C7CEEA',
    '#E2B0FF', '#FFDAC1', '#FF9AA2', '#B5B8FF', '#AED9E0',
    '#FFC8DD', '#BDB2FF',
]

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


def generate_dotstrip(benchmarks):
    """Dot strip chart: benchmarks by size tier."""
    cats = Counter(b.get("category", "other") for b in benchmarks)
    categories = [(CATEGORY_LABELS.get(k, k), v) for k, v in cats.items()]

    tiers = {
        'Huge (200+)': [(c, v) for c, v in categories if v >= 200],
        'Large (100-199)': [(c, v) for c, v in categories if 100 <= v < 200],
        'Medium (50-99)': [(c, v) for c, v in categories if 50 <= v < 100],
        'Small (<50)': [(c, v) for c, v in categories if v < 50],
    }

    tier_colors = ['#FF6B6B', '#FFD93D', '#4D96FF', '#6BCB77']

    with plt.xkcd(scale=1.2, length=100, randomness=2):
        fig, ax = plt.subplots(figsize=(14, 8), facecolor=bg_color)
        ax.set_facecolor(bg_color)

        for i, (tier, items) in enumerate(tiers.items()):
            for j, (name, val) in enumerate(sorted(items, key=lambda x: -x[1])):
                jitter = (j - len(items) / 2) * 0.08
                ax.scatter(val, i + jitter, s=val * 1.2 + 30,
                           c=tier_colors[i], edgecolors=text_dark, linewidth=1,
                           alpha=0.8, zorder=5)
                if val > 40:
                    ax.text(val, i + jitter + 0.12, name, fontsize=7,
                            ha='center', va='bottom', color=text_dark, rotation=15)

        ax.set_yticks(range(len(tiers)))
        ax.set_yticklabels(list(tiers.keys()), fontsize=11, color=text_dark)
        ax.set_xlabel('Benchmark Count', fontsize=12, color=text_mid)
        ax.set_title('Benchmarks by Size Tier (dot size = count)', fontsize=18,
                     color=text_dark, pad=20)

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_ylim(-0.5, len(tiers) - 0.3)

        plt.tight_layout()
        ASSETS.mkdir(exist_ok=True)
        fig.savefig(ASSETS / "categories.png", dpi=200, bbox_inches='tight', facecolor=bg_color)
        plt.close()

    print("Generated categories.png (dotstrip)")


def generate_timeline(benchmarks):
    """Bar chart: benchmarks per quarter, hand-drawn style."""
    quarters = Counter()
    for b in benchmarks:
        pub = b.get("published", "")
        if len(pub) >= 7:
            year = pub[:4]
            month = int(pub[5:7])
            q = (month - 1) // 3 + 1
            quarters[f"{year} Q{q}"] += 1

    items = [(k, v) for k, v in sorted(quarters.items()) if k >= "2023"]

    labels = [k for k, _ in items]
    vals = [v for _, v in items]
    colors = [pastel_colors[i % len(pastel_colors)] for i in range(len(items))]

    with plt.xkcd(scale=1.5, length=120, randomness=3):
        fig, ax = plt.subplots(figsize=(16, 8), facecolor=bg_color)
        ax.set_facecolor(bg_color)

        x_pos = range(len(labels))
        ax.bar(list(x_pos), vals, color=colors, edgecolor=text_dark, linewidth=1.2, width=0.7)

        for x, v in zip(x_pos, vals):
            ax.text(x, v + 5, str(v), ha='center', va='bottom',
                    fontsize=10, color=text_dark, fontweight='bold')

        ax.set_xticks(list(x_pos))
        ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=9, color=text_dark)
        ax.set_ylabel('Number of Benchmarks', fontsize=12, color=text_mid)
        ax.set_title('New VLM Benchmarks by Quarter', fontsize=18, color=text_dark, pad=20)

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        # Annotate the peak
        peak_idx = vals.index(max(vals))
        ax.annotate(f'Peak: {vals[peak_idx]}!',
                    xy=(peak_idx, vals[peak_idx]),
                    xytext=(peak_idx - 2, vals[peak_idx] + 40),
                    fontsize=12, fontweight='bold', color='#FF6B6B',
                    arrowprops=dict(arrowstyle='->', color='#FF6B6B', lw=2))

        plt.tight_layout()
        ASSETS.mkdir(exist_ok=True)
        fig.savefig(ASSETS / "timeline.png", dpi=200, bbox_inches='tight', facecolor=bg_color)
        plt.close()

    print("Generated timeline.png (bar chart)")


def main():
    benchmarks = json.loads(DATA.read_text())
    print(f"Loaded {len(benchmarks)} benchmarks")
    generate_dotstrip(benchmarks)
    generate_timeline(benchmarks)


if __name__ == "__main__":
    main()
