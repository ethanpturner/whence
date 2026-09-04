"""Capture a scenario's registry interactions by resolving it live.

A recording is a real capture or it is nothing. Hand-writing one puts a fabricated response shape
into the benchmark, and the tool then passes against a registry that does not exist -- so this
script records exactly what the live registry returned, in the order the resolver asked for it, and
writes the manifest the replay reads back.

    uv run python scripts/capture_scenario.py merge-lineage QuantFactory/Some-Model --max-depth 2

Spends unauthenticated public requests, one per interaction. Nothing is invented: a 401 or a 404 is
recorded as the response it is, because the status code is often the finding.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from whence.registry import LiveRegistry, Response
from whence.resolve import Resolver

ROOT = Path(__file__).resolve().parent.parent


def _filename(path: str) -> str:
    """A readable file name for a response body, derived from the request path."""
    trimmed = path.lstrip("/")
    for prefix, label in (
        ("api/models/", "model"),
        ("api/datasets/", "dataset"),
        ("api/organizations/", "org"),
        ("api/users/", "user"),
    ):
        if trimmed.startswith(prefix):
            return f"{label}-" + trimmed[len(prefix) :].replace("/", "-").split("?")[0]
    if trimmed.startswith("api/models?author="):
        return "author-" + trimmed.split("author=", 1)[1].split("&")[0]
    if trimmed.endswith("/raw/main/README.md"):
        return "readme-" + trimmed[: -len("/raw/main/README.md")].replace("/", "-")
    return trimmed.replace("/", "-").replace("?", "-").replace("&", "-")


class _Recording:
    """Wraps the live registry and keeps every interaction, in request order."""

    def __init__(self, inner: LiveRegistry) -> None:
        self._inner = inner
        self.seen: dict[str, Response] = {}
        self.order: list[str] = []

    def get(self, path: str) -> Response:
        if path in self.seen:
            return self.seen[path]
        response = self._inner.get(path)
        if response.status == 0:
            raise SystemExit(
                f"transient failure on {path}. A recording captured around a network failure would "
                "bake a `partial` run into the fixture; re-run when the registry is reachable."
            )
        self.seen[path] = response
        self.order.append(path)
        return response


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug", help="scenario directory name under benchmarks/")
    parser.add_argument("target", help="the model to resolve")
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--max-nodes", type=int, default=200)
    parser.add_argument("--check-signatures", action="store_true")
    parser.add_argument("--check-structure", action="store_true")
    args = parser.parse_args()

    recorder = _Recording(LiveRegistry())
    Resolver(
        recorder,
        max_depth=args.max_depth,
        max_nodes=args.max_nodes,
        check_signatures=args.check_signatures,
        check_structure=args.check_structure,
    ).resolve(args.target)

    scenario = ROOT / "benchmarks" / args.slug
    recorded = scenario / "recorded"
    recorded.mkdir(parents=True, exist_ok=True)

    interactions: list[dict[str, Any]] = []
    for path in recorder.order:
        response = recorder.seen[path]
        entry: dict[str, Any] = {"request": f"GET {path}", "status": response.status}
        if response.location:
            entry["location"] = response.location
        if response.body is None:
            entry["body"] = None
        else:
            raw = response.body.get("_raw") if isinstance(response.body, dict) else None
            if isinstance(raw, str):
                name = _filename(path) + ".md"
                (recorded / name).write_text(raw)
            else:
                name = _filename(path) + ".json"
                (recorded / name).write_text(json.dumps(response.body))
            entry["body"] = name
        interactions.append(entry)

    lines = [
        "# Captured registry interactions, replayed offline (DEC-009). Written by",
        "# scripts/capture_scenario.py; status codes are part of the recording, and a 401 or 404 is",
        "# recorded as the response it is rather than treated as a capture failure.",
        f"captured_at: {datetime.now(tz=UTC).date().isoformat()}",
        "host: huggingface.co",
        "interactions:",
    ]
    for entry in interactions:
        lines.append(f"  - request: {entry['request']}")
        lines.append(f"    status: {entry['status']}")
        if "location" in entry:
            lines.append(f"    location: {entry['location']}")
        lines.append(f"    body: {entry['body'] if entry['body'] else 'null'}")
    (recorded / "manifest.yaml").write_text("\n".join(lines) + "\n")

    print(f"captured {len(interactions)} interactions into {recorded}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
