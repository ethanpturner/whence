"""Measure what the prose scanner does against real model cards.

The pattern in `whence/prose.py` is a heuristic over attacker-controlled English, and a heuristic
whose error rate nobody measured is an assertion. This samples published cards, runs the scanner,
and prints every claim it made so a person can read them and count the wrong ones.

Cards that declare `base_model` in frontmatter are reported separately: there the structured field
is the answer, and the scanner's output on those is a free check -- where it disagrees with a
declared base, one of the two is wrong and it is worth knowing which.

    uv run python scripts/measure_prose.py --limit 120

Spends one listing request and one README request per model, all public and unauthenticated.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any

from whence.prose import find_claims

BASE = "https://huggingface.co"


def _get(path: str) -> tuple[int, str]:
    request = urllib.request.Request(f"{BASE}{path}", headers={"User-Agent": "whence-measure"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, ""
    except urllib.error.URLError, TimeoutError:
        return 0, ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=120)
    parser.add_argument("--sort", default="downloads")
    parser.add_argument(
        "--search",
        default="",
        help="restrict the sample, e.g. `GGUF` for quantizations. The default sample is dominated "
        "by foundation models, which have no ancestor to name -- useful for false positives and "
        "silent about recall.",
    )
    args = parser.parse_args()

    query = f"/api/models?limit={args.limit}&sort={args.sort}&full=false"
    if args.search:
        query += f"&search={args.search}"
    status, body = _get(query)
    if status != 200:
        print(f"listing failed: {status}", file=sys.stderr)
        return 1
    models: list[dict[str, Any]] = json.loads(body)

    read = 0
    with_claim = 0
    rows: list[tuple[str, str, str, str]] = []
    for model in models:
        slug = str(model["id"])
        code, readme = _get(f"/{slug}/raw/main/README.md")
        if code != 200 or not readme:
            continue
        read += 1
        claims = find_claims(readme, subject=slug)
        if not claims:
            continue
        with_claim += 1
        head = readme.split("---")[1] if readme.startswith("---") and "---" in readme[3:] else ""
        declared = "declared" if "base_model:" in head else "prose-only"
        for claim in claims:
            rows.append((slug, claim.name, claim.relation, declared))

    print(f"read {read} cards; {with_claim} produced at least one claim\n")
    for slug, name, relation, declared in rows:
        print(f"  {slug}\n      --{relation}--> {name}   [{declared}]")
    print(
        f"\n{len(rows)} claims from {read} cards. Every line above is a claim the tool would put "
        "in a BOM; read them and count the ones that name something that is not an ancestor."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
