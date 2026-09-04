# 2026-09-04 — The last two designed scenarios, and three things they found

`quantized-republication` and `no-lineage` were named in the registry from the start and never
built. Building them closed the gap between what the corpus claims to cover and what it covers —
and, as has now happened every time, the scenarios found more than they were written to grade.

## What each is for

**quantized-republication** is a GGUF requantization of an EXL2 quantization of a distillation,
across three namespaces. It is the hardest case any weight-level method will ever face: every step
is lossy and irreversible, so no digest matches anything upstream and no structural check bridges it.
Whatever phase two eventually verifies, it will not verify this. The chain is provenance metadata or
it is nothing.

And the metadata breaks in the middle. `LoneStriker/…-exl2` declares no base at all, while its own
repository name spells the missing link out in full — and the guess is almost certainly correct,
which is exactly what makes it the corpus's strongest invention trap. A resolver that repairs chains
from repository names is right here and wrong wherever a name is aspirational, coincidental, or
deliberate, and nothing in its output distinguishes the four cases. This is the artifact an attacker
republishing someone else's weights under a familiar name would most want a tool to complete for
them.

**no-lineage** is `bert-base-uncased`. Its graph is not empty — two corpora and a library — and the
point is that no derivation edge appears at all. A tool that emits nothing when it finds no lineage
is indistinguishable from one that failed to run, and "this model has no ancestor" is a statement
the graph has to be able to make. Its card is also full of derivation verbs pointing the wrong way:
"can be fine-tuned on a downstream task" describes descendants.

## Three latent defects

**A non-JSON body was discarded live.** `LiveRegistry` returned `None` for anything that failed
`r.json()`, so the prose scanner had never seen a card against the real registry. It worked in
replay — the recorded loader wraps text as `_raw` — and found nothing in every live run, silently.
The two sides of the seam disagreed about a shape, which means the recordings had been proving
nothing about the thing they stand in for on that path.

**`distilled-from` was not a Relation.** The scanner had emitted it since the day it was written.
Nothing ever constructed it, because the only recorded card carrying prose says "fine-tuned". The
first live capture of a card saying "distilled" raised `ValueError: not a valid Relation` — DEC-015
working exactly as designed, refusing to normalize a relation nobody had decided about, at the cost
of one crash rather than a corpus of quietly wrong edges. It is its own relation now (DEC-027): a
student's weights are not derived from its teacher's at all, so no weight-level method can ever
confirm a distillation, where a fine-tune at least leaves a body to compare.

Both of these are the same shape as the `max_nodes` finding yesterday: **a path that no scenario
exercises is a path with no evidence behind it**, however carefully it was written.

## The copied card, and knowing when to stop

The exl2 repository republishes DeepSeek's model card verbatim — normal practice for a
quantization. So the scanner reads DeepSeek's sentence about *their* family ("we have open-sourced …
six dense models distilled from DeepSeek-R1") as a claim about this artifact, and emits
`--distilled-from--> DeepSeek-R1`. That is approximately true and specifically wrong: this is a
quantization *of* one of the six.

I tried three narrowings and measured each against the 389-card candidate sample. Suppressing cards
that never name their own repository: catches it, loses two correct claims. Suppressing sentences
describing a plurality: catches it, and also suppresses all six official DeepSeek distillations,
which carry the identical sentence on their own cards where it is correct. Requiring the sentence's
subject to be this artifact: sound in principle, and against real names it discriminates nothing,
because `DeepSeek-R1-Zero` in the lead-in matches `DeepSeek-R1-Distill-Llama-70B…` under any rule
loose enough to handle real naming.

Three heuristics deep with no clean discriminator is the signal to stop tuning and write it down.
DEC-028 records the limitation, `quantized-republication` pins the behaviour so the corpus is not
silent about the tool's weakest output, and a test holds it.

**The more useful thing the measurement revealed:** 6 of the scanner's 11 claims are right by family
membership rather than by reading a self-description. The DeepSeek distillations' own cards state
the family sentence, and the claim is correct only because the artifact happens to be one of the
six. DEC-023's 11-of-11 still holds as a fact about output — and the mechanism behind it is weaker
than the number implies, which is worth saying out loud in the same place the number is quoted.

## Open

Comparing a card against its declared upstream's card would detect verbatim republication directly,
and would cost one request on a path that already fetches the base. It is the first thing to try if
this class grows. It is not attempted now because the sample contains exactly one instance, and
building a mechanism on one example is how `transferred-namespace`'s original premise got written
wrong.
