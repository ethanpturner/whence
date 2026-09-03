"""whence — model provenance resolution.

Resolves a published model's dependency graph and records, per edge, whether the relationship is
claimed or verified. See docs/architecture/ for the design.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from whence.cyclonedx import to_cyclonedx
from whence.evaluate import score
from whence.registry import LiveRegistry, RecordedRegistry, Registry
from whence.resolve import Resolver

ROOT = Path(__file__).resolve().parent.parent.parent


def _registry_for(scenario: Path | None) -> Registry:
    return RecordedRegistry(scenario / "recorded") if scenario else LiveRegistry()


def _cmd_resolve(args: argparse.Namespace) -> int:
    scenario = Path(args.scenario) if args.scenario else None
    resolver = Resolver(_registry_for(scenario), max_depth=args.max_depth)
    report = resolver.resolve(args.target)
    if args.bom:
        print(json.dumps(to_cyclonedx(report), indent=2))
    else:
        print(f"root    : {report.root.purl()}")
        print(f"partial : {report.partial}")
        for edge in report.edges:
            declared = f"  (declared {edge.declared_as.slug})" if edge.declared_as else ""
            print(
                f"  {edge.source.slug} --{edge.relation.value}--> {edge.target.slug}{declared}\n"
                f"      {edge.provenance.value} / {edge.verdict.value}"
            )
        for ceiling in report.ceilings_hit:
            print(f"  ceiling: {ceiling}")
        for unreached in report.transient_failures:
            print(f"  unreached (transient): {unreached}")
    # A partial run exits non-zero so a pipeline consuming the BOM notices (DEC-014).
    return 1 if report.partial else 0


def _cmd_evaluate(args: argparse.Namespace) -> int:
    registry = yaml.safe_load((ROOT / "benchmarks" / "scenarios.yaml").read_text())
    failed = 0
    for entry in registry.get("scenarios") or []:
        if entry["status"] != "recorded":
            print(f"skip  {entry['slug']}  ({entry['status']})")
            continue
        scenario = ROOT / entry["path"]
        target = yaml.safe_load((scenario / "input" / "target.yaml").read_text())
        resolver = Resolver(
            RecordedRegistry(scenario / "recorded"), max_depth=int(target.get("max_depth", 2))
        )
        report = resolver.resolve(str(target["target"]))
        result = score(report, scenario / "expected", entry["slug"])
        if result.passed:
            print(f"ok    {entry['slug']}  ({len(result.recovered)} edges)")
        else:
            failed += 1
            print(f"FAIL  {entry['slug']}")
            for label, items in (
                ("missed", result.missed),
                ("mismatched", result.mismatched),
                ("invented", result.invented),
                ("honesty", result.honesty_failures),
            ):
                for item in items:
                    print(f"        {label}: {item}")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="whence", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    resolve = sub.add_parser("resolve", help="resolve a model's dependency graph")
    resolve.add_argument("target")
    resolve.add_argument(
        "--scenario", help="replay a benchmark scenario's recording instead of the network"
    )
    resolve.add_argument("--max-depth", type=int, default=2)
    resolve.add_argument("--bom", action="store_true", help="emit CycloneDX instead of a summary")
    resolve.set_defaults(func=_cmd_resolve)

    evaluate = sub.add_parser(
        "evaluate", help="score every recorded scenario against its truth set"
    )
    evaluate.set_defaults(func=_cmd_evaluate)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
