# 2026-09-02 — Settling the CycloneDX mapping, and the field that had to be refused

DEC-013. The mapping is written, the worked example validates against the real 1.7 schema, and the
validation runs offline.

## The constraint, which I did not expect to be this sharp

A CycloneDX `dependency` has exactly three fields: `ref`, `dependsOn`, `provides`. No `bom-ref`, no
`properties`. **An edge cannot be addressed and cannot be annotated.**

That is awkward in a way worth stating plainly: the part of the format that models relationships
has nowhere to say anything about them, and this project is entirely about saying something about
relationships. Checking the schema rather than assuming was what surfaced it; I had expected a
properties array to exist on dependencies, and it does not.

The resolution splits an edge across two structures. `dependencies` carries topology.
`declarations.claims` carries meaning, one claim per edge, with typed values in
`declarations.evidence[].data[]` under `whence:` keys. They join by predicate rather than by
reference.

That join is a convention rather than something the format enforces, and a consumer that does not
know it sees claims and dependencies as unrelated. It is a real cost and it is recorded as one.

## The field I had to refuse

`declarations.attestations[].map[].conformance` offers `score` — a number from 0 to 1 — with a
`rationale` beside it. It is sitting right there, it is clearly meant for exactly this kind of
assessment, and using it would have been the path of least resistance.

Refused, because a verdict is three-valued and a score is a number. Mapping onto it forces
`unverifiable` onto the same axis as `verified` and `contradicted`, and a consumer reading `0.0`
reads "not derived" where the truth is "not determined."

What makes this worth a journal paragraph rather than a line in the log: **this is DEC-001's
rejected alternative arriving through a different door.** I rejected boolean-plus-confidence in the
domain model in the first session on the argument that the third state disappears at the first
integration boundary. The serialization layer is an integration boundary, and the same collapse was
available there under a different name. A decision made about the domain model does not
automatically hold at the edges of the system; it has to be re-applied at each one, and this is the
first place that became concrete.

The verdict stays a discrete token in evidence data.

## Things that landed better than expected

**purl already does the pinning.** The `huggingface` purl type takes a full commit SHA as its
version — `pkg:huggingface/nvidia/Llama-3.1-Nemotron-70B-Instruct-HF@031d4042...`. DEC-002's digest
requirement maps onto an existing standard rather than a local convention, which is a much stronger
position than inventing an identifier scheme.

**`compositions[].aggregate` is a genuine fit for incompleteness.** Its enum carries `incomplete`
and `unknown` as distinct values, and `compositions[].dependencies` scopes each one to the refs it
applies to. So DEC-007's depth ceilings are `incomplete`, and an inconclusive resolution — the 401
in `prose-only-base` — is `unknown`, attached to the specific part of the graph rather than
declared over the document. Incompleteness being expressible natively, and expressible *locally*,
was the best surprise in the mapping.

## What now runs

`scripts/validate_examples.py` checks the worked example against the vendored schema. The schema
and its two referenced sub-schemas are committed under `schema/`, so the check does not depend on
the network or on an upstream file staying where it is.

This is the first thing in the repository that executes, and it is a docs-conformance check rather
than product code. That ordering is deliberate: the mapping document makes a claim about
conformance, and the claim should be checkable rather than asserted.

## Open next

- The upstream report to CycloneDX: a `bom-ref` or a `properties` array on `dependency` would
  remove both costs recorded in the mapping. Worth filing once the mapping has been exercised
  against more than two scenarios — one more, `deleted-namespace`, is probably the right threshold.
- Whether `whence:` should be proposed as registered CycloneDX taxonomy rather than a local
  namespace.
- Whether a redirected reference deserves a weaker verdict than a direct hit. Still open, still on
  one example.
- `deleted-namespace` remains the next scenario and the direct test of DEC-002.
