"""Every recorded scenario, scored against its authored truth set. No network, no credential."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from whence.evaluate import score
from whence.registry import RecordedRegistry
from whence.resolve import Resolver

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = yaml.safe_load((ROOT / "benchmarks" / "scenarios.yaml").read_text())
RECORDED = [e for e in REGISTRY["scenarios"] if e["status"] == "recorded"]


@pytest.mark.parametrize("entry", RECORDED, ids=[e["slug"] for e in RECORDED])
def test_scenario(entry: dict[str, object]) -> None:
    scenario = ROOT / str(entry["path"])
    target = yaml.safe_load((scenario / "input" / "target.yaml").read_text())
    resolver = Resolver(
        RecordedRegistry(scenario / "recorded"),
        max_depth=int(target.get("max_depth", 2)),
        check_structure=bool(target.get("check_structure", False)),
        check_signatures=bool(target.get("check_signatures", False)),
    )
    report = resolver.resolve(str(target["target"]))
    result = score(report, scenario / "expected", str(entry["slug"]))
    assert result.passed, (
        f"missed={result.missed} mismatched={result.mismatched} "
        f"invented={result.invented} honesty={result.honesty_failures}"
    )


def test_no_edge_is_ever_verified_in_phase_one() -> None:
    """Resolution establishes that a named artifact exists and pins. It does not establish that
    the derivation happened (DEC-005)."""
    for entry in RECORDED:
        scenario = ROOT / str(entry["path"])
        target = yaml.safe_load((scenario / "input" / "target.yaml").read_text())
        report = Resolver(
            RecordedRegistry(scenario / "recorded"), max_depth=int(target.get("max_depth", 2))
        ).resolve(str(target["target"]))
        assert not [e for e in report.edges if e.verdict.value == "verified"]


def test_a_user_owned_namespace_is_not_reported_free() -> None:
    """The sweep that found deleted-namespace also found `360kaUser`: organization 404, user 200.

    Consulting only the organization endpoint reports every personal account as abandoned, which
    accuses a live owner of having released a name they still hold. Pinned here because the check
    costs one request and its absence is invisible until it fires against someone real.
    """
    from whence.registry import Response
    from whence.resolve import Resolver

    class _Registry:
        def get(self, path: str) -> Response:
            if path.startswith("/api/organizations/"):
                return Response(status=404, body={"error": "not found"})
            if path.startswith("/api/users/"):
                return Response(status=200, body={"user": "someone real"})
            raise AssertionError(f"unexpected request: {path}")

    from whence.resolve import _State

    state = Resolver(_Registry())._namespace_state("someone", _State())
    assert state == "held", "a namespace held by a user must never be reported free"


def test_signature_state_is_unverifiable_when_not_checked() -> None:
    """`unsigned` is a statement about the publisher. The default path never looks, so asserting it
    would be an unmeasured negative -- the one thing this project forbids everywhere else."""
    scenario = ROOT / "benchmarks" / "declared-base"
    target = yaml.safe_load((scenario / "input" / "target.yaml").read_text())
    report = Resolver(RecordedRegistry(scenario / "recorded"), max_depth=1).resolve(
        str(target["target"])
    )
    models = [n for n in report.nodes if n.kind == "model"]
    assert models
    assert all(n.signature.value == "unverifiable" for n in models)


def test_a_transient_while_expanding_marks_the_run_partial() -> None:
    """The branch was previously dropped with no record, so a silently truncated graph was
    presented as whole (DEC-014)."""
    from whence.registry import Response

    class _Flaky:
        def __init__(self) -> None:
            self.seen = 0

        def get(self, path: str) -> Response:
            if path.endswith("/api/models/a/root"):
                self.seen += 1
                if self.seen == 1:
                    return Response(status=200, body={"sha": "abc", "cardData": {}})
                return Response(status=429, body=None)
            return Response(status=429, body=None)

    report = Resolver(_Flaky(), max_depth=2).resolve("a/root")
    assert report.partial
    assert "a/root" in report.transient_failures


def test_a_cross_namespace_redirect_keeps_the_name_the_card_gave() -> None:
    """DEC-011 and DEC-017. The declared name survives into the graph as a node of its own.

    Recording only the resolved target states that the model derives from an artifact its author
    never named, and it erases the finding: the whole exposure is that the name in the card and the
    artifact the registry serves are controlled by different parties. The BOM previously carried
    the receiving namespace and nothing else.
    """
    scenario = ROOT / "benchmarks" / "transferred-namespace"
    target = yaml.safe_load((scenario / "input" / "target.yaml").read_text())
    report = Resolver(RecordedRegistry(scenario / "recorded"), max_depth=1).resolve(
        str(target["target"])
    )
    by_slug = {n.ref.slug: n for n in report.nodes}

    declared = by_slug["runwayml/stable-diffusion-v1-5"]
    assert not declared.reachable
    assert dict(declared.properties) == {
        "whence:namespace-state": "held-empty",
        "whence:redirect-target": "stable-diffusion-v1-5/stable-diffusion-v1-5",
    }

    resolved = dict(by_slug["stable-diffusion-v1-5/stable-diffusion-v1-5"].properties)
    assert resolved["whence:namespace-state"] == "held"
    assert resolved["whence:risk"] == "ownership-boundary-crossed"

    # Resolution succeeded and established something other than what was asked, so the BOM says
    # `unknown` for the declared name rather than presenting the answer as complete.
    assert "runwayml/stable-diffusion-v1-5" in report.inconclusive
    edge = next(e for e in report.edges if e.relation.value == "derives-from")
    assert edge.declared_as is not None
    assert edge.declared_as.slug == "runwayml/stable-diffusion-v1-5"
    assert edge.verdict.value == "unverifiable"


def test_a_same_namespace_redirect_asks_no_ownership_question() -> None:
    """A rename inside one namespace. The same party controls both names, so a namespace lookup
    would spend a request per redirect to establish what is not in doubt -- and `declared-base`'s
    recording contains no such interaction, which is how the cost was noticed."""
    from whence.registry import Response

    class _Renaming:
        def __init__(self) -> None:
            self.asked: list[str] = []

        def get(self, path: str) -> Response:
            self.asked.append(path)
            if path == "/api/models/org/old":
                return Response(status=307, body=None, location="/api/models/org/new")
            if path == "/api/models/org/new":
                return Response(status=200, body={"sha": "abc", "cardData": {}})
            return Response(status=200, body={"sha": "root", "cardData": {"base_model": "org/old"}})

    registry = _Renaming()
    Resolver(registry, max_depth=1).resolve("org/root")
    assert not [p for p in registry.asked if "organizations" in p or "author=" in p]


def test_the_node_count_ceiling_stops_a_wide_graph() -> None:
    """DEC-007 named both ceilings and only the depth one existed (DEC-024).

    Depth does not bound a graph: one model naming forty parents is depth one and forty requests.
    Reaching the ceiling stops and is reported, rather than truncating silently.
    """
    from whence.registry import Response

    class _Wide:
        def get(self, path: str) -> Response:
            if path.endswith("/raw/main/README.md"):
                return Response(status=404, body=None)
            if path == "/api/models/a/root":
                return Response(
                    status=200,
                    body={
                        "sha": "root",
                        "cardData": {"base_model": [f"a/base{i}" for i in range(40)]},
                    },
                )
            return Response(status=200, body={"sha": "x", "cardData": {}})

    report = Resolver(_Wide(), max_depth=3, max_nodes=10).resolve("a/root")
    assert any("node count 10" in c for c in report.ceilings_hit)
    assert not report.partial, "a ceiling is a stop the tool chose, not a transient failure"


def test_a_card_declaring_a_base_is_not_also_read_for_prose() -> None:
    """DEC-023. A card that declares a base has answered the question, and reading its prose too
    would emit a second, weaker edge beside the good one. Every wrong claim the measurement found
    came from a card that already had a structured answer."""
    from whence.registry import Response

    asked: list[str] = []

    class _Declared:
        def get(self, path: str) -> Response:
            asked.append(path)
            if path == "/api/models/a/root":
                return Response(
                    status=200,
                    body={"sha": "root", "cardData": {"base_model": "a/base"}},
                )
            return Response(status=200, body={"sha": "b", "cardData": {}})

    Resolver(_Declared(), max_depth=1).resolve("a/root")
    assert not [p for p in asked if p.endswith("/raw/main/README.md")]


def test_replaying_a_recording_twice_produces_the_same_bytes() -> None:
    """A recorded scenario exists so a result can be re-derived and compared (DEC-009), and two
    runs that differ make that impossible.

    Two things defeated it. The report was dated with the wall clock, so every replay carried a
    different timestamp for facts observed on the recording's capture date; and a claim's `bom-ref`
    was its index in the edge list, so any upstream change shifted every later ref -- a diff of two
    BOMs showing every claim after the first as modified, and a reference held elsewhere silently
    pointing at a different claim.
    """
    from whence.cyclonedx import to_cyclonedx

    scenario = ROOT / "benchmarks" / "declared-base"
    target = yaml.safe_load((scenario / "input" / "target.yaml").read_text())

    def once() -> dict[str, object]:
        report = Resolver(RecordedRegistry(scenario / "recorded"), max_depth=2).resolve(
            str(target["target"])
        )
        return to_cyclonedx(report)

    first, second = once(), once()
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    # Dated from the recording, not from today.
    manifest = yaml.safe_load((scenario / "recorded" / "manifest.yaml").read_text())
    assert str(first["metadata"]["timestamp"]).startswith(str(manifest["captured_at"]))  # type: ignore[index]

    refs = [c["bom-ref"] for c in first["declarations"]["claims"]]  # type: ignore[index]
    assert len(refs) == len(set(refs))
    assert not any(ref.rsplit("-", 1)[-1].isdigit() for ref in refs), "a ref is positional again"
