# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

`whence` resolves the dependency graph of a published machine-learning model and records, per edge,
whether the relationship is claimed or verified.

**Phase one runs**: resolution, redirect handling, response classification, CycloneDX emission, and
an evaluation harness scoring five recorded scenarios offline. **Phase two — weight-level lineage
verification — is not built** (DEC-005), so no edge is ever `verified` today.

Keep tense discipline. Present indicative for what runs; "is designed to" for phase two and
anything else specified but unbuilt. Mixing them is the easiest mistake here and the hardest to
notice afterwards.

## Read before changing anything

`docs/architecture/project-scope.md`, `docs/architecture/decision-log.md`,
`docs/architecture/data-model.md`, and `docs/architecture/evaluation-plan.md`.

`data-model.md` is authoritative for field names, types, and enumerations. Code conforms to it; it
does not describe code.

## Binding constraints

These are decided. Violating one is a design change requiring a new entry in the decision log, not
an implementation detail.

- **A verdict is three-valued** — `verified`, `contradicted`, `unverifiable` — and never boolean
  (DEC-001). An unresolved edge is `unverifiable`; it is never reported as absent.
- **Nodes are pinned to a revision digest, never a name** (DEC-002). A name is an assertion.
- **Output is CycloneDX ML-BOM** (DEC-003). This project defines no BOM format.
- **Every edge carries a provenance class** (DEC-004). It is required; an edge cannot exist
  without one.
- **The tool never executes model code** (DEC-006). No framework load call, no pickle
  deserialization, no `trust_remote_code`. Every documented safe-loading flag in this ecosystem has
  been bypassed by a CVE; the only defensible position is not to load. Resolution requiring
  execution returns `unverifiable`.
- **Traversal is depth-bounded and reports its ceilings** (DEC-007). It never silently truncates.
- **Truth sets are authored and never supplied to the tool** (DEC-008).
- **The tool reports what it resolved, never what it inferred** (DEC-010). No heuristic completion
  of an unresolvable reference.

## Working norms

- **The quality gate is `uv run ruff check . && uv run mypy && uv run pytest`**, plus
  `uv run whence evaluate`, `scripts/verify_pins.py`, and `scripts/validate_examples.py`. All six
  are expected green.
- **mypy is strict and covers `scripts/` too.**
- **Every domain object is immutable and forbids unknown fields.** That is the mechanism by which
  a registry response carrying an unexpected field fails validation rather than passing downstream
  stripped and looking valid.
- **Where absence would read as a negative answer, say so explicitly.** A missing signature is
  `unsigned`, not `invalid` and not `None`. A missing digest sets `pinned = false`.
- **Never quote registry-derived text into a log record.** Model cards are untrusted input.
  Reference material by locator and digest.
- **The default test run makes no network call and needs no credential** (DEC-009). The `live`
  marker is deselected in `addopts` precisely so a bare `pytest` cannot reach out.
- **A benchmark scenario is registered in `benchmarks/scenarios.yaml` or it is not part of the
  set.** Never discover scenarios by scanning directories.
- **Vendored files are pinned by content digest and verified** (DEC-016).
  `scripts/verify_pins.py` checks `schema/PINNED.yaml` offline and emits the project's own three
  verdicts. Updating a vendored file means regenerating the pin, not editing around it.
- **Match the prose register** in docs and PR descriptions: flat declarative, no marketing
  language, no emoji, no second person. State the rule, then state why the alternative fails.

## Journal

`journal/` is a dated record of how the project evolved, one file per session as
`journal/YYYY-MM-DD-short-slug.md`. Record the reasoning, not the diff — the commit log already has
the diff.

## Relationship to sibling projects

`whence` is one of three planned tools sharing one thesis: a security claim should be a checkable
artifact rather than an assertion. The others are `tearline` (retrieval entitlement verification)
and `attestrun` (evaluation attestation and offline replay).

The three-valued verdict is defined here first and is expected to move into `attestrun` once that
exists, with `whence` importing it. Until then it lives in this repository's domain module. Do not
build a shared "commons" package for three projects that do not yet exist.

The claimed-versus-verified distinction is inherited from the Trace project's DEC-009. Cite that
lineage where it is load-bearing; do not continue Trace's decision numbering here.
