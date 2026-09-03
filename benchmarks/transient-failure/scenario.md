# transient-failure

**What this measures.** That a transient resolution failure produces no verdict, no edge, and no
composition — and that the run says so (DEC-014).

**Subject.** `nvidia/Llama-3.1-Nemotron-70B-Instruct-HF`, **deliberately the same target as
`declared-base`**, at the same revision. The two scenarios differ in exactly one variable: whether
the base resolution succeeds or is throttled. Their correct outputs then diverge sharply, which is
the cleanest way to check that the tool is not quietly degrading one case into the other.

## Why this scenario exists

DEC-014 was written because of something that happened rather than something anticipated. While
sweeping for a `deleted-namespace` candidate, the registry throttled the source address, and every
subsequent request returned 429 — including `Qwen/Qwen2.5-7B` and every other plainly live
repository. A resolver reading any non-200 as absence would have reported roughly 180 live models
as deleted.

The failure has two properties that make it worse than the ambiguity in `prose-only-base`:

**It is transient.** A tool that records the conclusion poisons its own output permanently on the
strength of a condition that cleared in minutes. Absence and denial are stable; throttling is not.

**It is a different category.** `unverifiable` is a claim about what the evidence supports. A rate
limit is a fact about the client. There was no evidence, because there was no look.

## The near-miss the scenario is really testing

The obvious implementation emits the edge with `verdict: unverifiable`, on the reasoning that the
tool could not verify it. That is wrong, and it is wrong in a way that is invisible downstream: a
consumer cannot distinguish it from `prose-only-base`, where the tool *did* look and genuinely could
not tell.

So `expected-absent.yaml` forbids the edge at any verdict, and forbids both composition aggregates
as well — `unknown` means examined-and-inconclusive, `incomplete` means stopped-at-a-chosen-ceiling,
and neither describes a request that was refused.

`expected-unresolvable.yaml` is empty on purpose. `unresolvable` is a provenance class for edges the
tool examined and could not establish; nothing here was examined.

## What survives the failure

The root's own metadata resolved, so edges the tool learned from it and never had to follow —
`trained-on` to the dataset, `requires-package` to the library — are recorded normally. Only the
reference that was actually requested and refused disappears. Partiality is scoped to what was
unreachable, not smeared across the run.

## On the recording

**Composed, not fabricated.** Every response body is an authentic capture from this registry: the
429 from the throttled sweep, the 200 from the `declared-base` capture. Their pairing did not occur
in one session.

That is a different thing from writing a body by hand, which
`deleted-namespace/recorded/README.md` rules out — the objection there is that response *shapes* are
the part most likely to be got wrong, and composing real captures keeps the shapes the registry's
own. Capturing this pair naturally would mean deliberately hammering a public API until it refused,
which is not a reasonable thing to do to obtain a fixture.

The 429 body echoes back the requesting IP address; that value is replaced with `REDACTED`. Nothing
in the tool's behaviour depends on it.

## Pass condition

Two edges recovered; **no** edge to `meta-llama/Llama-3.1-70B-Instruct` at any verdict; no
composition scoped to it; the report marked partial with that reference named in
`transient_failures`; and a non-zero exit.
