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
import concurrent.futures
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from whence.prose import find_claims

BASE = "https://huggingface.co"


CACHE = Path(__file__).resolve().parent.parent / ".prose-cache"


def _get(path: str, *, cache: bool = False) -> tuple[int, str]:
    """Fetch, with an on-disk cache for card bodies and a bounded retry on 429.

    Both exist because of a wrong answer this script produced. Rate-limited fetches were being
    swallowed and reported as "no card", so a follow-up analysis found zero cards stating a
    derivation the scanner had missed -- a clean recall result that was really throttling. A
    measurement tool that reports being throttled as a finding is this project's own failure mode,
    arriving in the instrument instead of the subject.
    """
    key = CACHE / (path.strip("/").replace("/", "_").replace("?", "_") or "root")
    if cache and key.exists():
        return 200, key.read_text()

    for attempt in range(4):
        request = urllib.request.Request(f"{BASE}{path}", headers={"User-Agent": "whence-measure"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8", "replace")
                if cache:
                    key.parent.mkdir(parents=True, exist_ok=True)
                    key.write_text(body)
                return response.status, body
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < 3:
                time.sleep(2**attempt)
                continue
            return exc.code, ""
        except urllib.error.URLError, TimeoutError:
            if attempt < 3:
                time.sleep(2**attempt)
                continue
            return 0, ""
    return 0, ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=120)
    parser.add_argument(
        "--searches",
        default="",
        help="comma-separated searches to pool, for a sample wider than one query can return. The "
        "registry caps a listing, so breadth comes from several queries rather than a bigger one.",
    )
    parser.add_argument(
        "--json", dest="as_json", action="store_true", help="emit the sample as JSON for review"
    )
    parser.add_argument("--sort", default="downloads")
    parser.add_argument(
        "--search",
        default="",
        help="restrict the sample, e.g. `GGUF` for quantizations. The default sample is dominated "
        "by foundation models, which have no ancestor to name -- useful for false positives and "
        "silent about recall.",
    )
    args = parser.parse_args()

    searches = [s.strip() for s in args.searches.split(",") if s.strip()] or [args.search]
    models: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for search in searches:
        query = f"/api/models?limit={args.limit}&sort={args.sort}&full=false"
        if search:
            query += f"&search={search}"
        status, body = _get(query)
        if status != 200:
            print(f"listing failed for {search!r}: {status}", file=sys.stderr)
            continue
        for model in json.loads(body):
            if str(model["id"]) not in seen_ids:
                seen_ids.add(str(model["id"]))
                models.append(model)
    if not models:
        print("no models sampled", file=sys.stderr)
        return 1

    read = 0
    rows: list[dict[str, str]] = []

    unreadable: list[tuple[str, int]] = []

    def one(model: dict[str, Any]) -> tuple[int, list[dict[str, str]]]:
        slug = str(model["id"])
        code, readme = _get(f"/{slug}/raw/main/README.md", cache=True)
        if code != 200 or not readme:
            # Recorded, not dropped. A 404 means the model has no card; a 429 means this script was
            # throttled and knows nothing about that card, and reporting the two alike is how the
            # earlier recall figure came out clean.
            if code not in (200, 404):
                unreadable.append((slug, code))
            return 0, []
        claims = find_claims(readme, subject=slug)
        head = readme.split("---")[1] if readme.startswith("---") and "---" in readme[3:] else ""
        # The tool only reads prose when the frontmatter declares no base, so a claim on a card
        # that declares one would never be emitted. Both are reported: the emitted set is what the
        # error rate is about, and the rest is a free check against a structured answer.
        declared = "declared" if "base_model:" in head else "prose-only"
        return 1, [
            {"model": slug, "name": c.name, "relation": c.relation, "card": declared}
            for c in claims
        ] or (
            [{"model": slug, "name": "", "relation": "", "card": declared}]
            if declared == "prose-only"
            else []
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for count, found in pool.map(one, models):
            read += count
            rows += found

    # A card that declares a `base_model` is never read for prose, so the population the scanner
    # can fire on at all is the cards without one. Precision without that denominator is a number
    # with no scale: eleven correct claims means one thing out of fifteen candidates and another
    # out of four hundred.
    silent = sum(1 for r in rows if not r["name"])
    rows = [r for r in rows if r["name"]]
    emitted = [r for r in rows if r["card"] == "prose-only"]
    if args.as_json:
        print(json.dumps({"cards_read": read, "claims": rows}, indent=2))
        return 0

    for row in rows:
        marker = " " if row["card"] == "prose-only" else "~"
        print(f"{marker} {row['model']}\n      --{row['relation']}--> {row['name']}")
    candidates = silent + len(emitted)
    if unreadable:
        throttled = sum(1 for _, code in unreadable if code == 429)
        print(
            f"\n!! {len(unreadable)} cards could not be read ({throttled} throttled). They are "
            "excluded from every figure below, and a large number here means the sample is "
            "smaller than it looks -- re-run rather than reading the percentages.",
            file=sys.stderr,
        )
    print(
        f"\nsampled {len(models)} models across {len(searches)} search(es); {read} had a readable "
        f"card.\n{candidates} of those declare no `base_model` and are therefore the only cards "
        f"the scanner is ever run against.\n"
        f"{len(rows)} claims in total, of which {len(emitted)} are on those candidate cards and so "
        f"are the only ones the tool would emit (a leading space marks those; `~` marks a card "
        f"that already has a structured answer and is shown as a free cross-check).\n"
        "Read them and count the ones that name something which is not an ancestor. Nothing here "
        "measures recall: a card in the silent remainder may state a derivation this pattern did "
        "not recognise, and only reading them would establish how many."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
