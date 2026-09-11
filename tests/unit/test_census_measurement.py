"""The census measurement replays to its published figures (docs/eval/census.md)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "scripts" / "measure_census.py"
PUBLISHED = ROOT / "docs" / "eval" / "census" / "results.json"


def test_replay_matches_published_results(tmp_path: Path) -> None:
    out = tmp_path / "results.json"
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--json", str(out)],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert completed.returncode == 0, completed.stderr
    replayed = json.loads(out.read_text())
    published = json.loads(PUBLISHED.read_text())
    for key in ("names", "declarations", "classes", "namespace_states", "rows"):
        assert replayed[key] == published[key], key


def test_the_census_is_the_papers() -> None:
    """2,501 declarations, as Stalnaker et al. report; every malformed name is unresolvable
    without a request, never guessed at (DEC-018)."""
    published = json.loads(PUBLISHED.read_text())
    assert published["declarations"] == 2501
    malformed = [r for r in published["rows"] if r["class"] == "malformed"]
    assert all("status" not in r for r in malformed)
