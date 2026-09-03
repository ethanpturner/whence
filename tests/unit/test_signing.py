"""OMS signature detection.

Detection, not verification (DEC-021): a present bundle is `unverifiable`, never `valid`.
"""

from __future__ import annotations

from typing import Any

from whence.domain import ArtifactRef, SignatureState
from whence.registry import Response
from whence.signing import detect

BUNDLE = {
    "mediaType": "application/vnd.dev.sigstore.bundle.v0.3+json",
    "dsseEnvelope": {"payload": "...", "signatures": [{"sig": "..."}]},
    "verificationMaterial": {"certificate": {}, "tlogEntries": []},
}


def ref(slug: str = "a/b") -> ArtifactRef:
    namespace, name = slug.split("/")
    return ArtifactRef(host="huggingface.co", namespace=namespace, name=name, pinned=False)


class _Registry:
    def __init__(self, status: int, body: Any = None) -> None:
        self._status, self._body = status, body

    def get(self, path: str) -> Response:
        return Response(status=self._status, body=self._body)


def test_a_present_bundle_is_unverifiable_never_valid() -> None:
    """The whole point. Reporting a present-but-unchecked signature as `valid` would be the
    transcription-as-verification error this project exists to correct, committed about the one
    artifact whose entire purpose is verification."""
    state, note = detect(_Registry(200, BUNDLE), ref())
    assert state is SignatureState.UNVERIFIABLE
    assert "has not been verified" in note


def test_absence_is_unsigned_and_that_is_conclusive() -> None:
    """`unsigned` is a statement about the publisher, not about a signature's validity, and it is
    the one thing detection can actually establish."""
    state, note = detect(_Registry(404), ref())
    assert state is SignatureState.UNSIGNED
    assert "no model.sig" in note


def test_a_non_bundle_file_is_not_treated_as_a_signature() -> None:
    state, note = detect(_Registry(200, {"mediaType": "text/plain"}), ref())
    assert state is SignatureState.UNVERIFIABLE
    assert "not a Sigstore bundle" in note


def test_a_structurally_incomplete_bundle_is_flagged() -> None:
    state, note = detect(_Registry(200, {"mediaType": BUNDLE["mediaType"]}), ref())
    assert state is SignatureState.UNVERIFIABLE
    assert "structurally incomplete" in note


def test_a_transient_failure_produces_no_conclusion() -> None:
    """DEC-014 applies here too: a rate limit is a fact about the client."""
    state, note = detect(_Registry(429), ref())
    assert state is SignatureState.UNVERIFIABLE
    assert "no conclusion drawn" in note
