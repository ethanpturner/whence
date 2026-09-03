"""Every recorded scenario, scored against its authored truth set. No network, no credential."""

from __future__ import annotations

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

    state = Resolver(_Registry())._namespace_state("someone")
    assert state == "held", "a namespace held by a user must never be reported free"
