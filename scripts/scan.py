"""
Daily scanner: queries arXiv for new VLM benchmark papers,
classifies them, extracts repo links, appends to data/benchmarks.json,
and syncs new entries to Supabase.
"""

import arxiv
import anthropic
import csv
import json
import os
import re
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
BENCHMARKS_FILE = DATA_DIR / "benchmarks.json"
SEEN_FILE = DATA_DIR / "seen_ids.json"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://xffdlyzkioroekuzpocg.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")

QUERIES = [
    'ti:"benchmark" AND abs:("vision language model" OR "VLM")',
    'ti:"benchmark" AND abs:("multimodal large language model" OR "MLLM")',
    'ti:"benchmark" AND abs:("video language model" OR "video LLM")',
    'ti:"benchmark" AND abs:("video understanding")',
    'ti:"benchmark" AND abs:("visual question answering")',
    'ti:"benchmark" AND abs:("multimodal" AND "evaluation")',
    'ti:"evaluation" AND abs:("vision language model" OR "VLM" OR "MLLM")',
    'ti:"evaluation" AND abs:("video understanding" OR "video language")',
    'ti:"benchmark" AND abs:("visual reasoning")',
    'ti:"benchmark" AND abs:("video hallucination")',
    'ti:"benchmark" AND abs:("temporal reasoning" AND "video")',
    'ti:"benchmark" AND abs:("long video")',
    'ti:"benchmark" AND abs:("streaming video")',
    'ti:"benchmark" AND abs:("medical" AND ("VLM" OR "multimodal" OR "vision language"))',
    'ti:"benchmark" AND abs:("spatial reasoning" AND "multimodal")',
    'ti:"benchmark" AND abs:("hallucination" AND ("VLM" OR "MLLM" OR "multimodal"))',
    'abs:("vision language model" AND "benchmark" AND "evaluation")',
    'abs:("video understanding benchmark")',
    'abs:("multimodal benchmark" AND "vision" AND "language")',
]

URL_PATTERN = re.compile(
    r'https?://(?:github\.com|huggingface\.co|hf\.co|gitlab\.com)/[^\s\)\]>\"\'}{,]+',
    re.IGNORECASE,
)
JUNK = [
    'huggingface.co/huggingface', 'huggingface.co/docs', 'huggingface.co/join',
    'huggingface.co/papers', 'huggingface.co/spaces', 'github.com/arxiv',
    'github.com/features', 'github.com/pricing', 'github.com/login', 'github.com/signup',
]

CLASSIFY_PROMPT = """You will receive arXiv papers. For each, determine if it introduces a NEW benchmark/dataset for evaluating VLMs/MLLMs/Video-LLMs. The benchmark must be the PRIMARY contribution and must require VISUAL input (images, video, etc.).

Answer NO if: the paper just proposes a model, is a survey, is text-only/audio-only, or the benchmark doesn't require visual input.

Also extract any URLs from the abstract that point to the benchmark's project page, code, or dataset.

For each paper, respond with JSON:
- "arxiv_id": echo back
- "is_benchmark": true/false
- "benchmark_name": name or null
- "category": one of ["general_multimodal", "video_understanding", "long_video", "streaming_video", "temporal_reasoning", "video_hallucination", "document_ocr", "chart_figure", "math_science", "hallucination", "spatial_3d", "medical", "safety_bias", "visual_reasoning", "egocentric_embodied", "grounding_localization", "audio_visual", "gui_web_agent", "geospatial", "quality_aesthetics", "multi_image", "other"]
- "num_samples": from abstract if mentioned, else null
- "description": 2-3 sentence summary of what makes it unique
- "task_types": list if mentioned, else null
- "modalities": list, else null
- "urls": list of project/repo/data URLs found in abstract, else []

Return ONLY a JSON array."""


def extract_urls(text):
    if not text:
        return []
    urls = URL_PATTERN.findall(text)
    return [u.rstrip(".,;:!?)") for u in dict.fromkeys(urls) if not any(j in u for j in JUNK)]


def load_seen():
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    # Bootstrap from existing benchmarks.json so we never re-add old papers
    if BENCHMARKS_FILE.exists():
        existing = json.loads(BENCHMARKS_FILE.read_text())
        return {b["arxiv_id"] for b in existing}
    return set()


def save_seen(ids):
    SEEN_FILE.write_text(json.dumps(sorted(ids)))


def fetch_papers(seen):
    client = arxiv.Client(page_size=50, delay_seconds=5.0, num_retries=5)
    papers = []
    new_ids = set()
    cutoff = datetime.now(timezone.utc) - timedelta(days=5)

    for query in QUERIES:
        search = arxiv.Search(query=query, max_results=50, sort_by=arxiv.SortCriterion.SubmittedDate)
        try:
            for r in client.results(search):
                # Skip papers older than 5 days
                if r.published < cutoff:
                    break

                aid = r.entry_id.split("/abs/")[-1].split("v")[0]
                if aid in seen or aid in new_ids:
                    continue
                new_ids.add(aid)

                urls = extract_urls(r.summary or "") + extract_urls(r.comment or "")
                for link in r.links:
                    urls.extend(extract_urls(link.href))

                papers.append({
                    "arxiv_id": aid,
                    "title": r.title,
                    "abstract": r.summary,
                    "authors": [a.name for a in r.authors[:5]],
                    "published": r.published.isoformat()[:10],
                    "url": r.entry_id,
                    "repo_links": list(dict.fromkeys(urls)),
                })
        except Exception as e:
            print(f"Query error: {e}")

    return papers


def classify(papers):
    if not papers:
        return []

    client = anthropic.Anthropic()
    benchmarks = []

    for i in range(0, len(papers), 25):
        batch = papers[i:i+25]
        lines = [
            f"[{j+1}] arxiv_id: {p['arxiv_id']}\n    Title: {p['title']}\n    Abstract: {p['abstract']}\n"
            for j, p in enumerate(batch)
        ]

        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8192,
                system=CLASSIFY_PROMPT,
                messages=[{"role": "user", "content": "Classify:\n\n" + "\n".join(lines)}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text[:text.rfind("```")]

            results = json.loads(text.strip())
            for r in results:
                if r.get("is_benchmark"):
                    paper = next((p for p in batch if p["arxiv_id"] == r["arxiv_id"]), {})
                    # Merge URLs from regex + LLM extraction
                    all_urls = list(dict.fromkeys(
                        (paper.get("repo_links") or []) + (r.get("urls") or [])
                    ))
                    benchmarks.append({
                        "benchmark_name": r.get("benchmark_name"),
                        "category": r.get("category", "other"),
                        "num_samples": r.get("num_samples"),
                        "modalities": r.get("modalities") or [],
                        "task_types": r.get("task_types") or [],
                        "description": r.get("description"),
                        "repo_links": all_urls,
                        "paper_title": paper.get("title"),
                        "arxiv_id": paper.get("arxiv_id"),
                        "arxiv_url": paper.get("url"),
                        "published": paper.get("published", "")[:10],
                        "authors": paper.get("authors", []),
                    })
        except Exception as e:
            print(f"Classification error: {e}")

    return benchmarks


def find_missing_links(benchmarks):
    """Scrape arXiv HTML for benchmarks without repo links."""
    for b in benchmarks:
        if b["repo_links"]:
            continue
        try:
            req = urllib.request.Request(
                f"https://arxiv.org/abs/{b['arxiv_id']}",
                headers={"User-Agent": "VLMBenchScanner/1.0"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
            urls = extract_urls(html)
            if urls:
                b["repo_links"] = urls
            time.sleep(1)
        except:
            continue


def sync_to_supabase(added):
    """Insert new benchmarks into Supabase with embeddings."""
    if not added or not SUPABASE_KEY or not OPENROUTER_KEY:
        if not SUPABASE_KEY:
            print("Skipping Supabase sync: no SUPABASE_SERVICE_KEY")
        if not OPENROUTER_KEY:
            print("Skipping Supabase sync: no OPENROUTER_API_KEY")
        return

    import httpx

    # Generate embeddings
    texts = [
        f"{b.get('benchmark_name') or ''}. {b.get('category') or ''}. {b.get('description') or ''}".strip()
        for b in added
    ]

    try:
        resp = httpx.post(
            "https://openrouter.ai/api/v1/embeddings",
            headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
            json={"model": "openai/text-embedding-3-large", "input": texts},
            timeout=60,
        )
        if resp.status_code != 200:
            print(f"Embedding error: {resp.status_code} {resp.text[:200]}")
            return
        embeddings = [e["embedding"] for e in resp.json()["data"]]
    except Exception as e:
        print(f"Embedding error: {e}")
        return

    # Insert into Supabase via REST API
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=ignore-duplicates",
    }

    for b, emb in zip(added, embeddings):
        row = {
            "benchmark_name": b.get("benchmark_name"),
            "category": b.get("category"),
            "num_samples": b.get("num_samples"),
            "modalities": b.get("modalities") or [],
            "task_types": b.get("task_types") or [],
            "description": b.get("description"),
            "repo_links": b.get("repo_links") or [],
            "paper_title": b.get("paper_title"),
            "arxiv_id": b.get("arxiv_id"),
            "arxiv_url": b.get("arxiv_url"),
            "published": b.get("published"),
            "authors": b.get("authors") or [],
            "embed_text": texts[added.index(b)],
            "embedding": str(emb),
        }
        try:
            r = httpx.post(
                f"{SUPABASE_URL}/rest/v1/benchmarks",
                headers=headers,
                json=row,
                timeout=10,
            )
            if r.status_code not in (200, 201, 409):
                print(f"Supabase insert error for {b.get('arxiv_id')}: {r.status_code} {r.text[:100]}")
        except Exception as e:
            print(f"Supabase insert error: {e}")

    print(f"Synced {len(added)} benchmarks to Supabase")


def main():
    seen = load_seen()
    print(f"Previously seen: {len(seen)}")

    papers = fetch_papers(seen)
    print(f"New papers: {len(papers)}")

    benchmarks = classify(papers)
    print(f"New benchmarks: {len(benchmarks)}")

    find_missing_links(benchmarks)

    # Append to existing JSON
    existing = json.loads(BENCHMARKS_FILE.read_text()) if BENCHMARKS_FILE.exists() else []
    existing_ids = {b["arxiv_id"] for b in existing}
    added = [b for b in benchmarks if b["arxiv_id"] not in existing_ids]

    if added:
        existing.extend(added)
        existing.sort(key=lambda x: x.get("category", ""))
        BENCHMARKS_FILE.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
        print(f"Added {len(added)} benchmarks. Total: {len(existing)}")

        # Sync to Supabase
        sync_to_supabase(added)
    else:
        print("No new benchmarks to add.")

    # Update seen
    seen.update(p["arxiv_id"] for p in papers)
    save_seen(seen)

    # Update CSV
    csv_file = DATA_DIR / "benchmarks.csv"
    with open(csv_file, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["benchmark_name", "category", "num_samples", "modalities", "task_types",
                     "description", "repo_links", "paper_title", "arxiv_id", "arxiv_url", "published", "authors"])
        for b in existing:
            w.writerow([
                b.get("benchmark_name") or "", b.get("category", ""),
                b.get("num_samples") or "", ", ".join(b.get("modalities") or []),
                ", ".join(b.get("task_types") or []), b.get("description") or "",
                " | ".join(b.get("repo_links") or []), b.get("paper_title", ""),
                b.get("arxiv_id", ""), b.get("arxiv_url", ""),
                b.get("published", ""), ", ".join(b.get("authors") or []),
            ])

    return len(added)


if __name__ == "__main__":
    main()
