"""Convert modelDNA pair results into a DEC-029 fingerprint evidence file.

    uv run python scripts/fingerprint_evidence.py PAIR.json [PAIR.json ...] -o evidence.json

Each input is one pair as the measurement driver wrote it (or as `modeldna compare --json` prints
it, with the two pinned revisions supplied by `--subject-revision`/`--candidate-revision`). The
output declares an effect for every modelDNA class, and the mapping is stated here rather than
derived, because the tool's own negative is not this tool's `contradicted` (DEC-029):

    EXACT_COPY, QUANTIZED_COPY, FINE_TUNE, SAME_LINEAGE   -> establishes
    LIKELY_MERGE, SAME_FAMILY_UNRESOLVED, NO_MATCH, INSUFFICIENT -> abstains

`NO_MATCH` abstains rather than contradicts: on lineagebench's own limitation case, a documented
depth up-scale of a Mistral model returns `NO_MATCH`, so mapping it to `contradicted` would have
refuted a true derivation. Nothing in a modelDNA pair verdict is mapped to `contradicts`; a
contradiction from this tool would need a separate, argued mapping and its own decision entry.

This script runs no model code: it reads JSON another process wrote (DEC-006).
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

MODELDNA_CLASSES: tuple[tuple[str, EvidenceEffect], ...] = (
    ("EXACT_COPY", EvidenceEffect.ESTABLISHES),
    ("QUANTIZED_COPY", EvidenceEffect.ESTABLISHES),
    ("FINE_TUNE", EvidenceEffect.ESTABLISHES),
    ("SAME_LINEAGE", EvidenceEffect.ESTABLISHES),
    ("LIKELY_MERGE", EvidenceEffect.ABSTAINS),
    ("SAME_FAMILY_UNRESOLVED", EvidenceEffect.ABSTAINS),
    ("NO_MATCH", EvidenceEffect.ABSTAINS),
    ("INSUFFICIENT", EvidenceEffect.ABSTAINS),
)


def _ref(slug: str, revision: str) -> ArtifactRef:
    namespace, name = slug.split("/", 1)
    return ArtifactRef(
        host="huggingface.co", namespace=namespace, name=name, revision=revision, pinned=True
    )


def verdict_from_pair(pair: dict[str, Any]) -> FingerprintVerdict:
    """One driver pair record -> one verdict. The class and probability are the tool's, verbatim."""
    verdict = pair["verdict"]
    probability = verdict.get("probability")
    # The artifact the tool actually read. lineagebench names one suspect under a namespace that
    # now redirects (DEC-017); the fingerprint is of the bytes the redirect serves, so the verdict
    # names that artifact and not the name the dataset used.
    subject = str(pair.get("subject_fingerprinted_as") or pair["subject"])
    candidate = str(pair.get("candidate_fingerprinted_as") or pair["candidate"])
    return FingerprintVerdict(
        subject=_ref(subject, str(pair["subject_revision"])),
        candidate=_ref(candidate, str(pair["candidate_revision"])),
        verdict_class=str(verdict["verdict"]),
        probability=float(probability) if probability is not None else None,
        detail="; ".join(str(n) for n in verdict.get("notes") or []) or None,
    )


def build(pairs: list[dict[str, Any]], tool_version: str) -> FingerprintEvidenceFile:
    return FingerprintEvidenceFile(
        tool="modeldna",
        tool_version=tool_version,
        generated_at=datetime.now(tz=UTC),
        classes=MODELDNA_CLASSES,
        verdicts=tuple(verdict_from_pair(p) for p in pairs),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pairs", nargs="+", type=Path)
    parser.add_argument("-o", "--out", type=Path, required=True)
    parser.add_argument("--subject-revision", help="for a bare `modeldna compare --json` record")
    parser.add_argument("--candidate-revision", help="for a bare `modeldna compare --json` record")
    parser.add_argument("--generated-at", help="ISO timestamp to record instead of now")
    args = parser.parse_args()

    records: list[dict[str, Any]] = []
    versions: set[str] = set()
    for path in args.pairs:
        record = json.loads(path.read_text())
        if "subject" not in record:
            # A raw `modeldna compare --json` record: target is the suspect, best_id the candidate.
            if not (args.subject_revision and args.candidate_revision):
                print(f"{path}: raw compare record needs both --*-revision flags", file=sys.stderr)
                return 1
            record = {
                "subject": record["target"],
                "subject_revision": args.subject_revision,
                "candidate": record["curves"]["best_id"],
                "candidate_revision": args.candidate_revision,
                "verdict": record["verdict"],
                "tool_version": record["tool_version"],
            }
        versions.add(str(record["tool_version"]))
        records.append(record)
    if len(versions) != 1:
        print(f"pairs come from several tool versions: {sorted(versions)}", file=sys.stderr)
        return 1
    evidence = build(records, versions.pop())
    if args.generated_at:
        evidence = FingerprintEvidenceFile.model_validate(
            {**evidence.model_dump(), "generated_at": args.generated_at}
        )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(to_json(evidence))
    print(f"{len(records)} verdicts -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
