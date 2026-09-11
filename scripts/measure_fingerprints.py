"""Apply modelDNA's lineagebench verdicts to real resolutions, and count what moved.

    uv run python scripts/measure_fingerprints.py            # replay the recording, offline
    uv run python scripts/measure_fingerprints.py --live     # capture a fresh recording

DEC-029 admits an external fingerprint verdict as evidence; DEC-030 says it attaches only to
artifacts a resolution reached. This script measures that path end to end: each `lineagebench`
suspect is resolved through the ordinary resolver (depth 2, structural check on), the evidence
file built by `scripts/fingerprint_evidence.py` is applied, and the result records, per suspect,
which edges moved, which verdicts attached nowhere and why, and where the card's declared relation
disagrees with the tool's class -- the false-declaration-of-kind class no metadata check can see.

The registry interactions are recorded so the figures replay offline (DEC-009). The evidence file
is the tool's output, read as data; nothing here executes model code (DEC-006).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from whence.domain import FingerprintEvidenceFile, Relation, ResolutionReport
from whence.fingerprint import apply, load
from whence.registry import LiveRegistry, RecordedRegistry, Registry, Response
from whence.resolve import Resolver

ROOT = Path(__file__).resolve().parent.parent
EVAL = ROOT / "docs" / "eval" / "fingerprints"
RECORDED = EVAL / "recorded"
EVIDENCE_FILES = (
    EVAL / "evidence" / "lineagebench-modeldna.json",
    EVAL / "evidence" / "lineagebench-cisco.json",
)
DATASET = ROOT / "docs" / "eval" / "lineagebench" / "dataset"

# How a card's declared relation and the dataset's documented kind would read in the tool's
# vocabulary, if they agreed. A verdict class outside the row is a disagreement about the *kind*
# of relationship -- the card said one thing about how the model was made, the weights say another.
CONSISTENT_CLASSES: dict[str, frozenset[str]] = {
    Relation.DERIVES_FROM.value: frozenset({"FINE_TUNE", "SAME_LINEAGE"}),
    Relation.MERGED_FROM.value: frozenset({"LIKELY_MERGE", "SAME_FAMILY_UNRESOLVED"}),
    Relation.QUANTIZED_FROM.value: frozenset({"QUANTIZED_COPY", "EXACT_COPY"}),
    Relation.ADAPTS.value: frozenset({"FINE_TUNE"}),
}


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
            raise SystemExit(f"transient failure on {path}; re-run when the registry is reachable.")
        self.seen[path] = response
        self.order.append(path)
        return response

    def write(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Captured registry interactions, replayed offline (DEC-009). Written by",
            "# scripts/measure_fingerprints.py.",
            f"captured_at: {datetime.now(tz=UTC).date().isoformat()}",
            "host: huggingface.co",
            "interactions:",
        ]
        for index, path in enumerate(self.order):
            response = self.seen[path]
            lines.append(f"  - request: GET {path}")
            lines.append(f"    status: {response.status}")
            if response.location:
                lines.append(f"    location: {response.location}")
            if response.body is None:
                lines.append("    body: null")
            else:
                name = f"{index:03d}-" + _filename(path) + ".json"
                (directory / name).write_text(json.dumps(response.body))
                lines.append(f"    body: {name}")
        (directory / "manifest.yaml").write_text("\n".join(lines) + "\n")


def _filename(path: str) -> str:
    return path.lstrip("/").replace("/", "-").replace("?", "-").replace("&", "-")[:100]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="capture a fresh recording")
    parser.add_argument("--json", dest="as_json", type=Path, default=None)
    args = parser.parse_args()

    truth = [json.loads(line) for line in (DATASET / "ground_truth.jsonl").read_text().splitlines()]
    suspects = sorted({str(row["suspect"]) for row in truth})
    kinds = {str(row["suspect"]): str(row["kind"]) for row in truth}
    files = [(load(path), str(path.relative_to(ROOT))) for path in EVIDENCE_FILES]

    registry: Registry
    recorder: _Recording | None = None
    if args.live:
        recorder = _Recording(LiveRegistry())
        registry = recorder
    else:
        registry = RecordedRegistry(RECORDED)

    per_suspect: list[dict[str, Any]] = []
    totals: dict[str, dict[str, int]] = {
        locator: {
            "verdicts_about_subject": 0,
            "established": 0,
            "created": 0,
            "contradicted": 0,
            "conflicting": 0,
            "abstained": 0,
            "unattached": 0,
        }
        for (_, _), locator in files
    }
    disagreements: list[dict[str, str]] = []
    for suspect in suspects:
        resolver = Resolver(registry, max_depth=2, check_structure=True)
        try:
            before = resolver.resolve(suspect)
        except ValueError as failure:
            per_suspect.append({"suspect": suspect, "error": str(failure)})
            continue
        report = before
        moved: list[dict[str, Any]] = []
        created_rows: list[dict[str, Any]] = []
        applications: dict[str, dict[str, Any]] = {}
        for (evidence_file, digest), locator in files:
            # An operator supplies the verdicts about the model being resolved. Applying every
            # verdict in a benchmark-wide file to every resolution would report each other
            # suspect's verdicts as unattached, which measures the file's shape, not the ingest.
            about = _about(evidence_file, report)
            totals[locator]["verdicts_about_subject"] += len(about.verdicts)
            previous = report
            report, app = apply(report, about, locator, digest)
            for old, new in zip(previous.edges, report.edges[: len(previous.edges)], strict=True):
                if old.verdict is not new.verdict:
                    fingerprint = new.evidence[-1]
                    moved.append(
                        {
                            "source": old.source.slug,
                            "relation": old.relation.value,
                            "target": old.target.slug,
                            "before": old.verdict.value,
                            "after": new.verdict.value,
                            "tool": str(fingerprint.tool),
                            "class": str(fingerprint.verdict_class),
                            "probability": fingerprint.probability,
                        }
                    )
                    consistent = CONSISTENT_CLASSES.get(old.relation.value, frozenset())
                    if fingerprint.verdict_class not in consistent:
                        disagreements.append(
                            {
                                "suspect": suspect,
                                "declared_relation": old.relation.value,
                                "documented_kind": kinds[suspect],
                                "tool": str(fingerprint.tool),
                                "tool_class": str(fingerprint.verdict_class),
                            }
                        )
            for edge in report.edges[len(previous.edges) :]:
                fingerprint = edge.evidence[0]
                created_rows.append(
                    {
                        "source": edge.source.slug,
                        "relation": edge.relation.value,
                        "target": edge.target.slug,
                        "tool": str(fingerprint.tool),
                        "class": str(fingerprint.verdict_class),
                        "probability": fingerprint.probability,
                        "documented_kind": kinds[suspect],
                    }
                )
            applications[locator] = {
                "verdicts_about_subject": len(about.verdicts),
                "established": app.established,
                "created": app.created,
                "contradicted": app.contradicted,
                "conflicting": app.conflicting,
                "abstained": app.abstained,
                "unattached": app.unattached,
            }
            for key in ("established", "created", "contradicted", "conflicting", "unattached"):
                totals[locator][key] += len(getattr(app, key))
            totals[locator]["abstained"] += app.abstained
        per_suspect.append(
            {
                "suspect": suspect,
                "root": before.root.slug,
                "documented_kind": kinds[suspect],
                "edges_before": len(before.edges),
                "declared": [
                    f"{e.source.slug} --{e.relation.value}--> {e.target.slug} [{e.verdict.value}]"
                    for e in before.edges
                    if e.relation is not Relation.REQUIRES_PACKAGE
                ],
                "moved": moved,
                "created": created_rows,
                "applications": applications,
                "evidence_records_on_edges": sum(
                    1 for e in report.edges for ev in e.evidence if ev.from_fingerprint
                ),
            }
        )

    if recorder is not None:
        recorder.write(RECORDED)
        print(f"captured {len(recorder.order)} interactions into {RECORDED}")

    summary: dict[str, Any] = {
        "evidence_files": [
            {
                "locator": locator,
                "digest": digest,
                "tool": evidence_file.tool,
                "tool_version": evidence_file.tool_version,
                "verdicts_in_file": len(evidence_file.verdicts),
                "classes": {cls: effect.value for cls, effect in evidence_file.classes},
                "class_counts": _class_counts(evidence_file),
            }
            for (evidence_file, digest), locator in files
        ],
        "suspects": per_suspect,
        "totals": totals,
        "kind_disagreements": disagreements,
    }
    if args.as_json:
        args.as_json.write_text(json.dumps(summary, indent=2) + "\n")

    for entry in summary["evidence_files"]:
        print(
            f"{entry['verdicts_in_file']} verdicts from {entry['tool']} {entry['tool_version']}; "
            "classes: " + ", ".join(f"{k}={v}" for k, v in sorted(entry["class_counts"].items()))
        )
        print(
            f"  applied to {len(suspects)} resolutions: "
            + ", ".join(f"{k}={v}" for k, v in totals[entry["locator"]].items())
        )
    for row in per_suspect:
        if "error" in row:
            print(f"  {row['suspect']}: did not resolve ({row['error']})")
            continue
        for m in row["moved"]:
            print(
                f"  moved   {m['source']} --{m['relation']}--> {m['target']}: "
                f"{m['before']} -> {m['after']} ({m['tool']} {m['class']}, p={m['probability']})"
            )
        for c in row["created"]:
            print(
                f"  created {c['source']} --{c['relation']}--> {c['target']} "
                f"({c['tool']} {c['class']}, p={c['probability']})"
            )
        for locator, app in row["applications"].items():
            for u in app["unattached"]:
                print(f"  unattached [{locator.rsplit('/', 1)[-1]}] {u}")
    print(f"kind disagreements (declared relation vs tool class): {len(disagreements)}")
    for d in disagreements:
        print(f"  {d['suspect']}: card {d['declared_relation']}, {d['tool']} {d['tool_class']}")
    return 0


def _about(file: FingerprintEvidenceFile, report: ResolutionReport) -> FingerprintEvidenceFile:
    """The verdicts whose subject is the resolution's root, at whatever name the root resolved to."""
    return FingerprintEvidenceFile.model_validate(
        {
            **file.model_dump(),
            "verdicts": tuple(v for v in file.verdicts if v.subject.slug == report.root.slug),
        }
    )


def _class_counts(evidence_file: FingerprintEvidenceFile) -> dict[str, int]:
    counts: dict[str, int] = {}
    for verdict in evidence_file.verdicts:
        counts[verdict.verdict_class] = counts.get(verdict.verdict_class, 0) + 1
    return counts


if __name__ == "__main__":
    sys.exit(main())
