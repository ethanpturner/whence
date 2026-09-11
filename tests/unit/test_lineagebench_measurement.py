"""The lineagebench measurement replays to its published figures.

`docs/eval/lineagebench.md` quotes counts. A recording that drifted from them, or a change to the
structural check that moved them, would leave the page asserting numbers nothing produces.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "scripts" / "measure_lineagebench.py"
PUBLISHED = ROOT / "docs" / "eval" / "lineagebench" / "results.json"


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
    assert replayed["pools"] == published["pools"]
    assert replayed["pairs"] == published["pairs"]


def test_the_positive_pool_has_no_contradiction() -> None:
    """Extends DEC-020's 0-of-33: a documented derivation is never contradicted by the body check."""
    published = json.loads(PUBLISHED.read_text())
    positives = [p for p in published["pairs"] if p["pool"] == "positive"]
    assert len(positives) == 13
    assert not [p for p in positives if p["verdict"] == "contradicted"]


def test_the_pools_are_the_datasets() -> None:
    published = json.loads(PUBLISHED.read_text())
    assert {k: v["n"] for k, v in published["pools"].items()} == {
        "positive": 13,
        "negative": 107,
        "limitation": 2,
    }
