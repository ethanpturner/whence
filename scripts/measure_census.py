"""Re-check the base-model references Stalnaker et al. found dead in July 2024, two years on.

Stalnaker et al. (arXiv 2502.04484) mined 760,460 models and found 2,501 base-model declarations
pointing at 1,371 identifiers the registry no longer served -- the closest thing to a census of
broken declarations that exists. `whence` classifies the namespace behind a dead reference as
`free`, `held-empty`, `held`, or `unknown` (DEC-017), and a `free` namespace is the re-registrable
case DEC-002 warns about. This script runs that classifier over the census's declared names and
records what the registry answers today.

    uv run python scripts/measure_census.py            # replay the recording, offline
    uv run python scripts/measure_census.py --live     # capture a fresh recording

Reads `docs/eval/census/dataset/dead_declared.json`, derived from the replication package's
`cleaned_data/model_data` (every `bases[]` entry whose resolved id begins with `404`). The names are
the strings the cards declared; 180 of them carry no namespace and are `unresolvable` here without a
request (DEC-018). A live run spends one request per well-formed name plus one to three per unique
namespace, all public and unauthenticated, paced under the anonymous rate limit; a 429 is retried
after a wait rather than recorded, because a throttled request did not look (DEC-014).

Recorded bodies are **projected** to the fields this measurement reads (see the manifest header).
A projection is not an authored response: every status, redirect and field value is what the
registry returned, and the fields dropped are ones nothing here consults.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from whence.domain import ResolutionClass
from whence.registry import LiveRegistry, RecordedRegistry, Registry, Response
from whence.resolve import Resolver, _State, parse_ref

ROOT = Path(__file__).resolve().parent.parent
EVAL = ROOT / "docs" / "eval" / "census"
DATASET = EVAL / "dataset" / "dead_declared.json"
RECORDED = EVAL / "recorded"

MODEL_FIELDS = ("id", "author", "sha", "createdAt", "gated", "private", "disabled")


def _project(path: str, response: Response) -> Response:
    """Keep the fields the measurement reads. Status and location are kept whole."""
    body = response.body
    if body is None:
        return response
    if path.startswith("/api/models/") and isinstance(body, dict):
        return Response(
            status=response.status,
            body={k: body[k] for k in MODEL_FIELDS if k in body}
            | ({"error": body["error"]} if "error" in body else {}),
            location=response.location,
        )
    if path.startswith("/api/models?author=") and isinstance(body, list):
        return Response(
            status=response.status,
            body=[{"id": str(m.get("id"))} for m in body if isinstance(m, dict)],
            location=response.location,
        )
    if path.startswith(("/api/organizations/", "/api/users/")) and isinstance(body, dict):
        return Response(
            status=response.status,
            body={k: body[k] for k in ("name", "fullname", "type", "error") if k in body},
            location=response.location,
        )
    return response


class _Recording:
    """A paced live registry that keeps every interaction, in request order, projected."""

    def __init__(self, inner: LiveRegistry, existing: Path | None) -> None:
        self._inner = inner
        self.seen: dict[str, Response] = {}
        self.order: list[str] = []
        if existing is not None and (existing / "manifest.yaml").exists():
            prior = RecordedRegistry(existing)
            for path, response in prior._by_path.items():  # resume: nothing re-fetched
                self.seen[path] = response
                self.order.append(path)
        self._last = 0.0

    def get(self, path: str) -> Response:
        if path in self.seen:
            return self.seen[path]
        for attempt in range(12):
            wait = max(0.0, 0.65 - (time.monotonic() - self._last))
            if wait:
                time.sleep(wait)
            response = self._inner.get(path)
            self._last = time.monotonic()
            if response.status == 429:
                print(f"429 on {path}; waiting 120s (attempt {attempt + 1})", file=sys.stderr)
                time.sleep(120)
                continue
            if response.status == 0:
                print(f"transient on {path}; waiting 30s", file=sys.stderr)
                time.sleep(30)
                continue
            response = _project(path, response)
            self.seen[path] = response
            self.order.append(path)
            return response
        raise SystemExit(
            f"{path} stayed throttled or unreachable through twelve attempts. Recording stopped "
            "rather than baking a transient condition into the census (DEC-014); re-run to resume."
        )

    def write(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Captured registry interactions, replayed offline (DEC-009). Written by",
            "# scripts/measure_census.py. Bodies are projected to the fields the measurement",
            "# reads -- model listings to id/author/sha/createdAt/gated/private/disabled, author",
            "# listings to their ids, overviews to name/fullname/type -- with every status, redirect",
            "# and kept value exactly as the registry returned it. A 401 or 404 is recorded as the",
            "# response it is; a 429 was waited out and is not recorded (DEC-014).",
            f"captured_at: {datetime.now(tz=UTC).date().isoformat()}",
            "host: huggingface.co",
            "interactions:",
        ]
        for path in self.order:
            response = self.seen[path]
            lines.append(f"  - request: GET {path}")
            lines.append(f"    status: {response.status}")
            if response.location:
                lines.append(f"    location: {response.location}")
            if response.body is None:
                lines.append("    body: null")
            else:
                name = _filename(path) + ".json"
                (directory / name).write_text(json.dumps(response.body))
                lines.append(f"    body: {name}")
        (directory / "manifest.yaml").write_text("\n".join(lines) + "\n")


def _filename(path: str) -> str:
    """A readable file name for a response body, made unique on a case-insensitive filesystem.

    Two namespaces that differ only in case -- `OpenAI` and `openai` both sit behind dead names --
    produced the same file on macOS, and the second write silently replaced the first: the replay
    then reported `OpenAI` as `held` from `openai`'s listing. The suffix is a digest of the exact
    path, so the file name depends on the bytes of the request rather than on how the filesystem
    compares them.
    """
    import hashlib

    suffix = "-" + hashlib.sha256(path.encode()).hexdigest()[:8]
    trimmed = path.lstrip("/")
    for prefix, label in (
        ("api/models?author=", "author-"),
        ("api/models/", "model-"),
        ("api/organizations/", "org-"),
        ("api/users/", "user-"),
    ):
        if trimmed.startswith(prefix):
            rest = trimmed[len(prefix) :].split("&")[0].replace("/overview", "")
            return label + rest.replace("/", "-") + suffix
    return trimmed.replace("/", "-").replace("?", "-").replace("&", "-")[:120] + suffix


def _status_class(response: Response) -> str:
    if response.redirected:
        return "redirects"
    if response.status == 200:
        return "resolves"
    if response.status == 404:
        return "absent"
    if response.resolution is ResolutionClass.INCONCLUSIVE:
        return "inconclusive"
    return f"status-{response.status}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="capture a fresh recording")
    parser.add_argument("--limit", type=int, default=0, help="live only: stop after N names")
    parser.add_argument("--json", dest="as_json", type=Path, default=None)
    args = parser.parse_args()

    dataset = json.loads(DATASET.read_text())
    names: list[dict[str, Any]] = dataset["declared"]

    registry: Registry
    recorder: _Recording | None = None
    if args.live:
        recorder = _Recording(LiveRegistry(), RECORDED)
        registry = recorder
    else:
        registry = RecordedRegistry(RECORDED)
    resolver = Resolver(registry)

    rows: list[dict[str, Any]] = []
    namespaces: dict[str, str] = {}
    mined = str(dataset["mined"])
    for i, entry in enumerate(names):
        declared = str(entry["declared"])
        if args.live and args.limit and i >= args.limit:
            break
        ref = parse_ref(declared, "huggingface.co")
        row: dict[str, Any] = {"declared": declared, "declarations": int(entry["declarations"])}
        if ref is None:
            row["class"] = "malformed"
            rows.append(row)
            continue
        response = registry.get(f"/api/models/{ref.slug}")
        row["status"] = response.status
        row["class"] = _status_class(response)
        if response.redirected:
            target = str(response.location).split("/api/models/", 1)[-1]
            row["redirect_target"] = target
            row["redirect_crosses_namespace"] = target.split("/")[0] != ref.namespace
        if response.status == 200 and isinstance(response.body, dict):
            created = response.body.get("createdAt")
            row["created_at"] = created
            # The census saw this name dead in July 2024. A repository created after that date
            # under the same name is a re-registration of a name a card still declares.
            row["created_after_census"] = bool(created and str(created)[:7] > mined)
            row["author"] = response.body.get("author")
        if row["class"] in ("absent", "inconclusive"):
            if ref.namespace not in namespaces:
                namespaces[ref.namespace] = resolver._namespace_state(ref.namespace, _State())
            row["namespace_state"] = namespaces[ref.namespace]
        rows.append(row)
        if recorder is not None and i % 50 == 49:
            recorder.write(RECORDED)
            print(f"{i + 1} names; {len(recorder.order)} interactions recorded", file=sys.stderr)

    if recorder is not None:
        recorder.write(RECORDED)
        print(f"captured {len(recorder.order)} interactions into {RECORDED}")

    def _count(key: str, pool: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in pool:
            value = str(row.get(key))
            counts[value] = counts.get(value, 0) + 1
        return dict(sorted(counts.items()))

    dead_now = [r for r in rows if r["class"] in ("absent", "inconclusive")]
    summary: dict[str, Any] = {
        "source": dataset["source"],
        "mined": mined,
        "names": len(rows),
        "declarations": sum(int(r["declarations"]) for r in rows),
        "classes": _count("class", rows),
        "resolving_created_after_census": sum(
            1 for r in rows if r.get("created_after_census") is True
        ),
        "redirects_crossing_namespace": sum(
            1 for r in rows if r.get("redirect_crosses_namespace") is True
        ),
        "namespace_states": {
            "unique_namespaces_behind_dead_names": len(namespaces),
            "by_namespace": _count("state", [{"state": v} for v in namespaces.values()]),
            "by_name": _count("namespace_state", dead_now),
            "declarations_by_name_state": {
                state: sum(
                    int(r["declarations"]) for r in dead_now if r["namespace_state"] == state
                )
                for state in sorted({str(r["namespace_state"]) for r in dead_now})
            },
        },
        "rows": rows,
    }
    if args.as_json:
        args.as_json.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"\n{summary['names']} declared names, {summary['declarations']} declarations, mined {mined}"
    )
    print("today: " + "  ".join(f"{k}={v}" for k, v in summary["classes"].items()))
    print(
        f"resolving names created after the census: {summary['resolving_created_after_census']}; "
        f"redirects crossing a namespace: {summary['redirects_crossing_namespace']}"
    )
    ns = summary["namespace_states"]
    print(
        f"namespaces behind still-dead names: {ns['unique_namespaces_behind_dead_names']} -> "
        + "  ".join(f"{k}={v}" for k, v in ns["by_namespace"].items())
    )
    print("by name: " + "  ".join(f"{k}={v}" for k, v in ns["by_name"].items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
