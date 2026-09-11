"""Run the structural check against lineagebench's labelled pairs.

DEC-020's check has a measured false-positive rate -- zero over 33 real declared fine-tunes -- and
an **unmeasured detection rate**, because that sample contained no mistaken declaration. lineagebench
(huggingface.co/datasets/AwaisAdilKhokhar/lineagebench) labels every pair from the publishing
organization's own documentation and ships 107 hard negatives: suspects scored against
cross-family wrong parents, plus cross-family parent-versus-parent pairs. Those are the first
labelled negatives this check has been run against.

    uv run python scripts/measure_lineagebench.py            # replay the recording, offline
    uv run python scripts/measure_lineagebench.py --live     # capture a fresh recording

The pairs are the dataset's. The script reconstructs the two pools from `ground_truth.jsonl` and
`parents.json` using the family grouping the dataset's README describes, and refuses to report if
the pool sizes disagree with the dataset's own `metrics.json` -- a reconstructed benchmark that is
silently the wrong size would measure something other than what it names.

A live run spends one listing request and one configuration request (plus the registry's content
redirect) per model, all public and unauthenticated. Four of the eight parents are gated; their
configurations answer 401 and the check returns `unverifiable` for every pair touching them. That
is recorded as the response it is, because the coverage bound is part of the result.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from whence.domain import ArtifactRef, Relation, Verdict
from whence.registry import LiveRegistry, RecordedRegistry, Registry, Response
from whence.structure import check

ROOT = Path(__file__).resolve().parent.parent
EVAL = ROOT / "docs" / "eval" / "lineagebench"
DATASET = EVAL / "dataset"
RECORDED = EVAL / "recorded"

# The dataset's README: "Same-family wrong parents (e.g. Zephyr against Mistral-v0.3 rather than
# v0.1) are deliberately excluded from the negative pool." The grouping is not a field in the
# dataset, so it is stated here and checked against metrics.json below.
FAMILIES: dict[str, str] = {
    "mistralai/Mistral-7B-v0.1": "mistral",
    "mistralai/Mistral-7B-v0.3": "mistral",
    "meta-llama/Llama-2-7b-hf": "llama-2",
    "meta-llama/Meta-Llama-3-8B": "llama-3",
    "Qwen/Qwen2.5-7B": "qwen2.5",
    "Qwen/Qwen2.5-14B": "qwen2.5",
    "google/gemma-2b": "gemma",
    "google/gemma-2-9b": "gemma",
}


def _ref(slug: str) -> ArtifactRef:
    namespace, name = slug.split("/", 1)
    return ArtifactRef(host="huggingface.co", namespace=namespace, name=name, pinned=False)


class _Recording:
    """Wraps the live registry and keeps every interaction, in request order (as capture_scenario)."""

    def __init__(self, inner: LiveRegistry) -> None:
        self._inner = inner
        self.seen: dict[str, Response] = {}
        self.order: list[str] = []

    def get(self, path: str) -> Response:
        if path in self.seen:
            return self.seen[path]
        response = self._inner.get(path)
        if response.status == 0:
            raise SystemExit(
                f"transient failure on {path}. A recording captured around a network failure would "
                "bake a `partial` result into the measurement; re-run when the registry is reachable."
            )
        self.seen[path] = response
        self.order.append(path)
        return response

    def write(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Captured registry interactions, replayed offline (DEC-009). Written by",
            "# scripts/measure_lineagebench.py; a 401 on a gated model is recorded as the response",
            "# it is, because the coverage bound is part of the measurement.",
            f"captured_at: {datetime.now(tz=UTC).date().isoformat()}",
            "host: huggingface.co",
            "interactions:",
        ]
        for path in self.order:
            response = self.seen[path]
            lines.append(f"  - request: GET {path}")
            lines.append(f"    status: {response.status}")
            if response.location:
                lines.append(f"    location: {response.location}")
            if response.body is None:
                lines.append("    body: null")
            else:
                name = _filename(path) + ".json"
                (directory / name).write_text(json.dumps(response.body))
                lines.append(f"    body: {name}")
        (directory / "manifest.yaml").write_text("\n".join(lines) + "\n")


def _filename(path: str) -> str:
    trimmed = path.lstrip("/")
    if trimmed.startswith("api/models/"):
        return "model-" + trimmed[len("api/models/") :].replace("/", "-")
    if "/resolve/main/config.json" in trimmed:
        return "config-" + trimmed.split("/resolve/")[0].replace("/", "-")
    if trimmed.startswith("api/resolve-cache/models/"):
        rest = trimmed[len("api/resolve-cache/models/") :]
        slug = "/".join(rest.split("/")[:2])
        return "cached-config-" + slug.replace("/", "-")
    return trimmed.replace("/", "-").replace("?", "-").replace("&", "-")[:120]


def _pools(
    truth: list[dict[str, Any]], parents: list[str]
) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    """(positives, negatives, limitation cases), each a (subject, candidate, kind) triple."""
    positives: list[tuple[str, str, str]] = []
    limitation: list[tuple[str, str, str]] = []
    negatives: list[tuple[str, str, str]] = []
    for row in truth:
        suspect, parent, kind = str(row["suspect"]), str(row["parent"]), str(row["kind"])
        if not row["in_positive_pool"]:
            limitation.append((suspect, parent, kind))
            continue
        positives.append((suspect, parent, kind))
        family = FAMILIES[parent]
        for wrong in parents:
            if FAMILIES[wrong] != family:
                negatives.append((suspect, wrong, f"{kind} suspect vs cross-family parent"))
    for i, a in enumerate(parents):
        for b in parents[i + 1 :]:
            if FAMILIES[a] != FAMILIES[b]:
                negatives.append((a, b, "cross-family parent vs parent"))
    return positives, negatives, limitation


def _outcome(verdict: Verdict, detail: str) -> str:
    if verdict is Verdict.CONTRADICTED:
        return "contradicted"
    if "is unavailable" in detail:
        return "config-unavailable"
    if "too few comparable" in detail:
        return "too-few-fields"
    if "not reached" in detail:
        return "transient"
    return "compatible"


def _gated(registry: Registry, slug: str) -> tuple[str | None, str | None]:
    """The model's revision and gating state from its listing; both go into the result."""
    response = registry.get(f"/api/models/{slug}")
    if response.status != 200 or not isinstance(response.body, dict):
        return None, f"listing answered {response.status}"
    body = response.body
    gated = body.get("gated")
    return (str(body["sha"]) if body.get("sha") else None), (str(gated) if gated else "false")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="capture a fresh recording")
    parser.add_argument(
        "--json", dest="as_json", type=Path, default=None, help="write the per-pair results here"
    )
    args = parser.parse_args()

    truth = [json.loads(line) for line in (DATASET / "ground_truth.jsonl").read_text().splitlines()]
    parents: list[str] = json.loads((DATASET / "parents.json").read_text())
    metrics = json.loads((DATASET / "metrics.json").read_text())
    positives, negatives, limitation = _pools(truth, parents)
    if (len(positives), len(negatives), len(limitation)) != (
        metrics["n_positive_pairs"],
        metrics["n_hard_negative_pairs"],
        metrics["n_limitation_cases"],
    ):
        print(
            f"reconstructed pools are {len(positives)}/{len(negatives)}/{len(limitation)}; the "
            f"dataset says {metrics['n_positive_pairs']}/{metrics['n_hard_negative_pairs']}/"
            f"{metrics['n_limitation_cases']}. Refusing to report against the wrong benchmark.",
            file=sys.stderr,
        )
        return 1

    registry: Registry
    recorder: _Recording | None = None
    if args.live:
        recorder = _Recording(LiveRegistry())
        registry = recorder
    else:
        registry = RecordedRegistry(RECORDED)

    models = sorted({s for s, _, _ in positives + negatives + limitation} | set(parents))
    listing = {slug: _gated(registry, slug) for slug in models}

    rows: list[dict[str, Any]] = []
    for pool, pairs in (
        ("positive", positives),
        ("negative", negatives),
        ("limitation", limitation),
    ):
        for subject, candidate, kind in pairs:
            # The limitation cases are a depth up-scale and a GPTQ repack. The dataset scores them
            # as `derives-from` claims a method should abstain on; the GPTQ case is a quantization,
            # which DEC-020 already puts out of the check's scope, and both relations are run so
            # the difference is visible.
            relation = Relation.DERIVES_FROM
            result = check(registry, _ref(subject), _ref(candidate), relation)
            rows.append(
                {
                    "pool": pool,
                    "kind": kind,
                    "subject": subject,
                    "candidate": candidate,
                    "verdict": result.verdict.value,
                    "outcome": _outcome(result.verdict, result.detail),
                    "differing_fields": list(result.differing_fields),
                    "subject_gated": listing[subject][1],
                    "candidate_gated": listing[candidate][1],
                }
            )

    if recorder is not None:
        recorder.write(RECORDED)
        print(f"captured {len(recorder.order)} interactions into {RECORDED}")

    def _count(pool: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in rows:
            if row["pool"] == pool:
                counts[str(row["outcome"])] = counts.get(str(row["outcome"]), 0) + 1
        return dict(sorted(counts.items()))

    pool_summary: dict[str, dict[str, Any]] = {
        pool: {"n": len(pairs), "outcomes": _count(pool)}
        for pool, pairs in (
            ("positive", positives),
            ("negative", negatives),
            ("limitation", limitation),
        )
    }
    summary: dict[str, Any] = {
        "dataset_revision": (DATASET / "SOURCE.md").read_text().split("`")[3],
        "models": {
            slug: {"revision": revision, "gated": gated}
            for slug, (revision, gated) in sorted(listing.items())
        },
        "pools": pool_summary,
        "pairs": rows,
    }
    if args.as_json:
        args.as_json.write_text(json.dumps(summary, indent=2) + "\n")

    gated = sorted(slug for slug, (_, g) in listing.items() if g not in (None, "false"))
    print(f"\n{len(models)} models; {len(gated)} gated: {', '.join(gated)}\n")
    for pool in ("positive", "negative", "limitation"):
        n = pool_summary[pool]["n"]
        print(f"{pool:<11} n={n:<4} " + "  ".join(f"{k}={v}" for k, v in _count(pool).items()))
    print()
    for row in rows:
        if row["outcome"] == "contradicted":
            print(
                f"  contradicted [{row['pool']}] {row['subject']} vs {row['candidate']}: "
                f"{', '.join(row['differing_fields'])}"
            )
    comparable_neg = [
        r
        for r in rows
        if r["pool"] == "negative" and r["outcome"] in ("contradicted", "compatible")
    ]
    hit = sum(1 for r in comparable_neg if r["outcome"] == "contradicted")
    print(
        f"\nDetection on labelled negatives: {hit} of {len(comparable_neg)} comparable pairs "
        f"contradicted, out of {len(negatives)} negatives in the pool. The remainder of the pool "
        f"reached no comparison, and a pair the check could not read is not a pair it missed.\n"
        "Nothing here measures the check against a mistaken *declaration*: these negatives are the "
        "dataset's constructions, and no card on the registry declares any of them."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
