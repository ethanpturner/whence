"""Convert Cisco Model Provenance Kit `scan --json` results into a DEC-029 evidence file.

    uv run python scripts/cisco_evidence.py --revisions docs/eval/lineagebench/results.json \
        SCAN.json [SCAN.json ...] -o evidence.json

A scan ranks a suspect against the kit's reference database and labels each match. The labels
are produced two ways, and the mapping declared here keeps them apart:

    Confirmed Match          -> abstains   (MFI tier 1 or 2: the architecture or family *hash*
                                            matched, and the pipeline score is set to 1.0 or 0.9
                                            before any weight is read -- a metadata match, which
                                            DEC-020 already treats as necessary and not sufficient)
    High-Confidence Match    -> establishes (identity score over five weight signals > 0.75)
    Weak Match, Not Matched, Insufficient data, and any "(metadata only)" label -> abstains

Only matches naming a model in the supplied revision table become verdicts, because a verdict
must pin both sides (DEC-002) and the kit reports the reference model by short name at whatever
revision its fingerprints were taken. Matches outside the table are listed on stderr and
dropped, which is itself a fact the measurement page reports.

Runs no model code; reads JSON another process wrote (DEC-006).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from whence.domain import ArtifactRef, EvidenceEffect, FingerprintEvidenceFile, FingerprintVerdict
from whence.fingerprint import to_json

CLASSES: tuple[tuple[str, EvidenceEffect], ...] = (
    ("Confirmed Match", EvidenceEffect.ABSTAINS),
    ("High-Confidence Match", EvidenceEffect.ESTABLISHES),
    ("Weak Match", EvidenceEffect.ABSTAINS),
    ("Not Matched", EvidenceEffect.ABSTAINS),
    ("Insufficient data", EvidenceEffect.ABSTAINS),
)

# The scan reports the suspect under the name it was asked about. lineagebench names one suspect
# under a namespace that now redirects (DEC-017); the kit fingerprinted what the redirect serves.
ALIASES = {"dphn/dolphin-2.9-llama3-8b": "cognitivecomputations/dolphin-2.9-llama3-8b"}


def _ref(slug: str, revision: str) -> ArtifactRef:
    namespace, name = slug.split("/", 1)
    return ArtifactRef(
        host="huggingface.co", namespace=namespace, name=name, revision=revision, pinned=True
    )


def _label(raw: str) -> str:
    return raw.replace(" (metadata only)", "")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scans", nargs="+", type=Path)
    parser.add_argument("--revisions", type=Path, required=True, help="lineagebench results.json")
    parser.add_argument("-o", "--out", type=Path, required=True)
    parser.add_argument("--tool-version", default="1.1.0")
    parser.add_argument("--generated-at", help="ISO timestamp to record instead of now")
    args = parser.parse_args()

    table: dict[str, dict[str, Any]] = json.loads(args.revisions.read_text())["models"]
    by_name = {slug.split("/", 1)[1]: slug for slug in table}
    verdicts: list[FingerprintVerdict] = []
    dropped: list[str] = []
    for path in args.scans:
        scan = json.loads(path.read_text())
        suspect_raw = str(scan["model_info"]["model_path"])
        suspect = ALIASES.get(suspect_raw, suspect_raw)
        suspect_revision = table.get(suspect, {}).get("revision") or (
            "d94261ccf9597b04b60b0dd5d15c76e9da2bb6f1" if suspect_raw in ALIASES else None
        )
        if not suspect_revision:
            print(f"{path}: {suspect} has no recorded revision; skipped", file=sys.stderr)
            continue
        for match in scan["matches"]:
            name = str(match["model_id"])
            candidate = by_name.get(name)
            label = _label(str(match["provenance_decision"]))
            if candidate is None or candidate == suspect:
                dropped.append(f"{suspect}: {name} ({label}, {match['scores']['pipeline_score']})")
                continue
            metadata_only = "(metadata only)" in str(match["provenance_decision"])
            verdicts.append(
                FingerprintVerdict(
                    subject=_ref(suspect, suspect_revision),
                    candidate=_ref(candidate, str(table[candidate]["revision"])),
                    verdict_class=label if not metadata_only else "Insufficient data",
                    probability=float(match["scores"]["pipeline_score"]),
                    detail=(
                        f"mfi_tier={match['scores']['mfi_tier']} "
                        f"identity={match['scores']['identity_score']} "
                        f"match_type={match['match_type']}"
                    ),
                )
            )
    for line in dropped:
        print(f"dropped (not a lineagebench model): {line}", file=sys.stderr)
    evidence = FingerprintEvidenceFile(
        tool="cisco-ai-provenance-kit",
        tool_version=args.tool_version,
        generated_at=datetime.fromisoformat(args.generated_at)
        if args.generated_at
        else datetime.now(tz=UTC),
        classes=CLASSES,
        verdicts=tuple(verdicts),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(to_json(evidence))
    print(f"{len(verdicts)} verdicts ({len(dropped)} matches dropped) -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
