# 2026-09-03 — Working the queue: two scenarios captured, and the upstream report that was already filed

Cleared the three items queued yesterday. Two produced work I expected; the third produced a
correction.

## withdrawn-base

The throttle cleared, so `microsoft/WizardLM-2-7B` was confirmable: still 401, and
`MaziyarPanahi/WizardLM-2-7B-GGUF` (157,179 downloads) declares it as base. Captured all three
responses including the `microsoft` namespace, which resolves.

That last request is the scenario. `deleted-namespace` and `withdrawn-base` look nearly identical —
both have an unreachable base — and they grade opposite behaviour. The difference is who controls
the name: a freed namespace is a hijack opportunity, a held one is a dead end. Distinguishing them
costs exactly one extra request, resolving the namespace rather than only the repository, and that
request separates "this dependency is gone" from "anyone can become this dependency."

So `withdrawn-base` forbids the `whence:risk` property that `deleted-namespace` requires. If the
tool flags every unreachable node as re-registrable, the flag stops meaning anything and the
scenario it was built for is worthless.

**The trap in this one is the 401 body:** `{"error":"Invalid username or password."}`, returned to a
request that carried no credentials at all. A tool that believes the prose concludes it is
misconfigured, and then aborts, or retries with backoff, or classifies the response as transient
under DEC-014 and marks the whole run partial. All three wrong. The rule this forces is worth
stating plainly: **response class comes from the status code, never from the prose in the body.**
Registry error strings are written for humans debugging their own scripts and describe the most
common cause rather than the actual one. Reading them as ground truth imports the registry's guess
about the caller into the tool's model of the world.

## What choosing that subject caught — DEC-015

The base declaration is `base_model:quantized:microsoft/WizardLM-2-7B`. The registry supplies the
derivation qualifier and my `Relation` enum had no term for quantization, so the edge would have
flattened to `derives-from`.

Checking how common that is settled it. Across 3,206 qualified `base_model:` tags from the top 4,000
models: **quantized 1,030, finetune 507, adapter 39, merge 27.** Quantization is the most commonly
declared derivation in the ecosystem, at about twice the rate of fine-tuning — and it had no name in
the data model. The most common real relation was the one I had not modelled.

> **Corrected 2026-09-03**, see `2026-09-03-verifying-the-measurement.md`. The 3,206 figure
> double-counts, the distinct-reference count is 1,603, and the ecosystem-wide claim about
> quantization does not survive a second sample. Left as written because this is a dated record of
> what I believed at the time.

The consequence is not bookkeeping. DEC-005 already anticipates that quantized and merged models are
where weight comparison performs worst, so an edge carrying its qualifier tells phase two in advance
which of its results to distrust. A flattened edge presents every derivation as equally checkable.

Also decided: a **bare** `base_model:` declaration records `derives-from` with the kind unspecified
and is never assumed to be fine-tuning. Given the distribution above, that assumption would be wrong
more often than right, and it is the inference DEC-010 forbids.

Relation stays a closed enum rather than becoming open like `NodeKind`, because relation kind drives
phase-two method selection — an unrecognized relation should stop the run, not normalize to
something plausible.

## transient-failure

Built on the same target as `declared-base`, deliberately. Same subject, same revision, one variable
changed: the base resolution is throttled instead of succeeding. Their correct outputs then diverge
sharply, which is the cleanest available check that the tool is not quietly degrading one into the
other.

The near-miss is the whole scenario. The obvious implementation emits the edge with
`verdict: unverifiable` — the tool could not verify it, after all — and that is invisible
downstream: a consumer cannot distinguish it from `prose-only-base`, where the tool *did* look and
genuinely could not tell. So the edge is forbidden at any verdict, and both composition aggregates
are forbidden too, since `unknown` means examined-and-inconclusive and `incomplete` means
stopped-at-a-chosen-ceiling. Neither describes a request that was refused.

`expected-unresolvable.yaml` is empty on purpose, and the emptiness is the assertion.

The recording is **composed rather than fabricated**: every body is an authentic capture, but the
429 and the 200 came from different sessions. That is a real distinction from the hand-written
fixture ruled out in `deleted-namespace` — the objection there is that response shapes are the part
most likely to be got wrong, and composing real captures keeps the shapes the registry's own. The
alternative, hammering a public API until it refuses in order to obtain a fixture, is not a
reasonable thing to do.

Redacted the IP address the 429 body echoes back before committing it. Checked the tree for leaks
afterwards.

## The upstream report — and the correction

I had this queued as "write the CycloneDX report," with three scenarios' experience behind it as the
threshold I had set. Searching the specification repository first changed the task entirely.

**It is already open: CycloneDX/specification#135, "Support more relationship types," filed
2022-03-04.** Its own suggestion 1 — add a `properties` object to the relationship objects — is
precisely the change that would remove both costs recorded in my mapping document. And its most
recent comment, from 2025-08-12, raises the ML case independently: a model depending on datasets for
initial training, fine-tuning, and RAG, arguing that "the nature of the relationship has implications
on vulnerabilities/licensing/compliance."

So there was nothing to report. Had I written the issue as planned I would have filed a duplicate on
a four-year-old thread and been, correctly, ignored.

What the thread does lack is measurement. The maintainer asked in 2023-01-17 for concrete examples of
relationship types CycloneDX does not already support, and the answers since have been illustrative
rather than quantified. The tag distribution is a direct answer to that question — it converts "we
would like typed relationships" into "the registry already publishes four of them and one accounts
for a third of all declarations." Drafted a comment carrying that, the namespace-reuse consequence,
the string-join workaround, and the reason `conformance.score` cannot hold a three-valued verdict.

Deliberately narrowed the ask to suggestion 1. A stalled issue is better served by making the
smaller change easy to accept than by broadening the request.

**Not posted.** It is an outward-facing action on someone else's project and that is not mine to
take unilaterally. Held at `docs/upstream/cyclonedx-135-comment.md` with the pre-posting checks
listed.

## The pattern, third instance

DEC-013 was the serialization boundary. DEC-014 was the network boundary. This entry adds a third
place the same care was needed and nearly was not applied: **the assumption that a gap I found is a
gap nobody else has found.** The check cost two API queries and changed the output from a duplicate
issue into a contribution.

## Open next

- `deleted-namespace` still needs a real capture: authenticated token, sampling frame drawn from the
  download tail rather than the head. It is the only `planned` scenario left.
- The initial commit. Five scenarios, fifteen decisions, and one runnable check is a reasonable
  first commit, and the repository has been uncommitted for two days.
- Decide whether to post the #135 comment.
