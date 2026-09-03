# Draft comment on CycloneDX/specification#135

**Status: draft, not posted.** Posting is an outward-facing action on a third-party project and
needs a decision from the repository owner first.

**Target:** [CycloneDX/specification#135 — "Support more relationship types"](https://github.com/CycloneDX/specification/issues/135)
(open since 2022-03-04, last activity 2025-08-12).

## Why a comment and not a new issue

The gap `whence` hit is already this issue, and the issue's own suggestion 1 — "add to the existing
relationship objects a properties object" — is the change that would resolve it. Filing separately
would fragment a four-year-old thread.

The most recent comment (2025-08-12) raises the ML case directly: a model depending on datasets for
initial training, fine-tuning, and runtime RAG, where "the nature of the relationship has
implications on vulnerabilities/licensing/compliance." That is the same need.

The maintainer's standing question, from 2023-01-17, is: *"Are there any concrete examples of
relationship types that you'd like CycloneDX to support that it doesn't already?"* The thread has
answered with examples but not with measurements. The contribution below is the measurement, plus
the security consequence and the cost of the workaround.

---

## Draft text

> Adding a measured data point to the ML case raised above, since the thread has examples but no
> distribution data.
>
> I'm building a tool that resolves a published model's dependency graph and records, per edge,
> whether a relationship was **asserted** by the publisher or **established** by the tool. The
> claimed-versus-verified distinction is the entire output, and it is a property of the edge rather
> than of either endpoint.
>
> **How common are typed relationships, in practice?** I harvested `base_model:` tags from the top
> 4,000 models by download on Hugging Face — 3,206 tags carrying an explicit derivation qualifier:
>
> | Declared relation | Count |
> |---|---:|
> | `quantized` | 1,030 |
> | `finetune` | 507 |
> | `adapter` | 39 |
> | `merge` | 27 |
>
> Quantization is the most commonly declared derivation in the ecosystem, at roughly twice the rate
> of fine-tuning. These are not hypothetical relationship types; the registry already publishes
> them and consumers already act on them. Collapsing all four into `dependsOn` discards the
> majority of what the source data says.
>
> It also matters technically rather than only descriptively: weight-level lineage comparison
> behaves very differently on a quantized derivation than on a fine-tune, so an edge that carries
> its qualifier tells a downstream verifier where its method is unreliable. A flattened edge
> presents every derivation as equally checkable.
>
> **The security consequence.** The case that pushed me here is model namespace reuse: when a
> publisher's account is deleted, the namespace is freed and anyone may re-register it, so a
> dependency pinned by name resolves to whatever later occupies it. Palo Alto Unit 42 documented
> orphaned namespaces reachable through two major hosted model catalogs. Expressing this needs two
> facts on the edge — that the target was asserted rather than resolved, and that the reference is
> re-registrable. Neither has anywhere to go today.
>
> **What I had to do instead.** `dependency` has `ref`, `dependsOn`, and `provides`: no `bom-ref`
> and no `properties`, so an edge can be neither addressed nor annotated. I split each edge across
> two structures — `dependencies` for topology, one `declarations.claims` entry per edge for
> meaning — and join them by matching `claims.target` against the purl embedded in `claims.predicate`.
> The join is deterministic but it is my convention, not something the format expresses, so a
> consumer that does not know it sees claims and dependencies as unrelated.
>
> I also could not use `declarations.attestations[].map[].conformance.score` for the verdict, which
> was the obvious-looking home. My verdicts are three-valued — verified, contradicted,
> **unverifiable** — and `score` is a number in [0,1]. Mapping onto it forces "not determined" onto
> the same axis as "not derived," and a consumer reading `0.0` cannot tell them apart. The
> distinction between *refuted* and *unestablished* is the whole point of a provenance tool, so it
> stays a discrete token in evidence data.
>
> **The narrow ask.** Suggestion 1 in the original post — a `properties` array on `dependency` —
> would be sufficient for everything above, and a `bom-ref` on `dependency` would let claims
> reference edges directly instead of by string join. I don't need the generic relationships object
> from suggestion 2 for this use case, and I'd rather see the smaller change land than the larger
> one stay open.
>
> Happy to contribute a worked ML-BOM example against whatever shape you'd prefer.

---

## Notes before posting

- Verify the tag counts reproduce; they came from a single sweep on 2026-09-02 and the sample is the
  download-ranked head, which is stated in the comment but worth re-checking.
- The Unit 42 reference should carry a link when posted.
- Do not overstate: `whence` is design-stage. The comment says "I'm building", which is accurate;
  it should not imply a shipped tool.
