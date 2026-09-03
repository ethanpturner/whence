"""Validate the worked CycloneDX examples in docs/ against the vendored 1.7 schema.

`cyclonedx-mapping.md` claims its example is a conformant CycloneDX 1.7 document. This makes
that claim checkable rather than asserted, and it runs offline: the schema is vendored under
schema/ so the check does not depend on the network or on an upstream file staying put.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schema" / "bom-1.7.schema.json"
EXAMPLES = ROOT / "docs" / "architecture" / "examples"


def main() -> int:
    schema = json.loads(SCHEMA.read_text())
    validator = jsonschema.Draft7Validator(schema)

    examples = sorted(EXAMPLES.glob("*.cdx.json"))
    if not examples:
        print(f"no examples found under {EXAMPLES}", file=sys.stderr)
        return 1

    failed = 0
    for path in examples:
        errors = sorted(
            validator.iter_errors(json.loads(path.read_text())), key=lambda e: list(e.path)
        )
        if errors:
            failed += 1
            print(f"FAIL {path.relative_to(ROOT)} ({len(errors)} error(s))")
            for error in errors[:10]:
                print(f"  {list(error.path)}: {error.message}")
        else:
            print(f"ok   {path.relative_to(ROOT)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
