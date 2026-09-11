"""The signature measurement replays to its published figures (docs/eval/signatures.md)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "scripts" / "measure_signatures.py"
PUBLISHED = ROOT / "docs" / "eval" / "signatures" / "results.json"


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
    for key in ("signed_models", "detection", "verifies", "identity", "rows"):
        assert replayed[key] == published[key], key


def test_a_present_bundle_is_still_unverifiable_to_the_tool() -> None:
    """DEC-021 holds after the measurement: `whence` itself reports every bundle `unverifiable`.
    The verification figures come from a separate tool and are joined as evidence, not adopted as
    the signature state."""
    published = json.loads(PUBLISHED.read_text())
    assert set(published["detection"]) == {"unverifiable"}


def test_a_verified_signature_can_still_name_the_wrong_publisher() -> None:
    """The class between DEC-021 and OMS: bundles that verify cryptographically and bind an
    identity that is not the publishing namespace's."""
    published = json.loads(PUBLISHED.read_text())
    wrong = [r for r in published["rows"] if r["verifies"] and r["identity"] == "does-not-match"]
    assert wrong, "the measurement found at least one; a zero here means the join broke"
    # Some of them are byte-identical copies of another swept model's bundle, which is how a
    # signature comes to sit under a namespace that did not sign it. Not all: an upstream that
    # re-signed after the copy leaves the copy sharing nothing in the sweep.
    assert any(r["bundle_shared_with"] for r in wrong)
    # Name coverage cannot see the copy: a requantisation keeps the file names.
    assert any(not r["present_but_unsigned"] and not r["signed_but_absent"] for r in wrong)
