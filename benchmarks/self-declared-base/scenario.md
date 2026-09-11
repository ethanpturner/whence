# self-declared-base

**What this measures.** That a card naming the model as its own base is recorded as the claim it
is — an edge from the node to itself, `unverifiable` — flagged so a consumer can see the
declaration is degenerate, and neither followed nor completed with a guess about what the author
meant.

**Subject.** `nmthien/vietnamese-gpt2`, whose card metadata declares `base_model:
nmthien/vietnamese-gpt2`. Resolved one hop with defaults. Chosen from the 64 such models among the
45,000 most downloaded on 2026-09-10 (`docs/eval/census/dataset/self_referential_top45k.json`)
because it is ungated, small, and declares nothing else in metadata, so the self-reference is the
whole graph.

## Why the shape is worth a scenario

Stalnaker et al. (arXiv 2502.04484) found 684 cycles in the declared base-model graph of 760,460
models, and 675 of them were a model declaring itself. That is the most common malformed lineage
declaration on the registry by a wide margin — more common than a freed namespace — and it is the
one a resolver is most likely to mishandle in one of two opposite directions:

- **Follow it.** A frontier that re-enqueues the target loops, or spends a request re-resolving the
  node already in hand. The traversal's `expanded` set already prevents the loop; DEC-031 also
  removes the request, because the target is known before anything is asked.
- **Drop it.** The natural implementation treats a self-reference as noise and emits no edge. That
  erases the fact that the card's lineage metadata is unusable, and a reader of the BOM sees a model
  with no declared base rather than a model whose declared base is itself.

The scenario grades both. `expected-graph.yaml` requires the self-edge with provenance
`asserted-by-card` and the node property `whence:declaration: self-referential`;
`expected-absent.yaml` forbids `contradicted` (a self-reference is not evidence against ancestry),
`verified` (a name resolving to itself establishes nothing about a derivation), the claim that the
model has no upstream, and any guess at the base the author meant (DEC-010).

## What the recording holds

One interaction: the model's own listing. The self-reference is recognised before a request is
made, and the card declares no datasets. The `transformers` package edge comes from
`library_name`, as in every other scenario.

## What the BOM says

`dependencies[]` carries the root's `dependsOn` naming its own purl. CycloneDX does not forbid a
self-dependency and `whence` does not hide one: the component property is where a consumer learns
why it is there.
