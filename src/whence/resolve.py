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
from whence.signing import detect as detect_signature
from whence.structure import check as structural_check

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
    inconclusive: list[str] = field(default_factory=list)


class Resolver:
    def __init__(
        self,
        registry: Registry,
        host: str = "huggingface.co",
        max_depth: int = 2,
        *,
        check_structure: bool = False,
        check_signatures: bool = False,
    ) -> None:
        self._registry, self._host, self._max_depth = registry, host, max_depth
        # Opt-in: one extra request per resolved model. Detection only -- a present bundle reports
        # `unverifiable`, never `valid` (DEC-021).
        self._check_signatures = check_signatures
        # Structured properties keyed by slug, filled during resolution and consumed by
        # _record_node. Keeps the BOM's facts out of prose notes.
        self._pending_properties: dict[str, tuple[tuple[str, str], ...]] = {}
        # Opt-in: two extra requests per derives-from edge, and the only path that can move an
        # edge's verdict off `unverifiable` -- downward, to `contradicted`, never up (DEC-020).
        self._check_structure = check_structure

    # -- node resolution -------------------------------------------------------------------

    def _namespace_state(self, namespace: str, state: _State) -> str:
        """`free`, `held-empty`, `held`, or `unknown`. Only a free namespace is re-registrable.

        A namespace on this registry may be owned by an organization **or** by a user, and the two
        have separate endpoints. Checking only organizations reports every user-owned namespace as
        free, which would turn an ordinary personal account into a fabricated hijack finding -- the
        most damaging false positive this tool can produce, since it accuses a live owner of having
        abandoned a name. The user endpoint is consulted only when the organization lookup is
        negative, so a held organization costs no extra request.
        """
        org = self._registry.get(f"/api/organizations/{namespace}/overview")
        if org.resolution is ResolutionClass.TRANSIENT:
            # `unknown` reads as "we looked and could not tell". We did not look (DEC-014).
            state.transient.append(f"namespace {namespace}")
            return "unknown"
        if org.status == 404:
            user = self._registry.get(f"/api/users/{namespace}/overview")
            if user.resolution is ResolutionClass.TRANSIENT:
                state.transient.append(f"namespace {namespace}")
                return "unknown"
            if user.status != 404:
                return "held"
            return "free"
        listing = self._registry.get(f"/api/models?author={namespace}&limit=5")
        if listing.resolution is ResolutionClass.TRANSIENT:
            state.transient.append(f"namespace {namespace}")
            return "unknown"
        return "held-empty" if isinstance(listing.body, list) and not listing.body else "held"

    def _resolve_artifact(
        self, slug: str, state: _State, *, kind: str
    ) -> tuple[ArtifactRef | None, ArtifactRef | None, ResolutionClass, list[str]]:
        """Returns (resolved, declared_as, class, notes)."""
        declared = parse_ref(slug, self._host)
        if declared is None:
            return None, None, ResolutionClass.CONCLUSIVE, ["reference is not owner/name"]

        properties: list[tuple[str, str]] = []
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
                properties.append(("whence:access", "gated"))
            # Stashed after every property is collected, not before.
            if ref is not None:
                self._pending_properties[ref.slug] = tuple(properties)
            return ref, None, ResolutionClass.CONCLUSIVE, notes

        # 404, 401, 403: the artifact did not resolve. Absence is reported, never inferred.
        # DEC-014's inconclusive class: attempted and not settled. Recorded so the BOM can carry
        # `compositions.aggregate: unknown`, which mapping section 6 requires and which was never
        # emitted -- every 401 produced no composition at all.
        if response.resolution is ResolutionClass.INCONCLUSIVE:
            state.inconclusive.append(declared.slug)
        ns = self._namespace_state(declared.namespace, state)
        notes = [f"namespace-state: {ns}"]
        properties.append(("whence:namespace-state", ns))
        if ns == "free":
            notes.append("risk: reregistrable-reference")
            properties.append(("whence:risk", "reregistrable-reference"))
        self._pending_properties[declared.slug] = tuple(properties)
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

        # The root is a node like any other. It was previously recorded only as `report.root`, so
        # anything computed per node -- signature state above all -- never applied to the artifact
        # the caller actually asked about.
        self._record_node(root_ref, "model", Verdict.UNVERIFIABLE, True, (), state)

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
            if response.resolution is ResolutionClass.TRANSIENT:
                # Previously folded into the check below and `continue`d without recording, so the
                # branch was dropped and the run was NOT marked partial -- a silently truncated
                # graph presented as whole, which is what DEC-014's partial marker prevents.
                state.transient.append(ref.slug)
                continue
            if not isinstance(response.body, dict):
                continue
            for slug, relation, kind, locator in self._declared_edges(response.body):
                self._add_edge(ref, slug, relation, kind, locator, state, frontier, depth)

        return ResolutionReport(
            root=root_ref,
            nodes=tuple(state.nodes.values()),
            edges=tuple(state.edges),
            ceilings_hit=tuple(state.ceilings),
            transient_failures=tuple(dict.fromkeys(state.transient)),
            inconclusive=tuple(dict.fromkeys(state.inconclusive)),
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

        verdict = Verdict.UNVERIFIABLE
        if self._check_structure and kind == "model":
            outcome = structural_check(self._registry, source, resolved, relation)
            verdict = outcome.verdict
            if outcome.detail:
                notes = [*notes, f"structure: {outcome.detail}"]

        self._record_node(resolved, kind, Verdict.UNVERIFIABLE, True, tuple(notes), state)
        state.edges.append(
            Edge(
                source=source,
                target=resolved,
                declared_as=declared,
                relation=relation,
                provenance=asserted,
                # Resolution establishes that the named artifact exists and pins. It does not
                # establish that the derivation happened (DEC-005). Only the structural check can
                # move this, and only downward, to `contradicted` (DEC-020).
                verdict=verdict,
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
        if ref.slug in state.nodes:
            return
        # Not checked is `unverifiable`, not `unsigned`. `unsigned` is a statement about the
        # publisher, and the default path never looked -- so every BOM asserted an unmeasured
        # negative as fact, the one thing this project forbids everywhere else.
        signature = SignatureState.UNVERIFIABLE
        signature_note = "signatures were not checked; pass --check-signatures to look"
        if self._check_signatures and kind == "model" and reachable:
            signature, signature_note = detect_signature(self._registry, ref)
        if kind == "model":
            notes = (*notes, f"signature: {signature_note}")
        properties = list(self._pending_properties.pop(ref.slug, ()))
        if not ref.pinned and kind == "package":
            properties.append(("whence:unpinned-reason", "no version declared in source metadata"))
        state.nodes[ref.slug] = Node(
            ref=ref,
            kind=normalize_node_kind(kind),
            verdict=verdict,
            signature=signature,
            reachable=reachable,
            notes=notes,
            properties=tuple(properties),
        )
