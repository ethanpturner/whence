"""DEC-029: a fingerprint evidence file moves an edge only under the effect it declares.

Every path is exercised against `declared-base`'s recording, so no network is touched and the
pinned revisions are the recording's own.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from whence.cyclonedx import to_cyclonedx
from whence.domain import (
    ArtifactRef,
    Edge,
    EvidenceEffect,
    FingerprintEvidenceFile,
    FingerprintVerdict,
    ProvenanceClass,
    ResolutionReport,
    Verdict,
)
from whence.evaluate import score
from whence.fingerprint import apply, load
from whence.registry import RecordedRegistry
from whence.resolve import resolver_for

ROOT = Path(__file__).resolve().parents[2]
SCENARIO = ROOT / "benchmarks" / "declared-base"


def _report() -> ResolutionReport:
    target = yaml.safe_load((SCENARIO / "input" / "target.yaml").read_text())
    return resolver_for(target, RecordedRegistry(SCENARIO / "recorded")).resolve(
        str(target["target"])
    )


def _declared_edge(report: ResolutionReport) -> Edge:
    return next(e for e in report.edges if e.relation.value == "derives-from")


def _file(
    verdicts: list[FingerprintVerdict],
    classes: dict[str, EvidenceEffect] | None = None,
) -> FingerprintEvidenceFile:
    return FingerprintEvidenceFile(
        tool="modeldna",
        tool_version="0.1.0",
        generated_at="2026-09-10T12:00:00Z",  # type: ignore[arg-type]
        classes=tuple(
            (
                classes
                or {
                    "FINE_TUNE": EvidenceEffect.ESTABLISHES,
                    "NO_MATCH": EvidenceEffect.ABSTAINS,
                    "REFUTED": EvidenceEffect.CONTRADICTS,
                }
            ).items()
        ),
        verdicts=tuple(verdicts),
    )


def _verdict(edge: Edge, cls: str, probability: float | None = 0.99) -> FingerprintVerdict:
    return FingerprintVerdict(
        subject=edge.source, candidate=edge.target, verdict_class=cls, probability=probability
    )


def test_an_undeclared_class_fails_validation() -> None:
    edge = _declared_edge(_report())
    with pytest.raises(ValidationError, match="no declared effect"):
        _file([_verdict(edge, "SOMETHING_NEW")])


def test_an_unpinned_side_fails_validation() -> None:
    edge = _declared_edge(_report())
    loose = ArtifactRef(
        host=edge.target.host, namespace=edge.target.namespace, name=edge.target.name, pinned=False
    )
    with pytest.raises(ValidationError, match="pinned"):
        FingerprintVerdict(subject=edge.source, candidate=loose, verdict_class="FINE_TUNE")


def test_establishes_moves_a_declared_edge_and_keeps_the_card_record() -> None:
    report = _report()
    edge = _declared_edge(report)
    assert edge.verdict is Verdict.UNVERIFIABLE
    updated, app = apply(report, _file([_verdict(edge, "FINE_TUNE")]), "fp.json", "ab" * 32)
    moved = _declared_edge(updated)
    assert moved.verdict is Verdict.VERIFIED
    assert moved.provenance is ProvenanceClass.VERIFIED_BY_WEIGHTS
    # Two records: the card's own assertion, and the fingerprint that established it.
    assert len(moved.evidence) == 2
    assert moved.evidence[0].from_fingerprint is False
    fingerprint = moved.evidence[1]
    assert (fingerprint.tool, fingerprint.verdict_class, fingerprint.probability) == (
        "modeldna",
        "FINE_TUNE",
        0.99,
    )
    assert fingerprint.content_digest == "ab" * 32
    assert app.established and not app.unattached
    # The rest of the graph is untouched.
    assert len(updated.edges) == len(report.edges)


def test_contradicts_moves_a_declared_edge_down() -> None:
    report = _report()
    edge = _declared_edge(report)
    updated, app = apply(report, _file([_verdict(edge, "REFUTED", None)]), "fp.json", "cd" * 32)
    moved = _declared_edge(updated)
    assert moved.verdict is Verdict.CONTRADICTED
    # Contradiction does not establish anything; the provenance is still the card's.
    assert moved.provenance is ProvenanceClass.ASSERTED_BY_CARD
    assert app.contradicted


def test_abstains_changes_nothing() -> None:
    report = _report()
    edge = _declared_edge(report)
    updated, app = apply(report, _file([_verdict(edge, "NO_MATCH", 0.2)]), "fp.json", "ef" * 32)
    assert updated == report
    assert app.abstained == 1 and app.attached == 0


def test_an_artifact_the_resolution_did_not_reach_is_unattached_and_no_node_is_invented() -> None:
    report = _report()
    edge = _declared_edge(report)
    stranger = ArtifactRef(
        host="huggingface.co", namespace="nobody", name="model", revision="f" * 40, pinned=True
    )
    verdict = FingerprintVerdict(subject=edge.source, candidate=stranger, verdict_class="FINE_TUNE")
    updated, app = apply(report, _file([verdict]), "fp.json", "00" * 32)
    assert updated == report
    assert (
        len(app.unattached) == 1 and "not an artifact this resolution reached" in app.unattached[0]
    )


def test_a_revision_mismatch_is_unattached() -> None:
    report = _report()
    edge = _declared_edge(report)
    other = ArtifactRef.model_validate({**edge.target.model_dump(), "revision": "1" * 40})
    verdict = FingerprintVerdict(subject=edge.source, candidate=other, verdict_class="FINE_TUNE")
    updated, app = apply(report, _file([verdict]), "fp.json", "00" * 32)
    assert updated == report
    assert "different bytes" in app.unattached[0]


def test_a_contradiction_on_an_undeclared_pair_is_recorded_nowhere() -> None:
    report = _report()
    edge = _declared_edge(report)
    # Reverse the pair: both are reached nodes, and no card declares base -> root.
    verdict = FingerprintVerdict(
        subject=edge.target, candidate=edge.source, verdict_class="REFUTED"
    )
    updated, app = apply(report, _file([verdict]), "fp.json", "00" * 32)
    assert updated == report
    assert "no claim to contradict" in app.unattached[0]


def test_establishes_on_an_undeclared_pair_of_reached_nodes_creates_the_edge() -> None:
    report = _report()
    edge = _declared_edge(report)
    verdict = FingerprintVerdict(
        subject=edge.target, candidate=edge.source, verdict_class="FINE_TUNE"
    )
    updated, app = apply(report, _file([verdict]), "fp.json", "00" * 32)
    assert len(updated.edges) == len(report.edges) + 1
    created = updated.edges[-1]
    assert created.provenance is ProvenanceClass.VERIFIED_BY_WEIGHTS
    assert created.verdict is Verdict.VERIFIED
    assert created.relation.value == "derives-from"
    assert len(created.evidence) == 1 and created.evidence[0].from_fingerprint
    assert app.created


def test_the_harness_accepts_verified_only_with_fingerprint_evidence() -> None:
    report = _report()
    edge = _declared_edge(report)
    # Without a fingerprint, a `verified` edge is an honesty failure, as before.
    faked = ResolutionReport.model_validate(
        {
            **report.model_dump(),
            "edges": tuple(
                Edge.model_validate(
                    {**e.model_dump(), "verdict": "verified", "provenance": "verified-by-weights"}
                )
                if e is edge
                else e
                for e in report.edges
            ),
        }
    )
    assert any(
        "no fingerprint evidence" in f
        for f in score(faked, SCENARIO / "expected", "x").honesty_failures
    )
    # With one, that specific failure is gone (the scenario's own truth set may still expect
    # `unverifiable`, which is a different, correct mismatch: the truth set was authored without
    # an evidence file).
    updated, _ = apply(report, _file([_verdict(edge, "FINE_TUNE")]), "fp.json", "ab" * 32)
    failures = score(updated, SCENARIO / "expected", "x").honesty_failures
    assert not any("fingerprint" in f for f in failures)


def test_the_bom_carries_the_tool_class_and_probability_as_evidence_data() -> None:
    report = _report()
    edge = _declared_edge(report)
    updated, _ = apply(report, _file([_verdict(edge, "FINE_TUNE", 0.9931)]), "fp.json", "ab" * 32)
    bom = to_cyclonedx(updated)
    claim = next(c for c in bom["declarations"]["claims"] if "derives-from" in c["bom-ref"])
    evidence = next(
        e for e in bom["declarations"]["evidence"] if e["bom-ref"] == claim["evidence"][0]
    )
    data = [(d["name"], d["contents"]["attachment"]["content"]) for d in evidence["data"]]
    names = dict(data)
    assert names["whence:verdict"] == "verified"
    assert names["whence:provenance"] == "verified-by-weights"
    assert names["whence:fingerprint-tool"] == "modeldna"
    assert names["whence:fingerprint-class"] == "FINE_TUNE"
    assert names["whence:fingerprint-probability"] == "0.9931"
    assert "Established by a weight-level fingerprint" in claim["reasoning"]
    # The card's locator is still there beside the file's: two records, not a replacement.
    assert [v for n, v in data if n == "whence:locator"] == ["cardData.base_model", "fp.json"]


def test_load_reads_the_file_and_digests_its_bytes(tmp_path: Path) -> None:
    report = _report()
    edge = _declared_edge(report)
    file = _file([_verdict(edge, "FINE_TUNE")])
    path = tmp_path / "fp.json"
    path.write_text(json.dumps(file.model_dump(mode="json")))
    loaded, digest = load(path)
    assert loaded == file
    assert len(digest) == 64
    # An unknown field is a load failure, never silently dropped (DomainModel forbids extras).
    path.write_text(json.dumps({**file.model_dump(mode="json"), "confidence": 1.0}))
    with pytest.raises(ValidationError):
        load(path)


def test_merge_lineage_keeps_its_ceiling_and_composition_when_evidence_lands() -> None:
    """Phase 4 of the fingerprint measurement, pinned: modelDNA read the merge's GGUF as a
    quantized copy of the one parent the card declares five times. The edge moves to `verified`
    with the class verbatim -- the card said `merged-from`, the weights say `QUANTIZED_COPY`, and
    both records stay -- while the node-count ceiling and its `incomplete` composition survive.
    """
    scenario = ROOT / "benchmarks" / "merge-lineage"
    target = yaml.safe_load((scenario / "input" / "target.yaml").read_text())
    report = resolver_for(target, RecordedRegistry(scenario / "recorded")).resolve(
        str(target["target"])
    )
    evidence_path = (
        ROOT / "docs" / "eval" / "fingerprints" / "evidence" / "scenario-merge-lineage.json"
    )
    evidence, digest = load(evidence_path)
    updated, app = apply(report, evidence, str(evidence_path.relative_to(ROOT)), digest)

    mopey = next(
        e for e in updated.edges if e.target.slug == "failspy/Llama-3-8B-Instruct-MopeyMule"
    )
    assert mopey.verdict is Verdict.VERIFIED
    assert mopey.relation.value == "merged-from"
    assert mopey.declared_count == 5
    assert mopey.evidence[-1].verdict_class == "QUANTIZED_COPY"
    # The second declared parent returned NO_MATCH, which the file maps to `abstains`.
    psycho = next(e for e in updated.edges if e.target.slug.startswith("zementalist/"))
    assert psycho.verdict is Verdict.UNVERIFIABLE
    assert app.abstained == 1 and len(app.established) == 1
    # DEC-007 bookkeeping is untouched by evidence.
    assert updated.ceilings_hit == report.ceilings_hit
    bom = to_cyclonedx(updated)
    assert {c["aggregate"] for c in bom["compositions"]} == {"incomplete"}
    failures = score(updated, scenario / "expected", "merge-lineage").honesty_failures
    assert not any("fingerprint" in f for f in failures)
