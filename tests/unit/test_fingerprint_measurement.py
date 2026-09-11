"""The fingerprint measurement replays to its published figures.

`docs/eval/fingerprints.md` quotes counts of edges moved, verdicts unattached, and kind
disagreements. A recording or evidence file that drifted from them, or a change to the ingest that
moved them, would leave the page asserting numbers nothing produces.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from whence.fingerprint import load

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "scripts" / "measure_fingerprints.py"
EVAL = ROOT / "docs" / "eval" / "fingerprints"
PUBLISHED = EVAL / "results.json"
EVIDENCE = EVAL / "evidence" / "lineagebench-modeldna.json"
CISCO = EVAL / "evidence" / "lineagebench-cisco.json"


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
    assert replayed["totals"] == published["totals"]
    assert replayed["suspects"] == published["suspects"]
    assert replayed["kind_disagreements"] == published["kind_disagreements"]
    assert replayed["evidence_files"] == published["evidence_files"]


def test_the_evidence_files_are_the_tools_and_no_class_contradicts() -> None:
    published = {e["tool"]: e for e in json.loads(PUBLISHED.read_text())["evidence_files"]}
    for path, tool in ((EVIDENCE, "modeldna"), (CISCO, "cisco-ai-provenance-kit")):
        evidence, digest = load(path)
        assert evidence.tool == tool
        assert digest == published[tool]["digest"]
        assert len(evidence.verdicts) == published[tool]["verdicts_in_file"]
        # Neither tool's negative is mapped to `contradicts`: a tool's own negative is not this
        # tool's contradiction (DEC-029, the SOLAR case), and the kit's "Confirmed Match" is a
        # metadata match that DEC-020 already treats as necessary and not sufficient.
        assert all(effect.value != "contradicts" for _, effect in evidence.classes)
    cisco, _ = load(CISCO)
    assert cisco.effect_of("Confirmed Match").value == "abstains"


def test_a_verified_edge_in_the_results_always_names_its_fingerprint() -> None:
    published = json.loads(PUBLISHED.read_text())
    for row in published["suspects"]:
        for moved in row.get("moved", []):
            assert moved["after"] in ("verified", "contradicted")
            assert moved["tool"] and moved["class"]
        for created in row.get("created", []):
            assert created["tool"] and created["class"]
