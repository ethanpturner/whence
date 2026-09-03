# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

`whence` resolves the dependency graph of a published machine-learning model and records, per edge,
whether the relationship is claimed or verified.

**What runs**: resolution, redirect handling, response classification, CycloneDX emission, OMS
signature detection, a structural lineage check, and an evaluation harness scoring **seven**
recorded scenarios offline.

Phase two **began** with the structural check (DEC-020), which is the only mechanism that can emit
`contradicted`. **Weight-level comparison of tensor values is not built** (DEC-005), and no edge is
ever `verified` — a structural match is a necessary condition, not a sufficient one.

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

- **The quality gate is `uv run ruff check . && uv run ruff format --check . && uv run mypy &&
  uv run pytest`**, plus
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
- **A heuristic over card text is measured before it ships.** `scripts/measure_prose.py` runs the
  prose scanner against live cards and prints every claim it would put in a BOM. The first version
  of the pattern was 0/10 correct against 91 cards; the numbers and what they changed are in
  DEC-023. Do not widen the pattern without re-running it.
- **Match the prose register** in docs and PR descriptions: flat declarative, no marketing
  language, no emoji, no second person. State the rule, then state why the alternative fails.

## Journal

`journal/` is a dated record of how the project evolved, one file per session as
`journal/YYYY-MM-DD-short-slug.md`. Record the reasoning, not the diff — the commit log already has
the diff.

## Relationship to sibling projects

One of four sharing a thesis: a security claim should be a checkable artifact rather than an
assertion. [`trace`](https://github.com/ethanpturner/trace) is where the distinction originates
(its DEC-009), [`tearline`](https://github.com/ethanpturner/tearline) applies it to retrieval
entitlements, and [`attestrun`](https://github.com/ethanpturner/attestrun) to the evaluation
results the others produce.

**The verdict vocabulary is shared by agreement, not by import.** All of them declare `verified` /
`contradicted` / `unverifiable` and none imports it from another. Settled in `attestrun`'s DEC-001:
a reader cloning this repository should not need a second one to run it, the independent agreement
is what demonstrates the distinction generalises, and a dependency from the verified to the verifier
points the wrong way. Do not extract it into a shared package, and do not read the repetition as
debt.

The claimed-versus-verified distinction is inherited from Trace's DEC-009. Cite that lineage where
it is load-bearing; do not continue another project's decision numbering here.
