"""The domain invariants that make a wrong object unrepresentable rather than merely discouraged."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from whence.domain import (
    ArtifactRef,
    Edge,
    Evidence,
    ProvenanceClass,
    Relation,
    ResolutionReport,
    Verdict,
    now,
)

PINNED = ArtifactRef(host="h", namespace="ns", name="m", revision="abc123", pinned=True)
UNPINNED = ArtifactRef(host="h", namespace="ns", name="other", pinned=False)
EVIDENCE = (Evidence(locator="cardData.base_model", content_digest="d"),)


def test_pinned_requires_a_revision() -> None:
    with pytest.raises(ValidationError, match="pinned must be true exactly"):
        ArtifactRef(host="h", namespace="ns", name="m", revision="abc", pinned=False)
    with pytest.raises(ValidationError, match="pinned must be true exactly"):
        ArtifactRef(host="h", namespace="ns", name="m", pinned=True)


def test_purl_omits_version_when_unpinned() -> None:
    assert PINNED.purl() == "pkg:huggingface/ns/m@abc123"
    assert UNPINNED.purl() == "pkg:huggingface/ns/other"


def test_unresolvable_edge_cannot_carry_a_stronger_verdict() -> None:
    with pytest.raises(ValidationError, match="unresolvable edge must be unverifiable"):
        Edge(
            source=PINNED,
            target=UNPINNED,
            relation=Relation.DERIVES_FROM,
            provenance=ProvenanceClass.UNRESOLVABLE,
            verdict=Verdict.VERIFIED,
        )


def test_declared_as_must_differ_from_target() -> None:
    """Populating it with a copy would make a rename indistinguishable from a direct hit."""
    with pytest.raises(ValidationError, match="declared_as is populated only when it differs"):
        Edge(
            source=PINNED,
            target=UNPINNED,
            declared_as=UNPINNED,
            relation=Relation.DERIVES_FROM,
            provenance=ProvenanceClass.ASSERTED_BY_CARD,
            verdict=Verdict.UNVERIFIABLE,
            evidence=EVIDENCE,
        )


def test_cross_namespace_redirect_is_flagged() -> None:
    elsewhere = ArtifactRef(host="h", namespace="other-ns", name="other", pinned=False)
    edge = Edge(
        source=PINNED,
        target=UNPINNED,
        declared_as=elsewhere,
        relation=Relation.DERIVES_FROM,
        provenance=ProvenanceClass.ASSERTED_BY_CARD,
        verdict=Verdict.UNVERIFIABLE,
        evidence=EVIDENCE,
    )
    assert edge.crosses_namespace
    same = Edge(
        source=PINNED,
        target=UNPINNED,
        declared_as=ArtifactRef(host="h", namespace="ns", name="renamed", pinned=False),
        relation=Relation.DERIVES_FROM,
        provenance=ProvenanceClass.ASSERTED_BY_CARD,
        verdict=Verdict.UNVERIFIABLE,
        evidence=EVIDENCE,
    )
    assert not same.crosses_namespace


def test_partial_is_true_exactly_when_something_was_unreached() -> None:
    with pytest.raises(ValidationError, match="partial must be true exactly"):
        ResolutionReport(
            root=PINNED,
            nodes=(),
            edges=(),
            ceilings_hit=(),
            transient_failures=("a/b",),
            partial=False,
            captured_at=now(),
        )


def test_objects_are_frozen_and_reject_unknown_fields() -> None:
    """Both of these are also static errors, which is the point: mypy and the runtime agree that
    the object cannot be built or mutated. The ignores are deliberate -- the test asserts the
    runtime guard holds for callers who are not type-checked, such as registry JSON."""
    with pytest.raises(ValidationError):
        ArtifactRef(host="h", namespace="n", name="m", pinned=False, invented="x")  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        PINNED.host = "other"  # type: ignore[misc]
