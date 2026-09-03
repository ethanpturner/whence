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
        RecordedRegistry(scenario / "recorded"), max_depth=int(target.get("max_depth", 2))
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
