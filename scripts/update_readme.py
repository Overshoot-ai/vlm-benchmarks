"""Regenerate README stats from benchmarks.json."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data" / "benchmarks.json"
README = ROOT / "README.md"


def main():
    benchmarks = json.loads(DATA.read_text())
    total = len(benchmarks)

    readme = README.read_text()

    # Update total count
    readme = re.sub(
        r'\*\*[\d,]+ benchmarks\*\*',
        f'**{total:,} benchmarks**',
        readme,
    )

    README.write_text(readme)
    print(f"README updated: {total} benchmarks")


if __name__ == "__main__":
    main()
