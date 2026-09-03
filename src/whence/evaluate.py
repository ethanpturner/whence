"""Score a resolution against a scenario's authored truth set.

Nothing under `expected/` reaches the resolver (DEC-008); it is read only here, after the run.

Three axes, reported separately because they fail differently:

  recall     edges in expected-graph.yaml that were recovered, with the right relation,
             provenance class and verdict
  invention  edges in expected-absent.yaml that were emitted -- a headline number, since a tool
             that fabricates plausible edges is worse than no tool
  honesty    expected-unresolvable.yaml: ceilings that must be reported, and verdicts that must
             not be stronger than the evidence supports
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from whence.domain import ResolutionReport


@dataclass
class Score:
    scenario: str
    recovered: list[str] = field(default_factory=list)
    missed: list[str] = field(default_factory=list)
    mismatched: list[str] = field(default_factory=list)
    invented: list[str] = field(default_factory=list)
    honesty_failures: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not (self.missed or self.mismatched or self.invented or self.honesty_failures)


def _key(source: str, target: str, relation: str) -> str:
    return f"{source} --{relation}--> {target}"


def _target_slug(raw: Any) -> str:
    return str(raw).split("@")[0]


def score(report: ResolutionReport, expected_dir: Path, scenario: str) -> Score:
    result = Score(scenario=scenario)
    emitted = {_key(e.source.slug, e.target.slug, e.relation.value): e for e in report.edges}
    declared = {
        _key(e.source.slug, e.declared_as.slug, e.relation.value): e
        for e in report.edges
        if e.declared_as is not None
    }

    graph_path = expected_dir / "expected-graph.yaml"
    if graph_path.exists():
        for row in (yaml.safe_load(graph_path.read_text()) or {}).get("edges") or []:
            key = _key(_target_slug(row["source"]), _target_slug(row["target"]), row["relation"])
            edge = emitted.get(key)
            if edge is None:
                result.missed.append(key)
                continue
            problems = []
            if row.get("provenance") and edge.provenance.value != row["provenance"]:
                problems.append(f"provenance {edge.provenance.value} != {row['provenance']}")
            if row.get("verdict") and edge.verdict.value != row["verdict"]:
                problems.append(f"verdict {edge.verdict.value} != {row['verdict']}")
            if row.get("declared_as"):
                got = edge.declared_as.slug if edge.declared_as else None
                if got != _target_slug(row["declared_as"]):
                    problems.append(f"declared_as {got} != {row['declared_as']}")
            if row.get("target_revision") and edge.target.revision != row["target_revision"]:
                problems.append(f"revision {edge.target.revision} != {row['target_revision']}")
            (result.mismatched if problems else result.recovered).append(
                f"{key} ({'; '.join(problems)})" if problems else key
            )

    absent_path = expected_dir / "expected-absent.yaml"
    if absent_path.exists():
        loaded = yaml.safe_load(absent_path.read_text()) or {}
        for row in loaded.get("absent") or []:
            key = _key(_target_slug(row["source"]), _target_slug(row["target"]), row["relation"])
            edge = emitted.get(key) or declared.get(key)
            if edge is None:
                continue
            # An entry may forbid an edge outright, or only in a particular shape. `without:
            # declared_as` forbids emitting the resolved target while discarding the declared name;
            # `verdict_if_emitted` forbids only that verdict. Treating a conditional forbid as
            # absolute would score a correct tool as inventing.
            if row.get("without") == "declared_as":
                if edge.declared_as is None:
                    result.invented.append(f"{key} (emitted without declared_as)")
            elif "verdict_if_emitted" in row:
                if edge.verdict.value == row["verdict_if_emitted"]:
                    result.invented.append(f"{key} (verdict {edge.verdict.value})")
            else:
                result.invented.append(key)

    unres_path = expected_dir / "expected-unresolvable.yaml"
    if unres_path.exists():
        loaded = yaml.safe_load(unres_path.read_text()) or {}
        for row in loaded.get("ceilings") or []:
            if row.get("expect_reported") and not report.ceilings_hit:
                result.honesty_failures.append("a ceiling was expected and none was reported")
        for row in loaded.get("unresolvable") or []:
            subject = row.get("subject") or ""
            if "weight" in subject and any(
                e.provenance.value == "verified-by-weights" for e in report.edges
            ):
                result.honesty_failures.append(
                    "verified-by-weights claimed; unreachable in phase one"
                )
    # No edge may ever be `verified` in phase one: resolution establishes existence, not derivation.
    for edge in report.edges:
        if edge.verdict.value == "verified":
            result.honesty_failures.append(f"verdict `verified` on {edge.relation.value} edge")
    return result
