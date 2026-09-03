"""CycloneDX 1.7 emission, per DEC-013 and `docs/architecture/cyclonedx-mapping.md`.

Topology goes in `dependencies`, meaning goes in `declarations`, and incompleteness goes in
`compositions`. A `dependency` has no `bom-ref` and no `properties`, so an edge can be neither
addressed nor annotated; claims are joined to edges by predicate instead. That cost is recorded
upstream at CycloneDX/specification#135.

`conformance.score` is deliberately unused: it is a 0-to-1 number, and mapping a three-valued
verdict onto it would put "not determined" on the same axis as "not derived".
"""

from __future__ import annotations

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
    for note in node.notes:
        key, _, value = note.partition(": ")
        properties.append({"name": f"whence:{key.strip()}", "value": (value or note).strip()})
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
    claim = {
        "bom-ref": f"claim-{edge.relation.value}-{index}",
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
    if compositions:
        bom["compositions"] = compositions
    if report.partial:
        # DEC-014: a partial run's silence is not a pass, and the BOM must say so.
        bom["metadata"].setdefault("properties", []).extend(
            [{"name": "whence:partial", "value": "true"}]
            + [{"name": "whence:unreached", "value": r} for r in report.transient_failures]
        )
    return bom
