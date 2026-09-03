# Vendored schemas

Third-party files, committed unmodified so that `scripts/validate_examples.py` runs offline and so
that the conformance claim in `../docs/architecture/cyclonedx-mapping.md` does not depend on an
upstream file staying where it is.

| File | License |
|---|---|
| `bom-1.7.schema.json` | Apache-2.0 |
| `spdx.schema.json` | Apache-2.0 |
| `jsf-0.82.schema.json` | Apache-2.0 |

All three come from [CycloneDX/specification](https://github.com/CycloneDX/specification) under
`schema/`. The CycloneDX specification is a work of the CycloneDX project under the OWASP
Foundation and is licensed Apache-2.0; these files carry that license, not this repository's.

## Pinned

`PINNED.yaml` records the source commit and, per file, the git blob id, the SHA-256, and the size.
Content was verified present at commit
[`595d98f`](https://github.com/CycloneDX/specification/tree/595d98f16159bdf7463adc140509ded479130b8b/schema)
(2026-09-02).

```
uv run python scripts/verify_pins.py            # offline; recomputes digests
uv run python scripts/verify_pins.py --online   # also asks upstream, advisory only
```

The verifier emits the same three verdicts the tool is designed to emit about model lineage —
`verified`, `contradicted`, `unverifiable` — because `PINNED.yaml` is a *claim* about what this
repository contains and recomputing the digests is what turns it into a finding (DEC-016).

Two properties worth noting, both of which are the project's own rules applied to itself:

- **The pin is by content, not by name.** `blob_sha1` is content-addressed, so it verifies the exact
  bytes independently of any branch, tag, or commit. Retrieval originally used the `master` branch,
  which is precisely the unpinned-by-name pattern DEC-002 rejects.
- **An unreachable upstream produces no verdict.** `--online` is advisory: if the network fails, the
  upstream check reports `unverifiable` and the exit code is unaffected (DEC-014). A transient
  condition can never turn a green run red.

## Updating

Replace the files, regenerate `PINNED.yaml` with the new commit and digests, and re-run both
scripts. A schema change that moves the mapping's worked example is a design change, not a
dependency bump — `validate_examples.py` failing after an update is a signal to read
`cyclonedx-mapping.md`, not to edit the example until it passes.
