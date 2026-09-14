# Checks that cannot come out false

**Audited:** 2026-09-14, as part of a sweep across all five sibling repositories. Detector at
`docket`'s `scripts/audit_unfailable.py`, run against this tree; the taxonomy and the reasoning
behind the sweep are on that repository's page of the same name.

This project is retired (DEC-032). Nothing changed. The code runs, the eleven scenarios replay,
and the four measurement pages are reproducible from the recordings committed beside them; this
page records what an audit found in a tree that has stopped moving, so that a reader replaying
those measurements knows what is vestigial and what is load-bearing.

## The taxonomy

| | What it looks like |
|---|---|
| **A** | A filter naming a value nothing assigns. |
| **B** | A metric whose numerator or denominator cannot vary. |
| **C** | A guard whose failure branch is unreachable. |
| **D** | A claim true of one path and silent about the others. |
| **E** | A polarity disagreement between a question, a label, and the field it is stored in. |
| **F** | A test that cannot fail. |

## Confirmed

### A — `Relation.TOKENIZED_BY` is in neither map that produces a relation

`src/whence/domain.py:66`. A `Relation` is produced in exactly two places: the registry qualifier
map in `resolve.py` (`finetune`, `quantized`, `merge`, `adapter`) and the prose verb map in
`prose.py` (`fine-tuned`, `quantized`, `distilled`). `tokenized-by` is in neither, and no other
code path constructs one. Nothing can emit it.

It is a vocabulary entry for a relationship the resolver was never taught to find. Harmless in a
retired tree, and worth knowing if anyone reads `Relation` as a description of what the tool
detects: it over-states by one member.

### A — `ProvenanceClass.VERIFIED_BY_DIGEST` was reserved for work that was never done

`src/whence/domain.py:41`. DEC-004 declares the five classes and its own open question says the
matter would be settled *"once OMS consumption is implemented"*. It was not. `signing.py` detects
a bundle and stops (DEC-021), and the only class a check can raise an edge to is
`verified-by-weights`, from an external fingerprint file (DEC-029).

So the member is unreachable, permanently now, and the reason is recorded in the decision that
created it. A consumer reading the `ProvenanceClass` vocabulary would conclude the tool can
establish an edge by digest comparison. It cannot, and the postmortem says why.

## Cleared as deliberate

### `SignatureState.VALID` and `SignatureState.INVALID`

Both are declared and neither is assigned. This is the design, stated in DEC-021 and in the type's
own docstring, and it is the clearest instance in any of the five repositories of an unreachable
value that is correct.

`signing.py` returns `unsigned` when no bundle is published and `unverifiable` in every other case,
including when a bundle is present and parseable. The tool has no identity policy, so it has
nothing to verify a signature *against*, and reporting `valid` would assert that the signature
verifies, that it covers the files served today, and that the identity it binds is the publisher's
— three separate claims, none of which detection establishes.

The signatures measurement exists precisely because the tool refuses this. It was produced by
running `sigstore-python` separately, and it found that 63 of 64 bundles verify while **7 of them
bind an identity that is not the publisher's**. Had `SignatureState.VALID` been reachable from
detection, those seven would have been reported valid.

An unreachable value is a defect when something filters on it and the filter is therefore dead. It
is a correct design when the value names a conclusion the tool has declined to draw, and the
declining is the point.

## Cleared on inspection

| Candidate | Why it is not a finding |
|---|---|
| **A — `Relation.DISTILLED_FROM`** (detector false positive) | Assigned through `prose.py`'s `_RELATIONS` string map and converted by `Relation(claim.relation)`, which the parser cannot follow. Exercised by `tests/unit/test_prose.py` and by DEC-028's republished-card case. |
| **A — `Verdict.VERIFIED`** | Reachable and reached. `tests/unit/test_fingerprint_evidence.py` asserts it three times on edges carrying a DEC-029 evidence file, and the fingerprints measurement moved five real edges to it. |
| **C — the "no verified edge" guard** | `evaluate.py` refuses a `verified` verdict without fingerprint evidence, and both halves are exercised: the ten recorded scenarios carry no evidence file and produce none, while the fingerprint tests produce `verified` edges that pass the guard. The guard could fail, and DEC-030 narrowed it from "no edge is ever verified" to its current form precisely when `verified` became reachable. |
| **B — the lineagebench figures** | Captured from live registry reads, committed as fixtures, and both directions are non-trivial: 0 contradictions over 7 comparable positives and 28 over 30 comparable negatives. The two negatives it does not contradict are named, with the reason (identical five-field bodies). A denominator of 30 out of 107 is published rather than hidden. |
| **B — the census figures** | 2,229 captured interactions; the classifier ran over 516 namespaces it had never seen and produced three states with no `unknown`. The rates it reports — 57 of 516 free, against 7 of 1,573 — are over different populations, and the page says so rather than reconciling them. |
| **B — the signatures figures** | Produced by a separate tool over captured bundles, and the interesting number (7 of 64 binding a non-publisher identity) is one this repository's own code could not have produced. |
| **F — the tests** | The detector found none whose assertions compare only literals. |

## What this tree teaches the others

Two of the four confirmed findings across the sweep are here, and both are the same shape: a
vocabulary member added for work that was planned and not done. Neither broke anything, because
nothing filtered on either.

The instructive case is the third one, `SignatureState.VALID`, which looks identical to a parser
and is the opposite thing. The difference is not in the code. It is that somebody wrote down, in
DEC-021 and in the docstring, why the value must stay unreachable — and then measured what would
have been wrong if it had not been.
