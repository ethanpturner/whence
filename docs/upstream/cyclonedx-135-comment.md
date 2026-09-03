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

> Adding measured data to the ML case raised above, since the thread has examples but no
> distribution figures.
>
> I'm building a tool that resolves a published model's dependency graph and records, per edge,
> whether a relationship was **asserted** by the publisher or **established** by the tool. That
> claimed-versus-verified distinction is the entire output, and it is a property of the edge rather
> than of either endpoint.
>
> **How common are typed relationships in practice?** Hugging Face publishes the derivation kind in
> its `base_model:` tags. Counting distinct references in two samples:
>
> | Declared relation | Top 4,000 by downloads (n=1,603) | 1,000 most recently modified (n=186) |
> |---|---:|---:|
> | `quantized` | 1,030 (64.3%) | 63 (33.9%) |
> | `finetune` | 507 (31.6%) | 84 (45.2%) |
> | `adapter` | 39 (2.4%) | 27 (14.5%) |
> | `merge` | 27 (1.7%) | 12 (6.5%) |
>
> Two things stand out. **Every reference in both samples carries a qualifier — zero were bare.**
> The registry always states the derivation kind, so collapsing these into `dependsOn` discards
> information that is always present, not occasionally present.
>
> And **which kind dominates depends on how you slice the registry**: quantization leads by
> download-weighted popularity, where GGUF republications of popular models are overrepresented,
> while fine-tuning leads among recently-modified models. That instability is the practical
> argument — a consumer cannot pick a sensible default relation type, because no default holds
> across slices of the same source.
>
> It also matters technically rather than only descriptively. Weight-level lineage comparison
> behaves very differently on a quantized derivation than on a fine-tune, so an edge that carries
> its qualifier tells a downstream verifier where its method is unreliable. A flattened edge
> presents every derivation as equally checkable.
>
> **The security consequence.** The case that pushed me here is model namespace reuse: when a
> publisher's account is deleted the namespace is freed and anyone may re-register it, so a
> dependency pinned by name resolves to whatever later occupies it. Palo Alto Unit 42 documented
> orphaned namespaces reachable through two major hosted model catalogs
> (https://unit42.paloaltonetworks.com/model-namespace-reuse/). Expressing this needs two facts on
> the edge — that the target was asserted rather than resolved, and that the reference is
> re-registrable. Neither has anywhere to go today.
>
> **What I had to do instead.** `dependency` has `ref`, `dependsOn`, and `provides`: no `bom-ref`
> and no `properties`, so an edge can be neither addressed nor annotated. I split each edge across
> two structures — `dependencies` for topology, one `declarations.claims` entry per edge for
> meaning — and join them by matching `claims.target` against the purl embedded in
> `claims.predicate`. The join is deterministic but it is my convention, not something the format
> expresses, so a consumer that does not know it sees claims and dependencies as unrelated.
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

## Pre-posting checks

- [x] **Figures re-verified 2026-09-03.** The head sample reproduces exactly. An earlier draft
      cited "3,206 tags" and called quantization the most common derivation in the ecosystem; both
      were wrong. The registry emits a bare *and* a qualified tag per reference, so 3,206 double-counts
      and the distinct-reference count is 1,603. The ecosystem-wide claim did not survive the
      recency sample. Corrected above and in DEC-015.
- [x] Unit 42 reference carries a link.
- [x] Does not overstate: "I'm building" is accurate for a design-stage project and implies no
      shipped tool.
- [ ] **Sampling limitation to disclose if asked.** Both samples are registry listings, not a
      random sample of the corpus. The `skip` parameter is deprecated and capped, so deeper
      sampling needs link-header pagination; neither sample reaches the long tail. The comment
      states each sample's basis rather than generalising to "the ecosystem" — keep it that way in
      any follow-up.
- [ ] Owner decision to post.
