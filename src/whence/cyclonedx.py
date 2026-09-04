"""CycloneDX 1.7 emission, per DEC-013 and `docs/architecture/cyclonedx-mapping.md`.

Topology goes in `dependencies`, meaning goes in `declarations`, and incompleteness goes in
`compositions`. A `dependency` has no `bom-ref` and no `properties`, so an edge can be neither
addressed nor annotated; claims are joined to edges by predicate instead. That cost is recorded
upstream at CycloneDX/specification#135.

`conformance.score` is deliberately unused: it is a 0-to-1 number, and mapping a three-valued
verdict onto it would put "not determined" on the same axis as "not derived".
"""

from __future__ import annotations

import hashlib
from typing import Any

from whence.domain import Edge, Node, ResolutionReport

_TYPES = {"model": "machine-learning-model", "dataset": "data", "package": "library"}


def _component(node: Node) -> dict[str, Any]:
    ref = node.ref
    properties = [
        {"name": "whence:pinned", "value": "true" if ref.pinned else "false"},
        {"name": "whence:signature-state", "value": node.signature.value},
        {"name": "whence:reachable", "value": "true" if node.reachable else "false"},
    ]
    # Structured properties, not prose split on a colon. The old mechanism emitted a property
    # literally named `whence:no version declared` for any note without a colon, and invented a
    # namespaced key for any note that happened to contain one.
    properties.extend({"name": name, "value": value} for name, value in node.properties)
    component: dict[str, Any] = {
        "bom-ref": ref.purl(),
        "type": _TYPES.get(node.kind, "library"),
        "name": ref.name,
        "purl": ref.purl(),
        "properties": properties,
    }
    if ref.namespace:
        component["group"] = ref.namespace
    if ref.revision:
        component["version"] = ref.revision
    return component


def _claim_digest(edge: Edge) -> str:
    """A short, stable identifier for one claim: source, relation, and target as emitted."""
    material = f"{edge.source.purl()}|{edge.relation.value}|{edge.target.purl()}"
    return hashlib.sha256(material.encode()).hexdigest()[:12]


def _evidence_data(name: str, value: str) -> dict[str, Any]:
    return {
        "name": name,
        "contents": {"attachment": {"contentType": "text/plain", "content": value}},
    }


def _claim(edge: Edge, index: int) -> tuple[dict[str, Any], dict[str, Any]]:
    evidence_ref = f"evidence-{edge.relation.value}-{index}"
    data = [
        _evidence_data("whence:provenance", edge.provenance.value),
        _evidence_data("whence:verdict", edge.verdict.value),
    ]
    if edge.declared_as is not None:
        data.append(_evidence_data("whence:declared-as", edge.declared_as.purl()))
        if edge.crosses_namespace:
            data.append(_evidence_data("whence:redirect", "cross-namespace"))
            data.append(_evidence_data("whence:risk", "ownership-boundary-crossed"))
    for item in edge.evidence:
        data.append(_evidence_data("whence:locator", item.locator))
    if edge.declared_count > 1:
        # The card asserted this same relationship more than once. A merge recipe does it once per
        # slice, so the number says how much of the merge this parent accounts for -- information
        # that was previously carried, wrongly, as repeated identical claims.
        data.append(_evidence_data("whence:declared-count", str(edge.declared_count)))
    claim = {
        # Derived from what the claim is about, not from its position in the list. An index-based
        # ref moves for every claim after any upstream change, so a diff of two BOMs shows every
        # later claim as modified and a reference held elsewhere silently points at a different
        # claim. The digest keeps the ref stable and the relation keeps it readable.
        "bom-ref": f"claim-{edge.relation.value}-{_claim_digest(edge)}",
        "target": edge.source.purl(),
        "predicate": f"{edge.relation.value} {edge.target.purl()}",
        "reasoning": _reasoning(edge),
        "evidence": [evidence_ref],
    }
    evidence = {
        "bom-ref": evidence_ref,
        "propertyName": "whence:edge",
        "description": f"Provenance and verdict for {claim['bom-ref']}.",
        "data": data,
    }
    return claim, evidence


def _reasoning(edge: Edge) -> str:
    if edge.provenance.value.startswith("asserted"):
        base = (
            "Declared in source metadata with no revision attached. The named artifact resolves and "
            "pins, so the reference is to a real artifact; the derivation itself is not established."
        )
    else:
        base = "The declared reference did not resolve, so no stronger provenance is reachable."
    if edge.crosses_namespace and edge.declared_as is not None:
        base += (
            f" Declared as {edge.declared_as.slug} and resolved by registry redirect to "
            f"{edge.target.slug}, which is a different namespace: the trust anchor moved."
        )
    return base


def to_cyclonedx(report: ResolutionReport) -> dict[str, Any]:
    by_slug = {n.ref.slug: n for n in report.nodes}
    root = next((n for n in report.nodes if n.ref.slug == report.root.slug), None)

    depends: dict[str, list[str]] = {}
    for edge in report.edges:
        depends.setdefault(edge.source.purl(), []).append(edge.target.purl())
    for node in report.nodes:
        depends.setdefault(node.ref.purl(), [])
    depends.setdefault(report.root.purl(), [])

    claims, evidences = [], []
    for index, edge in enumerate(report.edges, start=1):
        claim, evidence = _claim(edge, index)
        claims.append(claim)
        evidences.append(evidence)

    bom: dict[str, Any] = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.7",
        "version": 1,
        "metadata": {
            "timestamp": report.captured_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "component": _component(root)
            if root
            else {
                "bom-ref": report.root.purl(),
                "type": "machine-learning-model",
                "name": report.root.name,
                "purl": report.root.purl(),
            },
        },
        "components": [_component(n) for n in report.nodes if n.ref.slug != report.root.slug],
        "dependencies": [
            {"ref": ref, **({"dependsOn": sorted(set(on))} if on else {})}
            for ref, on in sorted(depends.items())
        ],
        "declarations": {"claims": claims, "evidence": evidences},
    }

    compositions = []
    if report.ceilings_hit:
        # A ceiling is a stop the tool chose (DEC-007), which is `incomplete`.
        scoped = [
            by_slug[s].ref.purl() for s in by_slug if any(s in c for c in report.ceilings_hit)
        ]
        compositions.append(
            {
                "bom-ref": "composition-depth-ceiling",
                "aggregate": "incomplete",
                "dependencies": scoped,
            }
        )
    if report.inconclusive:
        # Attempted and not settled -- a 401 or 403. Distinct from `incomplete`, which is a stop the
        # tool chose. Mapping section 6 and DEC-014's table both require this, and it was never
        # emitted: every scenario resolving a 401 produced `"compositions": null`.
        unresolved = [by_slug[s].ref.purl() for s in report.inconclusive if s in by_slug]
        if unresolved:
            compositions.append(
                {
                    "bom-ref": "composition-inconclusive",
                    "aggregate": "unknown",
                    "dependencies": unresolved,
                }
            )
    if compositions:
        bom["compositions"] = compositions
    if report.partial:
        # DEC-014: a partial run's silence is not a pass, and the BOM must say so.
        bom["metadata"].setdefault("properties", []).extend(
            [{"name": "whence:partial", "value": "true"}]
            + [{"name": "whence:unreached", "value": r} for r in report.transient_failures]
        )
    return bom
