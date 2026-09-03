"""OpenSSF Model Signing (OMS) detection.

A signed model carries `model.sig`: a Sigstore bundle
(`application/vnd.dev.sigstore.bundle.v0.3+json`) wrapping a DSSE envelope whose payload is an
in-toto statement over the model's files.

**Detection, not verification** (DEC-021). Presence establishes that the publisher signed something;
it does not establish that the signature is valid, that it covers the files in front of you, or that
the identity it binds is one you trust. Reporting a present-but-unchecked signature as `valid` would
be the transcription-as-verification error this project exists to correct, committed about the one
artifact whose entire purpose is verification.

So a model with a bundle is `unverifiable` and a model without one is `unsigned`, and the difference
between those two is worth surfacing on its own: it separates publishers who sign from publishers
who do not, which is currently about 1 in 700.
"""

from __future__ import annotations

from typing import Any

from whence.domain import ArtifactRef, ResolutionClass, SignatureState
from whence.registry import Registry

SIGNATURE_FILE = "model.sig"
BUNDLE_MEDIA_TYPES = (
    "application/vnd.dev.sigstore.bundle.v0.3+json",
    "application/vnd.dev.sigstore.bundle+json;version=0.2",
    "application/vnd.dev.sigstore.bundle+json;version=0.1",
)


def signature_path(ref: ArtifactRef) -> str:
    return f"/{ref.slug}/resolve/main/{SIGNATURE_FILE}"


def detect(registry: Registry, ref: ArtifactRef) -> tuple[SignatureState, str]:
    """Whether the model carries an OMS bundle. Returns the state and a note."""
    response = registry.get(signature_path(ref))
    hops = 0
    while response.redirected and hops < 3:
        response = registry.get(str(response.location))
        hops += 1

    if response.resolution is ResolutionClass.TRANSIENT:
        # DEC-014: a transient failure produces no verdict, and that includes this one.
        return SignatureState.UNVERIFIABLE, "signature not reached; no conclusion drawn"
    if response.status == 404:
        # Conclusive: the registry reports no such file. `unsigned` is a statement about the
        # publisher, not about the signature's validity, and is the one thing here that can be
        # established.
        return SignatureState.UNSIGNED, "no model.sig published"
    if response.status != 200 or not isinstance(response.body, dict):
        return SignatureState.UNVERIFIABLE, f"signature not readable (status {response.status})"

    bundle: dict[str, Any] = response.body
    media = str(bundle.get("mediaType", ""))
    if not media.startswith("application/vnd.dev.sigstore.bundle"):
        return (
            SignatureState.UNVERIFIABLE,
            f"a model.sig exists and is not a Sigstore bundle ({media!r})",
        )
    if "dsseEnvelope" not in bundle or "verificationMaterial" not in bundle:
        return (
            SignatureState.UNVERIFIABLE,
            "a Sigstore bundle is present and structurally incomplete",
        )

    return SignatureState.UNVERIFIABLE, (
        f"a Sigstore bundle is present ({media}) and has not been verified: whence does not check "
        f"the certificate chain, the transparency log, or that the signed digests match the files. "
        f"Presence establishes that the publisher signed something, not that this artifact is it"
    )
