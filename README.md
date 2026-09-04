# whence

**Status: runs.** `whence` resolves a model's dependency graph from recorded or live registry
metadata and emits a CycloneDX 1.7 ML-BOM. It also detects OMS signatures and, opt-in, compares a
declared base's transformer body.

Where a card declares no `base_model` but says in words what it was built from, that sentence
becomes an edge carrying the quotation and the name **exactly as written** — never qualified with a
namespace the card did not give (DEC-023). The pattern's error rate is measured against published
cards rather than asserted: its first version produced ten claims across 91 of them and all ten
named an ordinary English word.

**No edge is ever `verified`** — see below, which is the point rather than a gap. Phase two *began*
with the structural check (DEC-020), the only mechanism that can emit `contradicted`; weight-level
comparison of tensor values is not built (DEC-005), and a structural match is a necessary condition,
not a sufficient one.

```
uv run whence resolve nvidia/Llama-3.1-Nemotron-70B-Instruct-HF \
    --scenario benchmarks/declared-base --bom
uv run whence evaluate          # every recorded scenario, scored against its truth set, offline
uv run whence resolve <model> --check-structure --check-signatures   # phase two, opt-in
uv run python scripts/measure_prose.py --limit 60 --search distill  # what the prose scan does live
uv run python scripts/capture_scenario.py <slug> <model>            # record a scenario, live
```

## What it does

`whence` resolves the dependency graph of a published machine-learning model and records, for every
edge in that graph, whether the relationship is **claimed** or **verified**.

The distinction is the whole point. Model signing attests bytes and says nothing about lineage.
AI-BOM generators read a model card and transcribe what it asserts. Neither answers the question
an operator actually has, which is whether the artifact in front of them came from where it says
it came from.

It answers with three verdicts and never two: an edge is `verified`, `contradicted`, or
`unverifiable`. An edge that cannot be resolved is `unverifiable` — never reported as absent,
because absence of a resolvable link is not evidence that no link exists.

**Every edge is `unverifiable` unless the structural check contradicts it, and that is the
finding.** Almost nothing on the
Hugging Face registry pins its base by digest: cards name a base and stop. So the strongest thing
resolution establishes is that the named artifact exists and can be pinned — not that the
derivation happened. Tools that report such an edge without qualification are asserting a
verification they never performed.

## The specific failure it exists to prevent

A pipeline that pins a model by name rather than by revision digest is not pinning provenance.
Palo Alto Unit 42's Model Namespace Reuse work (September 2025) showed that deleting a Hugging
Face account frees the `Author/Model` namespace for re-registration, and that orphaned namespaces
were reachable through both Google Vertex AI Model Garden and Azure AI Foundry. A name is an
assertion. A digest is a fact.

Every node `whence` emits carries a revision digest, and a node it could not pin is marked as such
rather than silently recorded under its name. `benchmarks/deleted-namespace/` captures a live instance of an unclaimed one — of 1,573
base-reference namespaces checked in the download-ranked head, **7 are held by neither an
organization nor a user**, roughly 1 in 220. `benchmarks/transferred-namespace/` captures the other
shape: `runwayml/stable-diffusion-v1-5` redirects into an organization controlled by someone
else, and file requests under the old path are served from the new namespace with no error.

## Signatures

`whence` reads OpenSSF Model Signing bundles (`model.sig`) and reports whether a publisher signed.
A model with no bundle is `unsigned`; a model with one is **`unverifiable`, never `valid`** —
presence establishes that the publisher signed something, not that the signature is valid, covers
the files in front of you, or binds an identity you trust (DEC-021).

Adoption measured before implementing: 63 of 45,000 models sampled by download rank carry a bundle,
about 1 in 700.

## Scope

Read `docs/architecture/project-scope.md` for the scope and the non-goals, and
`docs/architecture/decision-log.md` for what has been decided and why. The evaluation plan in
`docs/architecture/evaluation-plan.md` states how the tool is intended to be measured, including
the negative set — the cases where the correct output is a refusal to conclude.

## Lineage

The claimed-versus-verified distinction is inherited from a prior project, Trace, where it is
recorded as DEC-009: a finding means evidence supports a weakness, and a documentation gap means
it could not be determined whether a control exists. Collapsing the two is the failure that work
exists to avoid. `whence` applies the same rule to provenance rather than to controls.
