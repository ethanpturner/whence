# Vendored schemas

Third-party files, committed unmodified so that `scripts/validate_examples.py` runs offline and so
that the conformance claim in `../docs/architecture/cyclonedx-mapping.md` does not depend on an
upstream file staying where it is.

| File | Source | License |
|---|---|---|
| `bom-1.7.schema.json` | [CycloneDX/specification](https://github.com/CycloneDX/specification) `schema/bom-1.7.schema.json` | Apache-2.0 |
| `spdx.schema.json` | same repository, referenced by the above | Apache-2.0 |
| `jsf-0.82.schema.json` | same repository, referenced by the above | Apache-2.0 |

Retrieved 2026-09-02 from the `master` branch. The CycloneDX specification is a work of the
CycloneDX project under the OWASP Foundation and is licensed Apache-2.0; these files carry that
license, not this repository's.

**Not pinned to a commit.** The retrieval is dated but not digest-pinned, which is precisely the
weakness this project exists to point out in other people's dependency records. Pinning these to
their source commit is open work, and doing so is the smallest possible demonstration of the thesis.
