# 2026-09-14 — Two words for work never done

A sweep across the sibling repositories for checks that cannot come out false reached this one.
The project is retired (DEC-032), so nothing changed; the page is
`docs/architecture/unfailable-checks.md`, and it exists so a reader replaying the measurements
knows which parts of the vocabulary are load-bearing and which are vestigial.

## What it found

Two enum members nothing can produce, and both are the same story. `Relation.TOKENIZED_BY` is in
neither of the two maps that make a relation — not the registry qualifier map, not the prose verb
map — so the resolver was never taught to find the relationship the member names.
`ProvenanceClass.VERIFIED_BY_DIGEST` was reserved by DEC-004, whose own open question said the
matter would be settled once OMS consumption was implemented. It was not, and now it will not be.

Neither broke anything, because nothing filters on either. What they cost is accuracy in a
vocabulary a consumer reads as a description of the tool: `Relation` over-states by one member,
and `ProvenanceClass` implies the tool can establish an edge by digest, which it never could.

That is worth recording rather than fixing. A retired project's enum is documentation now.

## The one that looks identical and is the opposite

`SignatureState.VALID` and `INVALID` are declared and neither is assigned. To the detector this is
the same finding. It is the opposite thing, and the distinction is the most useful output of the
whole audit.

`signing.py` returns `unsigned` or `unverifiable` and never anything else, because the tool has no
identity policy and so nothing to verify a signature against. Reporting `valid` would assert three
separate things at once — the signature verifies, it covers the files served today, and the
identity it binds is the publisher's — where detection establishes none of them.

The signatures measurement is what that refusal bought. Run separately with `sigstore-python`, it
found 63 of 64 bundles verifying and **7 of them binding an identity that is not the publisher's**.
Had `VALID` been reachable from detection, those seven would have been reported valid, and the
finding would have been the tool's own output rather than a discovery about the ecosystem.

## The difference, stated once

An unreachable value is a defect when something filters on it, because the filter is dead and
nobody knows. It is correct when the value names a conclusion the tool has declined to draw and
the declining is the point.

Nothing in the code separates the two. What separates them is that somebody wrote down why the
value must stay unreachable, in a decision entry and in the docstring, and then measured what
would have been wrong if it had not been. That is the whole difference, and it is not mechanical.
