# 2026-09-03 — Measuring instead of asserting

Two pieces of work, both of which replaced a claim with a number, and both of which found the claim
was doing more work than the evidence supported.

## merge-lineage

DEC-024 added a node-count ceiling because a merge names many parents at depth one. Nothing but a
synthetic test exercised it — a check that the code does what the code does. `merge-lineage` records
a real merge: ten `base_model` entries naming six artifacts, four of them LoRA adapters.

Building the scenario found three defects, and the order they surfaced in is the interesting part.

**Ten declarations became ten edges.** mergekit writes one entry per merge slice, so one parent was
declared five times and the graph said the model had ten dependencies where it has six. The
repetition is not noise — it says how much of the merge that parent accounts for — so the fix is one
edge carrying `declared_count`, not deduplication that throws the information away.

**The ceiling did not say what it skipped.** It reported "the remaining frontier was not followed",
which is a silent truncation with a sentence acknowledging it. DEC-007 requires that a ceiling name
what it did not follow, and I had written DEC-024 claiming it did. It names the five branches now,
and the five matter individually: one full model and four adapters, and a reader who cares about
adapter provenance needs a different half of that list than one who cares about base weights.

**`max_nodes` was never read by the evaluator**, so the scenario passed against a ceiling that never
fired. Worse, the scenario test built its own resolver from the same `target.yaml`, so there were two
readers of that file and they drifted the moment the field was added. One place now.

The scorer had the matching gap: removing the deduplication emitted five identical edges and every
scenario still passed. That is the third time in two days that the answer to "why did this pass" was
"nothing looked", and the pattern is worth naming — **a check that is not mutation-tested is a check
whose absence is indistinguishable from its success.**

What the graph shows that the card does not: at depth two the four "merge parents" declare `adapts`
edges of their own, over two different bases, one of them a 4-bit quantized variant. The tool does
not second-guess the declared relation — an adapter can genuinely be merged into weights — it keeps
resolving, and the graph makes the question visible without answering it.

## The prose scanner, at 1,091 cards

DEC-023 recorded a precision figure over 174 cards from three searches. That is thin enough that the
decision it justified — precision over recall, do not widen the pattern — was really a preference
with a number attached.

The sample is now 1,091 cards from twelve searches. 389 declare no `base_model` and are the only
cards the scanner is ever run against; on those it makes 11 claims and all 11 are right. One further
false-positive class appeared at that size: `--quantized-from--> FP16`. A dtype read as an artifact,
systematic rather than incidental, because naming the source precision is how a quantization card is
normally written.

**The recall question is now answered rather than disclaimed.** 248 candidates mention a derivation
and produce no claim, which sounds bad and mostly is not — 47 are cards the scanner is right to
ignore, including unfilled template boilerplate and models "based on the transformer architecture".
The largest real gap is "based on" / "built on", 59 cards. I widened the pattern to accept it and
measured: claims went from 11 to 75, and the additions named datasets the model was fine-tuned *on*,
models it was merely compared to, bare fragments like "v2", and a Mistral quantization acquiring a
Llama-2 ancestor. English uses "based on" for every relation a card has to another name.

So not widening is a measurement now, and a test pins it so nobody widens it casually on the grounds
that it obviously should.

## The instrument had the bug it exists to detect

My first attempt at the recall figure came back clean: zero cards stating a derivation the scanner
had missed. It was wrong. Rate-limited fetches were being swallowed by a bare `except` and reported
as "no card", so the measurement was mostly 429s. A tool built to insist that absence of evidence is
not evidence of absence had a measurement script doing exactly that about itself.

Cards are cached on disk now, 429s are retried, and anything still unreadable is counted and printed
as excluded. The number that made me check was suspicious — zero is rarely a real answer — which is
the only reason it did not go into a decision log.

## Open

The 1,091 cards are the most-downloaded matches for twelve terms, and popular cards are better
written than the median. What the pattern does on the long tail is unmeasured.
