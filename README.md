# whence

**Status: design. Nothing is built.** This repository currently holds the scope, the decision
log, the data model, and the evaluation plan. No code has been written, and every statement
about behaviour below is a statement of intent.

## What this is designed to be

`whence` is designed to resolve the dependency graph of a published machine-learning model and
record, for every edge in that graph, whether the relationship is **claimed** or **verified**.

The distinction is the whole point. Model signing attests bytes and says nothing about lineage.
AI-BOM generators read a model card and transcribe what it asserts. Neither answers the question
an operator actually has, which is whether the artifact in front of them came from where it says
it came from.

`whence` is designed to answer that with three verdicts and never two: an edge is `verified`,
`contradicted`, or `unverifiable`. An edge that cannot be resolved is `unverifiable` — it is never
reported as absent, because absence of a resolvable link is not evidence that no link exists.

## The specific failure it exists to prevent

A pipeline that pins a model by name rather than by revision digest is not pinning provenance.
Palo Alto Unit 42's Model Namespace Reuse work (September 2025) showed that deleting a Hugging
Face account frees the `Author/Model` namespace for re-registration, and that orphaned namespaces
were reachable through both Google Vertex AI Model Garden and Azure AI Foundry. A name is an
assertion. A digest is a fact.

`whence` is designed so that every node it emits carries a revision digest, and so that a node it
could not pin is marked as such rather than silently recorded under its name.

## Intended scope

Read `docs/architecture/project-scope.md` for the scope and the non-goals, and
`docs/architecture/decision-log.md` for what has been decided and why. The evaluation plan in
`docs/architecture/evaluation-plan.md` states how the tool is intended to be measured, including
the negative set — the cases where the correct output is a refusal to conclude.

## Lineage

The claimed-versus-verified distinction is inherited from a prior project, Trace, where it is
recorded as DEC-009: a finding means evidence supports a weakness, and a documentation gap means
it could not be determined whether a control exists. Collapsing the two is the failure that work
exists to avoid. `whence` applies the same rule to provenance rather than to controls.
