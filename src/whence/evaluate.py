"""Score a resolution against a scenario's authored truth set.

Nothing under `expected/` reaches the resolver (DEC-008); it is read only here, after the run.

Three axes, reported separately because they fail differently:

  recall     edges in expected-graph.yaml that were recovered, with the right relation,
             provenance class and verdict
  invention  edges in expected-absent.yaml that were emitted -- a headline number, since a tool
             that fabricates plausible edges is worse than no tool
  honesty    expected-unresolvable.yaml: ceilings that must be reported, verdicts that must not be
             stronger than the evidence supports, node facts, and the BOM compositions that record
             what the run could not determine

Every key in a truth set is either scored or counted as unchecked prose, and a key in neither
category is a **failure**. Six keys were authored and read by nothing -- `nodes`, `compositions`,
`compositions_absent`, `properties_absent`, `behaviour_absent`, `report` -- while every scenario
printed `ok`. A scorer that ignores what it does not recognise reports the absence of a check as a
pass, which is the overclaiming this project exists to measure.

`negative_assertions` and `behaviour_absent` forbid *claims* -- "the base does not exist", "the
reference is merely a dead end". This tool emits a graph and a BOM, not narrative, so they are
vacuously satisfied rather than checked. They are counted and printed as unchecked, because a
negative set that silently scores as passed is the same failure one step removed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from whence.cyclonedx import to_cyclonedx
from whence.domain import ResolutionReport


@dataclass
class Score:
    scenario: str
    recovered: list[str] = field(default_factory=list)
    missed: list[str] = field(default_factory=list)
    mismatched: list[str] = field(default_factory=list)
    invented: list[str] = field(default_factory=list)
    honesty_failures: list[str] = field(default_factory=list)
    #: Entries forbidding a narrative claim. Counted, never scored -- see the module docstring.
    unchecked_prose: int = 0

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

    # An edge is identified by (source, relation, target), so two of them are one relationship
    # asserted twice -- never two dependencies. A BOM carrying repeats inflates the graph and makes
    # two renderings of the same model diff as though it had changed.
    keys = [_key(e.source.slug, e.target.slug, e.relation.value) for e in report.edges]
    for duplicate in {k for k in keys if keys.count(k) > 1}:
        result.honesty_failures.append(
            f"{duplicate} was emitted {keys.count(duplicate)} times; repeated declarations are one "
            "edge carrying a `declared_count`, not several edges"
        )

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
            # How many times the source declared this same relationship. Unscored until
            # `merge-lineage` was mutation-tested: removing the deduplication emitted five
            # identical edges and every scenario still passed, because nothing looked.
            expected_count = int(row.get("declared_count", 1))
            if edge.declared_count != expected_count:
                problems.append(f"declared_count {edge.declared_count} != {expected_count}")
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

    _score_nodes(result, expected_dir, report)
    _score_unresolvable(result, expected_dir, report)

    # No edge is ever `verified`: resolution establishes existence, not derivation, and the
    # structural check is a necessary condition rather than a sufficient one (DEC-005, DEC-020).
    for edge in report.edges:
        if edge.verdict.value == "verified":
            result.honesty_failures.append(f"verdict `verified` on {edge.relation.value} edge")

    _check_keys_are_all_handled(result, expected_dir)
    return result


#: Every key a truth set may carry, and whether this module scores it or counts it as prose. A key
#: in neither set fails the scenario rather than being ignored. Keyed by name rather than by file:
#: the corpus already puts `report:` in one scenario's graph file and `compositions_absent:` in
#: another's absent file, and a per-file map turned that into a failure about the wrong thing.
SCORED_KEYS = frozenset(
    {
        "root",
        "edges",
        "nodes",
        "absent",
        "unresolvable",
        "ceilings",
        "compositions",
        "compositions_absent",
    }
)
#: Entries forbidding a *claim* rather than an artifact. This tool emits a graph and a BOM, not
#: narrative, so they are vacuously satisfied. Counted and printed, never folded into the pass.
PROSE_KEYS = frozenset(
    {"negative_assertions", "omissions", "properties_absent", "behaviour_absent", "report"}
)


def _score_nodes(result: Score, expected_dir: Path, report: ResolutionReport) -> None:
    """Node facts: whether it was pinned, whether it was reachable, and its BOM properties.

    The properties matter more than they look. `deleted-namespace`'s entire finding is two of them
    -- `whence:namespace-state: free` and `whence:risk: reregistrable-reference` -- and without
    them the BOM records an ordinary missing dependency rather than a re-registrable one, which is
    the difference between an inconvenience and a supply-chain exposure. They were unscored.
    """
    path = expected_dir / "expected-graph.yaml"
    if not path.exists():
        return
    by_slug = {node.ref.slug: node for node in report.nodes}
    for row in (yaml.safe_load(path.read_text()) or {}).get("nodes") or []:
        slug = _target_slug(row["ref"])
        node = by_slug.get(slug)
        if node is None:
            result.honesty_failures.append(f"node {slug} expected in the graph and absent")
            continue
        if "pinned" in row and bool(node.ref.revision) != bool(row["pinned"]):
            result.honesty_failures.append(
                f"node {slug} pinned={bool(node.ref.revision)} != {row['pinned']}"
            )
        if "reachable" in row and node.reachable != bool(row["reachable"]):
            result.honesty_failures.append(
                f"node {slug} reachable={node.reachable} != {row['reachable']}"
            )
        emitted = dict(node.properties)
        for name, value in (row.get("properties") or {}).items():
            if emitted.get(str(name)) != str(value):
                result.honesty_failures.append(
                    f"node {slug} property {name}={emitted.get(str(name))!r} != {value!r}"
                )


def _score_unresolvable(result: Score, expected_dir: Path, report: ResolutionReport) -> None:
    """What the run must admit it could not determine.

    An `unresolvable` subject naming a derivation asserts that no verdict stronger than
    `unverifiable` is reachable for it. That was checked by looking for the substring "weight" and
    nothing else, so every subject naming a specific edge passed without being read.
    """
    path = expected_dir / "expected-unresolvable.yaml"
    if not path.exists():
        return
    loaded = yaml.safe_load(path.read_text()) or {}
    for row in loaded.get("ceilings") or []:
        if not row.get("expect_reported"):
            continue
        if not report.ceilings_hit:
            result.honesty_failures.append("a ceiling was expected and none was reported")
            continue
        # `kind` distinguishes the depth ceiling from the node-count one. Checking only that some
        # ceiling was reported let a scenario written for one pass on the other -- which is what
        # `merge-lineage` did before `max_nodes` was wired into the evaluator at all.
        kind = str(row.get("kind") or "")
        if kind and not any(kind in hit for hit in report.ceilings_hit):
            result.honesty_failures.append(
                f"expected a {kind!r} ceiling; got {list(report.ceilings_hit)}"
            )
        for name in row.get("names_unfollowed") or []:
            if not any(str(name) in hit for hit in report.ceilings_hit):
                result.honesty_failures.append(
                    f"the ceiling does not name {name}, which it stopped short of (DEC-007)"
                )

    by_pair = {(e.source.slug, e.relation.value, e.target.slug): e for e in report.edges}
    for row in loaded.get("unresolvable") or []:
        subject = str(row.get("subject") or "")
        if any(e.provenance.value == "verified-by-weights" for e in report.edges):
            result.honesty_failures.append("verified-by-weights claimed; no such comparison exists")
        # `subject` is written for a person: "whether the declared artifact and the redirect target
        # are the same bytes" says what is open far better than a triple would. So the row carries
        # an optional `edge:` naming what must stay `unverifiable`, and a row without one is prose
        # -- counted, not silently passed. Parsing the sentence instead would be a scorer that
        # believes whatever the truth set happens to phrase in a familiar way.
        if "source" in row and "relation" in row:
            _score_unresolvable_edge(result, row, report)
            continue
        pair = row.get("edge")
        if not isinstance(pair, dict):
            result.unchecked_prose += 1
            continue
        key = (str(pair["source"]), str(pair["relation"]), str(pair["target"]))
        edge = by_pair.get(key)
        if edge is None:
            result.honesty_failures.append(f"{subject}: no edge {' '.join(key)} was emitted")
        elif edge.verdict.value != "unverifiable":
            result.honesty_failures.append(
                f"{subject}: verdict {edge.verdict.value}, and nothing supports more"
            )

    # Compositions record what the BOM says was NOT fully determined (DEC-014). A run that resolves
    # a 401 and emits no `unknown` aggregate presents a partial graph as a complete one.
    expected_aggregates = {str(r["aggregate"]) for r in (loaded.get("compositions") or [])}
    forbidden = {str(r["aggregate"]) for r in (loaded.get("compositions_absent") or [])}
    if expected_aggregates or forbidden:
        bom = to_cyclonedx(report)
        actual = {str(c["aggregate"]) for c in (bom.get("compositions") or [])}
        for missing in expected_aggregates - actual:
            result.honesty_failures.append(f"composition aggregate {missing!r} expected and absent")
        for present in forbidden & actual:
            result.honesty_failures.append(f"composition aggregate {present!r} must not appear")


def _score_unresolvable_edge(result: Score, row: dict[str, Any], report: ResolutionReport) -> None:
    """An edge that exists and cannot be established -- `prose-only-base`'s whole scenario.

    The name is on the **target**, not on `declared_as`. `declared_as` pairs a name that was given
    with an artifact that was resolved (DEC-011), and here nothing resolved: the card says the model
    derives from "Mistral-7B-v0.2" and the tool declines to guess whose. Putting the name in
    `declared_as` with an empty target would record a claim with nothing it is a claim about.

    The excerpt is checked because without it the edge is an assertion with nothing behind it, and
    a reader cannot audit the tool's refusal to resolve -- which is the reason DEC-012 permits an
    excerpt at all.
    """
    declared = str(row.get("declared_as") or row.get("target") or "")
    relation = str(row["relation"])
    edge = next(
        (
            e
            for e in report.edges
            if e.source.slug == str(row["source"])
            and e.relation.value == relation
            and (e.declared_as.slug if e.declared_as else e.target.slug) == declared
        ),
        None,
    )
    if edge is None:
        result.missed.append(f"{row['source']} --{relation}--> {declared} (unresolvable)")
        return
    for field_name, actual in (
        ("provenance", edge.provenance.value),
        ("verdict", edge.verdict.value),
    ):
        if row.get(field_name) and actual != row[field_name]:
            result.mismatched.append(f"{declared} {field_name} {actual} != {row[field_name]}")
    evidence = edge.evidence[0] if edge.evidence else None
    if row.get("evidence_locator"):
        got = evidence.locator if evidence else None
        if got != row["evidence_locator"]:
            result.mismatched.append(f"{declared} locator {got} != {row['evidence_locator']}")
    if row.get("evidence_excerpt"):
        got_excerpt = (evidence.excerpt or "") if evidence else ""
        wanted = " ".join(str(row["evidence_excerpt"]).split())
        if " ".join(got_excerpt.split()) != wanted:
            result.mismatched.append(f"{declared} excerpt {got_excerpt!r} != {wanted!r}")
    result.recovered.append(f"{row['source']} --{relation}--> {declared}")


def _check_keys_are_all_handled(result: Score, expected_dir: Path) -> None:
    """Fail on a key nothing reads, and count the prose ones.

    This is the guard that would have caught the six unread keys. It is cheap and it is the only
    thing standing between an authored expectation and being quietly ignored.
    """
    for filename in ("expected-graph.yaml", "expected-absent.yaml", "expected-unresolvable.yaml"):
        path = expected_dir / filename
        if not path.exists():
            continue
        for key, value in (yaml.safe_load(path.read_text()) or {}).items():
            if key in PROSE_KEYS:
                result.unchecked_prose += len(value or [])
            elif key not in SCORED_KEYS:
                result.honesty_failures.append(
                    f"{filename} carries `{key}:`, which nothing scores -- an authored expectation "
                    "read as a pass is the overclaiming this corpus measures"
                )
