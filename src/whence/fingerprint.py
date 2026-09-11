"""Fingerprint evidence ingest (DEC-029).

An external weight-level tool runs as a separate process and writes a `FingerprintEvidenceFile`.
This module reads that file as inert data and applies each verdict to the graph under the effect
the file declares for its class. `whence` still downloads no weights and executes no model code
(DEC-005, DEC-006); everything here is bookkeeping over JSON somebody else produced.

What a verdict can do, and what it cannot:

  establishes  a declared edge between the two pinned artifacts moves to `verified` with
               provenance `verified-by-weights`; the card's own evidence stays on the edge as a
               second record, so a reader sees what was claimed and what established it. Where no
               card declares the edge and both artifacts are nodes the resolution reached, the
               edge is created with the fingerprint as its only evidence -- the undeclared lineage
               DEC-005 named. An edge the structural check already contradicted is not raised: a
               body that differs is not the body the tool sampled from, and both records stay.
  contradicts  a declared edge moves to `contradicted` and the evidence is appended. A pair no
               card declares is recorded nowhere on the graph: there is no claim to contradict.
  abstains     nothing on the graph changes.

A verdict naming an artifact the resolution did not reach, or naming it at a different revision,
is **unattached**: reported, counted, and never used to invent a node (DEC-010). The application
report says how many verdicts landed where, so a file that attached nothing is visible as such.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from whence.domain import (
    ArtifactRef,
    Edge,
    Evidence,
    EvidenceEffect,
    FingerprintEvidenceFile,
    FingerprintVerdict,
    ProvenanceClass,
    Relation,
    ResolutionReport,
    Verdict,
)


@dataclass
class Application:
    """What one evidence file did to one report."""

    locator: str
    content_digest: str
    tool: str
    established: list[str] = field(default_factory=list)
    created: list[str] = field(default_factory=list)
    contradicted: list[str] = field(default_factory=list)
    conflicting: list[str] = field(default_factory=list)
    abstained: int = 0
    unattached: list[str] = field(default_factory=list)

    @property
    def attached(self) -> int:
        return len(self.established) + len(self.created) + len(self.contradicted)


def load(path: Path) -> tuple[FingerprintEvidenceFile, str]:
    """Parse an evidence file and return it with the digest of its bytes.

    The digest travels onto every `Evidence` the file produces, so a `verified` edge is auditable to
    the exact file that established it. `model_validate_json` is used so an unknown field fails the
    load rather than passing stripped (DomainModel forbids extras).
    """
    raw = path.read_bytes()
    parsed = FingerprintEvidenceFile.model_validate_json(raw)
    return parsed, hashlib.sha256(raw).hexdigest()


def _same(a: ArtifactRef, b: ArtifactRef) -> bool:
    return a.slug == b.slug and a.revision == b.revision


def _evidence(
    verdict: FingerprintVerdict, file: FingerprintEvidenceFile, app: Application
) -> Evidence:
    return Evidence(
        locator=app.locator,
        content_digest=app.content_digest,
        # The tool's prose about the pair is untrusted text (DEC-012): bounded, rendered only.
        excerpt=(verdict.detail[:500] if verdict.detail else None),
        excerpt_truncated=bool(verdict.detail and len(verdict.detail) > 500),
        tool=file.tool,
        tool_version=file.tool_version,
        verdict_class=verdict.verdict_class,
        probability=verdict.probability,
    )


def _key(verdict: FingerprintVerdict) -> str:
    return f"{verdict.subject.slug} ~ {verdict.candidate.slug} [{verdict.verdict_class}]"


def apply(
    report: ResolutionReport, file: FingerprintEvidenceFile, locator: str, content_digest: str
) -> tuple[ResolutionReport, Application]:
    app = Application(locator=locator, content_digest=content_digest, tool=file.tool)
    edges = list(report.edges)
    nodes = {n.ref.slug: n for n in report.nodes}

    for verdict in file.verdicts:
        effect = file.effect_of(verdict.verdict_class)
        if effect is EvidenceEffect.ABSTAINS:
            app.abstained += 1
            continue

        subject_node = nodes.get(verdict.subject.slug)
        candidate_node = nodes.get(verdict.candidate.slug)
        for side, ref, node in (
            ("subject", verdict.subject, subject_node),
            ("candidate", verdict.candidate, candidate_node),
        ):
            if node is None:
                app.unattached.append(
                    f"{_key(verdict)}: {side} {ref.slug} is not an artifact this resolution reached"
                )
                break
            if node.ref.revision != ref.revision:
                app.unattached.append(
                    f"{_key(verdict)}: {side} {ref.slug} was fingerprinted at revision "
                    f"{ref.revision}, and the graph pins {node.ref.revision}; a fingerprint is a "
                    "statement about bytes and these are different bytes"
                )
                break
        else:
            index = next(
                (
                    i
                    for i, e in enumerate(edges)
                    if _same(e.source, verdict.subject) and _same(e.target, verdict.candidate)
                ),
                -1,
            )
            evidence = _evidence(verdict, file, app)
            if index < 0:
                if effect is EvidenceEffect.CONTRADICTS:
                    app.unattached.append(
                        f"{_key(verdict)}: no card declares this edge, so there is no claim to "
                        "contradict; recorded nowhere on the graph"
                    )
                    continue
                edges.append(
                    Edge(
                        source=verdict.subject,
                        target=verdict.candidate,
                        relation=Relation.DERIVES_FROM,
                        provenance=ProvenanceClass.VERIFIED_BY_WEIGHTS,
                        verdict=Verdict.VERIFIED,
                        evidence=(evidence,),
                    )
                )
                app.created.append(_key(verdict))
                continue

            edge = edges[index]
            if effect is EvidenceEffect.CONTRADICTS:
                edges[index] = Edge.model_validate(
                    {
                        **edge.model_dump(),
                        "verdict": Verdict.CONTRADICTED,
                        "evidence": (*edge.evidence, evidence),
                    }
                )
                app.contradicted.append(_key(verdict))
            elif edge.verdict is Verdict.CONTRADICTED:
                # The body check already refuted the declared relation. A fingerprint that says
                # otherwise is recorded, and the edge is not raised: two established sources
                # disagree, which DEC-029 leaves open, and this is the visible form of that.
                edges[index] = Edge.model_validate(
                    {**edge.model_dump(), "evidence": (*edge.evidence, evidence)}
                )
                app.conflicting.append(_key(verdict))
            else:
                edges[index] = Edge.model_validate(
                    {
                        **edge.model_dump(),
                        "verdict": Verdict.VERIFIED,
                        "provenance": ProvenanceClass.VERIFIED_BY_WEIGHTS,
                        "evidence": (*edge.evidence, evidence),
                    }
                )
                app.established.append(_key(verdict))

    updated = ResolutionReport.model_validate({**report.model_dump(), "edges": tuple(edges)})
    return updated, app


def summary_lines(app: Application) -> list[str]:
    """Human-readable account of an application, one fact per line, no excerpt content."""
    head = (
        f"evidence: {app.locator} ({app.tool}) sha256:{app.content_digest[:12]} -- "
        f"{app.attached} attached, {app.abstained} abstained, {len(app.unattached)} unattached"
    )
    lines = [head]
    lines.extend(f"  established: {k}" for k in app.established)
    lines.extend(f"  created:     {k}" for k in app.created)
    lines.extend(f"  contradicted:{k}" for k in app.contradicted)
    lines.extend(f"  conflicting: {k} (edge stays contradicted)" for k in app.conflicting)
    lines.extend(f"  unattached:  {k}" for k in app.unattached)
    return lines


def to_json(file: FingerprintEvidenceFile) -> str:
    """Serialize an evidence file the way `load` reads it back. Used by the converter script."""
    return json.dumps(file.model_dump(mode="json"), indent=2) + "\n"
