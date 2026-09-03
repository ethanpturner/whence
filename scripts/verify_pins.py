"""Verify the vendored schemas against `schema/PINNED.yaml`.

`PINNED.yaml` is a claim about what this repository contains. This turns it into a verdict, using
the same three values the tool is designed to emit about model lineage (DEC-001, DEC-016):

    verified      the recorded digests match the files on disk
    contradicted  a file is present and its digests do not match
    unverifiable  the claim could not be checked -- a recorded file is missing

Offline by default. `--online` additionally asks the upstream repository whether it still serves
these blobs at the pinned commit; a network failure there is a transient condition and produces no
verdict at all rather than a weak one (DEC-014), so it can never turn a green run red.

Exit codes: 0 all verified; 1 anything contradicted or unverifiable; 2 the record itself is
unusable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PINS = ROOT / "schema" / "PINNED.yaml"

VERIFIED = "verified"
CONTRADICTED = "contradicted"
UNVERIFIABLE = "unverifiable"


def git_blob_sha1(data: bytes) -> str:
    """Git's object id for a blob: sha1 of ``blob <len>\\0`` followed by the content."""
    header = f"blob {len(data)}".encode() + b"\0"
    return hashlib.sha1(header + data).hexdigest()  # noqa: S324 - object id, not a security digest


def check_file(entry: dict[str, object], base: Path) -> tuple[str, str]:
    path = base / str(entry["path"])
    if not path.exists():
        return UNVERIFIABLE, "file recorded in the pin but not present on disk"

    data = path.read_bytes()
    mismatches = []
    if (actual := len(data)) != entry["size"]:
        mismatches.append(f"size {actual} != {entry['size']}")
    if (actual_blob := git_blob_sha1(data)) != entry["blob_sha1"]:
        mismatches.append(f"blob_sha1 {actual_blob[:12]} != {str(entry['blob_sha1'])[:12]}")
    if (actual_256 := hashlib.sha256(data).hexdigest()) != entry["sha256"]:
        mismatches.append(f"sha256 {actual_256[:12]} != {str(entry['sha256'])[:12]}")

    if mismatches:
        return CONTRADICTED, "; ".join(mismatches)
    return VERIFIED, "digests match"


def check_upstream(record: dict[str, object]) -> None:
    """Report whether upstream still serves the pinned blobs. Never affects the exit code."""
    source = record["source"]
    assert isinstance(source, dict)
    repo = str(source["repository"]).removeprefix("https://github.com/")
    url = f"https://api.github.com/repos/{repo}/contents/{source['path_prefix']}?ref={source['commit']}"
    try:
        with urllib.request.urlopen(url, timeout=20) as response:  # noqa: S310 - fixed https URL
            listing = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        # DEC-014: a transient failure is not evidence. It produces no verdict.
        print(f"\nupstream  {UNVERIFIABLE}: not reached ({type(exc).__name__}). No verdict; exit code unaffected.")
        return

    upstream = {item["name"]: item["sha"] for item in listing}
    print(f"\nupstream at {str(source['commit'])[:12]}:")
    files = record["files"]
    assert isinstance(files, list)
    for entry in files:
        name = str(entry["path"])
        actual = upstream.get(name)
        if actual is None:
            print(f"  {UNVERIFIABLE:13} {name}: not served at this commit")
        elif actual == entry["blob_sha1"]:
            print(f"  {VERIFIED:13} {name}")
        else:
            print(f"  {CONTRADICTED:13} {name}: upstream blob {actual[:12]} != pinned {str(entry['blob_sha1'])[:12]}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--online", action="store_true", help="also query upstream (advisory only)")
    args = parser.parse_args()

    if not PINS.exists():
        print(f"no pin record at {PINS}", file=sys.stderr)
        return 2
    record = yaml.safe_load(PINS.read_text())
    if not isinstance(record, dict) or "files" not in record:
        print(f"{PINS} is not a usable pin record", file=sys.stderr)
        return 2

    files = record["files"]
    assert isinstance(files, list)
    worst = VERIFIED
    for entry in files:
        verdict, detail = check_file(entry, PINS.parent)
        print(f"  {verdict:13} {entry['path']}: {detail}")
        if verdict == CONTRADICTED:
            worst = CONTRADICTED
        elif verdict == UNVERIFIABLE and worst != CONTRADICTED:
            worst = UNVERIFIABLE

    if args.online:
        check_upstream(record)

    print(f"\n{len(files)} pinned file(s): {worst}")
    return 0 if worst == VERIFIED else 1


if __name__ == "__main__":
    raise SystemExit(main())
