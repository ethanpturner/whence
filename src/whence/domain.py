"""Domain objects.

`docs/architecture/data-model.md` is authoritative for field names, types, and enumerations. This
module conforms to it; it does not define its own shape. Every object is frozen and forbids unknown
fields, so a registry response carrying an unexpected key fails validation rather than passing
downstream stripped of it and looking valid.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, model_validator


def now() -> datetime:
    """The single clock. Never call `datetime.now` directly: recorded fixtures replay against this."""
    return datetime.now(UTC)


class DomainModel(BaseModel):
    """Frozen, and unknown fields are a validation failure rather than silently dropped."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class Verdict(StrEnum):
    """Three-valued, never boolean (DEC-001)."""

    VERIFIED = "verified"
    CONTRADICTED = "contradicted"
    UNVERIFIABLE = "unverifiable"


class ProvenanceClass(StrEnum):
    """How a relationship was established (DEC-004). Required on every edge."""

    ASSERTED_BY_CARD = "asserted-by-card"
    ASSERTED_BY_CONFIG = "asserted-by-config"
    VERIFIED_BY_DIGEST = "verified-by-digest"
    VERIFIED_BY_WEIGHTS = "verified-by-weights"
    UNRESOLVABLE = "unresolvable"


class SignatureState(StrEnum):
    """An unsigned artifact is `unsigned`, never `invalid`. The distinction is not cosmetic."""

    UNSIGNED = "unsigned"
    VALID = "valid"
    INVALID = "invalid"
    UNVERIFIABLE = "unverifiable"


class Relation(StrEnum):
    """Closed (DEC-015). An unrecognized relation stops the run rather than normalizing."""

    DERIVES_FROM = "derives-from"
    QUANTIZED_FROM = "quantized-from"
    #: Trained on a teacher model's outputs. Distinct from DERIVES_FROM because the student's
    #: weights are not derived from the teacher's at all -- no weight-level method can ever confirm
    #: it, where a fine-tune at least leaves something to compare (DEC-027).
    DISTILLED_FROM = "distilled-from"
    MERGED_FROM = "merged-from"
    ADAPTS = "adapts"
    TOKENIZED_BY = "tokenized-by"
    TRAINED_ON = "trained-on"
    REQUIRES_PACKAGE = "requires-package"


class EvidenceEffect(StrEnum):
    """What a fingerprint verdict class does to an edge's verdict (DEC-029). Declared per class by
    whoever ran the tool; a class with no declared effect is a validation failure, never a default,
    because a tool's own negative is not this tool's `contradicted`."""

    ESTABLISHES = "establishes"
    CONTRADICTS = "contradicts"
    ABSTAINS = "abstains"


class ResolutionClass(StrEnum):
    """Only the first two may produce a verdict (DEC-014)."""

    CONCLUSIVE = "conclusive"
    INCONCLUSIVE = "inconclusive"
    TRANSIENT = "transient"


# `NodeKind` is an open vocabulary (data-model.md §7): a registry naming a kind this list does not
# carry is normalized, not rejected. Provenance for an unfamiliar artifact type is still provenance.
KNOWN_NODE_KINDS = frozenset({"model", "dataset", "adapter", "tokenizer", "package"})


def normalize_node_kind(raw: str) -> str:
    return raw.strip().lower().replace("_", "-")


class ArtifactRef(DomainModel):
    """A reference. Without a revision it is a name, not an identity (DEC-002)."""

    host: str
    namespace: str
    name: str
    revision: str | None = None
    pinned: bool

    @model_validator(mode="after")
    def _pinned_iff_revision(self) -> ArtifactRef:
        if self.pinned != (self.revision is not None):
            raise ValueError("pinned must be true exactly when a revision is present (DEC-002)")
        return self

    @property
    def slug(self) -> str:
        return f"{self.namespace}/{self.name}" if self.namespace else self.name

    def purl(self, purl_type: str | None = None) -> str:
        """`pkg:huggingface/<ns>/<name>@<sha>`. Unpinned refs carry no version (DEC-013)."""
        kind = purl_type or ("pypi" if self.host == "pypi" else "huggingface")
        base = f"pkg:{kind}/{self.slug}"
        return f"{base}@{self.revision}" if self.revision else base


class Evidence(DomainModel):
    """Where an assertion was found. `excerpt` is untrusted data (DEC-012).

    The four optional `tool*` fields are set only on evidence derived from a fingerprint evidence
    file (DEC-029): they name the external tool, its version, and its verdict class verbatim, with
    the probability as an attribute and never a verdict (DEC-001). Card evidence leaves them unset.
    """

    locator: str
    content_digest: str
    excerpt: str | None = None
    excerpt_truncated: bool = False
    tool: str | None = None
    tool_version: str | None = None
    verdict_class: str | None = None
    probability: float | None = None

    @model_validator(mode="after")
    def _fingerprint_fields_travel_together(self) -> Evidence:
        fingerprint = (self.tool, self.tool_version, self.verdict_class)
        if any(f is not None for f in fingerprint) and not all(f is not None for f in fingerprint):
            raise ValueError("tool, tool_version and verdict_class are set together or not at all")
        if self.probability is not None and self.tool is None:
            raise ValueError(
                "a probability is an attribute of a fingerprint verdict; no tool named"
            )
        if self.probability is not None and not 0.0 <= self.probability <= 1.0:
            raise ValueError("probability must lie in [0, 1]")
        return self

    @property
    def from_fingerprint(self) -> bool:
        return self.tool is not None


class Node(DomainModel):
    ref: ArtifactRef
    kind: str
    verdict: Verdict
    signature: SignatureState
    reachable: bool
    notes: tuple[str, ...] = ()
    #: Structured facts for the BOM, as (key, value) pairs. Separate from `notes`, which is prose
    #: for a human. They were previously derived by splitting a note on ": ", which produced a
    #: property literally named `whence:no version declared` whenever a note had no colon, and
    #: silently invented a namespaced key whenever one did.
    properties: tuple[tuple[str, str], ...] = ()


class Edge(DomainModel):
    source: ArtifactRef
    target: ArtifactRef
    declared_as: ArtifactRef | None = None
    relation: Relation
    provenance: ProvenanceClass
    verdict: Verdict
    evidence: tuple[Evidence, ...] = ()
    #: How many times the source declared this same relation to this same target. Normally 1. A
    #: mergekit card emits one `base_model` entry per merge slice, so a parent weighted across five
    #: slices is declared five times -- which is a fact about the recipe, not five dependencies.
    #: Emitting five identical edges overstated the graph; the count carries what they meant.
    declared_count: int = 1

    @model_validator(mode="after")
    def _rules(self) -> Edge:
        # An unresolvable edge cannot be anything but unverifiable (data-model.md §11).
        if (
            self.provenance is ProvenanceClass.UNRESOLVABLE
            and self.verdict is not Verdict.UNVERIFIABLE
        ):
            raise ValueError("an unresolvable edge must be unverifiable")
        if self.provenance is not ProvenanceClass.UNRESOLVABLE and not self.evidence:
            raise ValueError("only an unresolvable edge may carry no evidence")
        # Populating declared_as with a copy of target would make a rename indistinguishable
        # from a direct hit (DEC-011).
        if self.declared_as is not None and self.declared_as.slug == self.target.slug:
            raise ValueError("declared_as is populated only when it differs from target")
        return self

    @property
    def crosses_namespace(self) -> bool:
        """A redirect across ownership is not a rename; the trust anchor moved (DEC-017)."""
        return self.declared_as is not None and self.declared_as.namespace != self.target.namespace


class ResolutionReport(DomainModel):
    root: ArtifactRef
    nodes: tuple[Node, ...]
    edges: tuple[Edge, ...]
    ceilings_hit: tuple[str, ...]
    transient_failures: tuple[str, ...]
    #: References whose resolution was attempted and inconclusive -- a 401 or 403. Distinct from a
    #: ceiling, which is a stop the tool chose, and from a transient failure, which produced no
    #: verdict at all. Maps to `compositions.aggregate: unknown` (DEC-014, mapping section 6).
    inconclusive: tuple[str, ...] = ()
    partial: bool
    captured_at: datetime

    @model_validator(mode="after")
    def _partial_iff_transient(self) -> ResolutionReport:
        if self.partial != bool(self.transient_failures):
            raise ValueError(
                "partial must be true exactly when transient failures occurred (DEC-014)"
            )
        return self


class FingerprintVerdict(DomainModel):
    """One statement by an external weight-level tool about one ordered pair (DEC-029).

    Both sides are pinned or the verdict fails validation: a fingerprint is a statement about bytes,
    and a name is not bytes (DEC-002). `verdict_class` is the tool's own class, verbatim -- never
    normalized and never mapped to a `Relation` (DEC-010, DEC-015).
    """

    subject: ArtifactRef
    candidate: ArtifactRef
    verdict_class: str
    probability: float | None = None
    detail: str | None = None

    @model_validator(mode="after")
    def _both_sides_pinned(self) -> FingerprintVerdict:
        if not self.subject.pinned or not self.candidate.pinned:
            raise ValueError(
                "a fingerprint verdict names two pinned artifacts; an unpinned side is a verdict "
                "about whatever the name resolves to today (DEC-002)"
            )
        if self.probability is not None and not 0.0 <= self.probability <= 1.0:
            raise ValueError("probability must lie in [0, 1]")
        return self


class FingerprintEvidenceFile(DomainModel):
    """The output of an external fingerprint tool, read as inert data (DEC-029).

    `classes` declares the effect of every verdict class the tool uses. Every class that appears in
    `verdicts` must be declared, so that a class nobody thought about cannot default to anything.
    """

    tool: str
    tool_version: str
    generated_at: datetime
    classes: tuple[tuple[str, EvidenceEffect], ...]
    verdicts: tuple[FingerprintVerdict, ...]

    @model_validator(mode="after")
    def _every_class_declared(self) -> FingerprintEvidenceFile:
        declared = dict(self.classes)
        if len(declared) != len(self.classes):
            raise ValueError("a verdict class is declared twice with possibly different effects")
        undeclared = sorted({v.verdict_class for v in self.verdicts} - set(declared))
        if undeclared:
            raise ValueError(
                f"verdict class(es) {', '.join(undeclared)} carry no declared effect; an effect is "
                "declared by whoever ran the tool, never defaulted (DEC-029)"
            )
        return self

    def effect_of(self, verdict_class: str) -> EvidenceEffect:
        return dict(self.classes)[verdict_class]
