"""Graph resolution.

Walks a model's declared dependencies, pins every node it can, and records for each edge whether
the relationship was asserted or established. The rules it exists to honour:

  DEC-002  a node is pinned by revision digest, never by name
  DEC-006  no model code is executed; metadata only
  DEC-007  traversal is depth-bounded and names what it did not follow
  DEC-010  what was resolved is reported; nothing is inferred
  DEC-011  a redirect records the name that was declared as well as the one resolved
  DEC-014  a transient failure produces no edge, no verdict, and marks the run partial
  DEC-015  the registry's derivation qualifier selects the relation
  DEC-017  a redirect across namespaces is flagged; the trust anchor moved
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from whence.domain import (
    ArtifactRef,
    Edge,
    Evidence,
    Node,
    ProvenanceClass,
    Relation,
    ResolutionClass,
    ResolutionReport,
    SignatureState,
    Verdict,
    normalize_node_kind,
    now,
)
from whence.registry import Registry

# The registry states the derivation kind; a bare declaration leaves it unspecified and is never
# assumed to be fine-tuning (DEC-015).
QUALIFIER_RELATIONS = {
    "finetune": Relation.DERIVES_FROM,
    "quantized": Relation.QUANTIZED_FROM,
    "merge": Relation.MERGED_FROM,
    "adapter": Relation.ADAPTS,
}


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value if isinstance(v, str)]


def parse_ref(slug: str, host: str, revision: str | None = None) -> ArtifactRef | None:
    """`ns/name` only. A bare name is not resolved by guessing an owner (DEC-010)."""
    if slug.count("/") != 1:
        return None
    namespace, name = slug.split("/", 1)
    if not namespace or not name:
        return None
    return ArtifactRef(
        host=host, namespace=namespace, name=name, revision=revision, pinned=revision is not None
    )


def relation_for(slug: str, tags: list[str]) -> Relation:
    for tag in tags:
        parts = tag.split(":")
        if len(parts) >= 3 and parts[0] == "base_model" and ":".join(parts[2:]) == slug:
            if parts[1] not in QUALIFIER_RELATIONS:
                raise ValueError(
                    f"unrecognized derivation qualifier {parts[1]!r}; Relation is closed by "
                    f"DEC-015 and an unknown kind stops the run rather than normalizing"
                )
            return QUALIFIER_RELATIONS[parts[1]]
    return Relation.DERIVES_FROM


@dataclass
class _State:
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    ceilings: list[str] = field(default_factory=list)
    transient: list[str] = field(default_factory=list)


class Resolver:
    def __init__(
        self, registry: Registry, host: str = "huggingface.co", max_depth: int = 2
    ) -> None:
        self._registry, self._host, self._max_depth = registry, host, max_depth

    # -- node resolution -------------------------------------------------------------------

    def _namespace_state(self, namespace: str) -> str:
        """`free`, `held-empty`, `held`, or `unknown`. Only a free namespace is re-registrable."""
        org = self._registry.get(f"/api/organizations/{namespace}/overview")
        if org.resolution is ResolutionClass.TRANSIENT:
            return "unknown"
        if org.status == 404:
            return "free"
        listing = self._registry.get(f"/api/models?author={namespace}&limit=5")
        if listing.resolution is ResolutionClass.TRANSIENT:
            return "unknown"
        return "held-empty" if isinstance(listing.body, list) and not listing.body else "held"

    def _resolve_artifact(
        self, slug: str, state: _State, *, kind: str
    ) -> tuple[ArtifactRef | None, ArtifactRef | None, ResolutionClass, list[str]]:
        """Returns (resolved, declared_as, class, notes)."""
        declared = parse_ref(slug, self._host)
        if declared is None:
            return None, None, ResolutionClass.CONCLUSIVE, ["reference is not owner/name"]

        endpoint = "datasets" if kind == "dataset" else "models"
        response = self._registry.get(f"/api/{endpoint}/{slug}")

        if response.resolution is ResolutionClass.TRANSIENT:
            state.transient.append(slug)
            return None, None, ResolutionClass.TRANSIENT, []

        if response.redirected:
            target_slug = str(response.location).split(f"/api/{endpoint}/", 1)[-1]
            resolved, _, cls, notes = self._resolve_artifact(target_slug, state, kind=kind)
            if resolved is None:
                return None, declared, cls, notes
            # DEC-017: following a registry-issued redirect is resolution, but a redirect across
            # namespaces changed who controls what the name returns.
            if resolved.namespace != declared.namespace:
                notes = [*notes, f"redirect crosses namespace: {declared.slug} -> {resolved.slug}"]
            return resolved, declared, cls, notes

        if response.status == 200 and isinstance(response.body, dict):
            revision = response.body.get("sha")
            ref = parse_ref(slug, self._host, str(revision) if revision else None)
            notes = []
            if response.body.get("gated") not in (False, None):
                notes.append("gated: weight-level verification unavailable without credentials")
            return ref, None, ResolutionClass.CONCLUSIVE, notes

        # 404, 401, 403: the artifact did not resolve. Absence is reported, never inferred.
        ns = self._namespace_state(declared.namespace)
        notes = [f"namespace-state: {ns}"]
        if ns == "free":
            notes.append("risk: reregistrable-reference")
        return None, declared, response.resolution, notes

    # -- traversal -------------------------------------------------------------------------

    def _declared_edges(self, body: dict[str, Any]) -> list[tuple[str, Relation, str, str]]:
        """(slug, relation, kind, locator). Reads only stated metadata (DEC-010)."""
        card = body.get("cardData") or {}
        tags = [t for t in (body.get("tags") or []) if isinstance(t, str)]
        out: list[tuple[str, Relation, str, str]] = []
        for slug in _as_list(card.get("base_model")):
            out.append((slug, relation_for(slug, tags), "model", "cardData.base_model"))
        for i, slug in enumerate(_as_list(card.get("datasets"))):
            out.append((slug, Relation.TRAINED_ON, "dataset", f"cardData.datasets[{i}]"))
        library = card.get("library_name") or body.get("library_name")
        if isinstance(library, str) and library:
            out.append((library, Relation.REQUIRES_PACKAGE, "package", "cardData.library_name"))
        return out

    def resolve(self, root_slug: str) -> ResolutionReport:
        state = _State()
        root_ref, _, cls, _ = self._resolve_artifact(root_slug, state, kind="model")
        if root_ref is None:
            raise ValueError(f"root {root_slug} did not resolve ({cls.value})")

        frontier = [(root_ref, 0)]
        expanded: set[str] = set()
        while frontier:
            ref, depth = frontier.pop(0)
            if ref.slug in expanded:
                continue
            expanded.add(ref.slug)
            if depth >= self._max_depth:
                state.ceilings.append(f"depth {self._max_depth} reached at {ref.slug}")
                continue
            response = self._registry.get(f"/api/models/{ref.slug}")
            if response.resolution is ResolutionClass.TRANSIENT or not isinstance(
                response.body, dict
            ):
                continue
            for slug, relation, kind, locator in self._declared_edges(response.body):
                self._add_edge(ref, slug, relation, kind, locator, state, frontier, depth)

        return ResolutionReport(
            root=root_ref,
            nodes=tuple(state.nodes.values()),
            edges=tuple(state.edges),
            ceilings_hit=tuple(state.ceilings),
            transient_failures=tuple(dict.fromkeys(state.transient)),
            partial=bool(state.transient),
            captured_at=now(),
        )

    def _add_edge(
        self,
        source: ArtifactRef,
        slug: str,
        relation: Relation,
        kind: str,
        locator: str,
        state: _State,
        frontier: list[tuple[ArtifactRef, int]],
        depth: int,
    ) -> None:
        if kind == "package":
            target = ArtifactRef(host="pypi", namespace="", name=slug, pinned=False)
            self._record_node(
                target, kind, Verdict.UNVERIFIABLE, True, ("no version declared",), state
            )
            state.edges.append(
                Edge(
                    source=source,
                    target=target,
                    relation=relation,
                    provenance=ProvenanceClass.ASSERTED_BY_CONFIG,
                    verdict=Verdict.UNVERIFIABLE,
                    evidence=(Evidence(locator=locator, content_digest=_digest(slug)),),
                )
            )
            return

        resolved, declared, cls, notes = self._resolve_artifact(slug, state, kind=kind)
        if cls is ResolutionClass.TRANSIENT:
            return  # DEC-014: no edge, no verdict.

        evidence = (Evidence(locator=locator, content_digest=_digest(slug)),)
        asserted = (
            ProvenanceClass.ASSERTED_BY_CARD
            if locator.startswith(("cardData.base_model", "cardData.datasets"))
            else ProvenanceClass.ASSERTED_BY_CONFIG
        )
        if resolved is None:
            # DEC-018: provenance records how the CLAIM was found, not whether the TARGET resolved.
            # A card that names a well-formed reference has asserted it, however unreachable that
            # reference turns out to be; the unreachability belongs on the node. `unresolvable` is
            # for a reference that could not be constructed at all.
            if declared is None:
                self._record_node(
                    ArtifactRef(host=self._host, namespace="", name=slug, pinned=False),
                    kind,
                    Verdict.UNVERIFIABLE,
                    False,
                    tuple(notes),
                    state,
                )
                state.edges.append(
                    Edge(
                        source=source,
                        target=ArtifactRef(host=self._host, namespace="", name=slug, pinned=False),
                        relation=relation,
                        provenance=ProvenanceClass.UNRESOLVABLE,
                        verdict=Verdict.UNVERIFIABLE,
                        evidence=evidence,
                    )
                )
                return
            self._record_node(declared, kind, Verdict.UNVERIFIABLE, False, tuple(notes), state)
            state.edges.append(
                Edge(
                    source=source,
                    target=declared,
                    relation=relation,
                    provenance=asserted,
                    verdict=Verdict.UNVERIFIABLE,
                    evidence=evidence,
                )
            )
            return

        self._record_node(resolved, kind, Verdict.UNVERIFIABLE, True, tuple(notes), state)
        state.edges.append(
            Edge(
                source=source,
                target=resolved,
                declared_as=declared,
                relation=relation,
                provenance=asserted,
                # Resolution establishes that the named artifact exists and pins. It does not
                # establish that the derivation happened (DEC-005).
                verdict=Verdict.UNVERIFIABLE,
                evidence=evidence,
            )
        )
        if kind == "model":
            frontier.append((resolved, depth + 1))

    def _record_node(
        self,
        ref: ArtifactRef,
        kind: str,
        verdict: Verdict,
        reachable: bool,
        notes: tuple[str, ...],
        state: _State,
    ) -> None:
        state.nodes.setdefault(
            ref.slug,
            Node(
                ref=ref,
                kind=normalize_node_kind(kind),
                verdict=verdict,
                signature=SignatureState.UNSIGNED,
                reachable=reachable,
                notes=notes,
            ),
        )
