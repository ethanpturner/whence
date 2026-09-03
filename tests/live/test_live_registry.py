"""Live registry checks. Deselected by default (`-m "not live"` in addopts).

These exist because everything else in the suite replays recordings, and a recording proves the
resolver handles a captured shape -- not that the shape is still what the registry sends. They are
the only place that can catch the registry changing underneath the fixtures.

They assert on *structure*, never on values that legitimately move. A test asserting a particular
revision digest would fail every time a publisher pushes a commit, and a suite that cries wolf gets
skipped.

Run with: uv run pytest -m live
"""

from __future__ import annotations

import pytest

from whence.domain import ArtifactRef, ResolutionClass, SignatureState, Verdict
from whence.registry import LiveRegistry
from whence.resolve import Resolver

pytestmark = pytest.mark.live

# Stable, widely mirrored, and the subject of benchmarks/declared-base.
SUBJECT = "nvidia/Llama-3.1-Nemotron-70B-Instruct-HF"


@pytest.fixture(scope="module")
def registry() -> LiveRegistry:
    return LiveRegistry()


def _skip_if_throttled(response_class: ResolutionClass) -> None:
    """A rate limit is a fact about the client, not a failure of the code under test (DEC-014)."""
    if response_class is ResolutionClass.TRANSIENT:
        pytest.skip("registry returned a transient response; not a result about the resolver")


def test_the_recorded_response_shape_is_still_what_the_registry_sends(
    registry: LiveRegistry,
) -> None:
    response = registry.get(f"/api/models/{SUBJECT}")
    _skip_if_throttled(response.resolution)
    assert response.status == 200
    assert isinstance(response.body, dict)
    # The fields the resolver reads. If any disappears, every recording is describing a dead API.
    assert "sha" in response.body
    assert "cardData" in response.body or "tags" in response.body


def test_a_live_resolution_pins_every_reachable_node(registry: LiveRegistry) -> None:
    report = Resolver(registry, max_depth=1).resolve(SUBJECT)
    assert report.root.pinned
    for node in report.nodes:
        if node.reachable and node.kind != "package":
            assert node.ref.pinned, f"{node.ref.slug} was reachable and did not pin"


def test_no_edge_is_verified_against_the_live_registry(registry: LiveRegistry) -> None:
    """The phase-one claim, checked where it matters most.

    Against recordings this is nearly tautological. Against the live registry it is the real
    assertion: cards name a base and stop, so nothing out there supplies what a `verified` edge
    would need.
    """
    report = Resolver(registry, max_depth=1).resolve(SUBJECT)
    assert report.edges
    assert not [e for e in report.edges if e.verdict is Verdict.VERIFIED]


def test_a_transferred_namespace_still_redirects_across_owners(registry: LiveRegistry) -> None:
    """benchmarks/transferred-namespace captures this. If it ever stops being true, the scenario
    is describing history rather than the registry, and its status should change."""
    response = registry.get("/api/models/runwayml/stable-diffusion-v1-5")
    _skip_if_throttled(response.resolution)
    assert response.redirected, "the redirect is gone; transferred-namespace needs revisiting"
    assert "runwayml" not in str(response.location)


def test_a_withdrawn_repository_is_inconclusive_not_absent(registry: LiveRegistry) -> None:
    """401 is not 404, and the misleading body must not change the class (DEC-014)."""
    response = registry.get("/api/models/microsoft/WizardLM-2-7B")
    _skip_if_throttled(response.resolution)
    assert response.resolution is ResolutionClass.INCONCLUSIVE


def test_a_signed_and_an_unsigned_model_are_distinguished(registry: LiveRegistry) -> None:
    """DEC-021, against the registry. IBM Granite publishes OMS bundles; most publishers do not.

    Asserts the distinction rather than a particular state for a particular model: if IBM stops
    signing, this should fail loudly rather than silently testing nothing.
    """
    from whence.signing import detect

    signed, note = detect(registry, _ref("ibm-granite/granite-swash-2b"))
    _skip_if_throttled(ResolutionClass.CONCLUSIVE)
    assert signed is SignatureState.UNVERIFIABLE, "a present bundle must never report valid"
    assert "has not been verified" in note

    unsigned, _ = detect(registry, _ref("Qwen/Qwen2.5-7B"))
    assert unsigned is SignatureState.UNSIGNED


def _ref(slug: str) -> ArtifactRef:

    namespace, name = slug.split("/")
    return ArtifactRef(host="huggingface.co", namespace=namespace, name=name, pinned=False)
