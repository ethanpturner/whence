# declared-base

**What this measures.** The simplest true positive: a model whose base, training dataset, and
loader library are all declared in structured card metadata, resolved across two hops.

**Subject.** `nvidia/Llama-3.1-Nemotron-70B-Instruct-HF` at revision
`031d4042f36adc1a52cca51b331d25cbe3cf1022`. Chosen because its lineage is documented, stable, and
widely cited, so the gold graph can be authored by reading the registry rather than by running any
tool.

## Why this scenario is not trivial

It was selected as the easy case and three things in it are not easy.

**Nothing is `verified`.** Every lineage assertion here is a bare name in card metadata with no
revision attached. The tool can establish that the named artifact exists and can be pinned; it
cannot establish that the derivation happened. Under DEC-001 that is `unverifiable`, and the
expected graph contains no `verified` edge at all.

This is the scenario's most important property. If phase one produced `verified` here, the verdict
would mean nothing — and the observation generalises: **almost no model on this registry pins its
base by digest**, so `verified-by-digest` is expected to be rare in practice. That is a finding
about the ecosystem, and it falls out of the design rather than having to be looked for.

**The first-hop base is gated.** `meta-llama/Llama-3.1-70B-Instruct` carries `gated: manual`. Its
metadata and revision are readable, so the node pins; its weights are not retrievable without
credentials the tool does not hold. Resolution and verification come apart cleanly here, which is
exactly the boundary DEC-005 draws.

**The second-hop base name redirects.** The card declares `meta-llama/Meta-Llama-3.1-70B`. The
registry answers with a 307 to `meta-llama/Llama-3.1-70B`. Following a redirect the registry
itself issued is resolution rather than inference, so DEC-010 permits it — but the declared name
and the resolved name are different strings, and a BOM that records only the resolved one has
quietly discarded what the author actually wrote.

## Open questions this scenario raised

1. **`Edge` could not express "declared as X, resolved to Y."** — *resolved by DEC-011.* The data
   model gave an edge a single `target`, so the redirect on the second hop had nowhere to live and
   the declared name was silently discarded. Authoring this truth set is what surfaced it.
   `declared_as` is now a field on `Edge` and is populated only when it differs from `target`.

2. **Whether a redirect should lower a verdict.** — *partly settled by DEC-017.* The redirect here
   is `meta-llama/Meta-Llama-3.1-70B` → `meta-llama/Llama-3.1-70B`, which stays **inside one
   namespace**: the owner is unchanged and the redirect is bookkeeping. That benign case is what
   DEC-011 was reasoned from, and generalising from it was the error DEC-017 corrects. A redirect
   that crosses ownership is flagged; see `transferred-namespace`. Whether even a within-namespace
   redirect deserves a weaker verdict than a direct hit is still open, and is now a narrower
   question than it was.

## Pass condition

Recall of the four expected edges with correct relation and provenance class on each; zero edges
from `expected-absent.yaml`; no edge reported as `verified` or `verified-by-weights`; and
`ceilings_hit` non-empty, naming the depth stop at `meta-llama/Llama-3.1-70B`.
