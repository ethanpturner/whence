# 2026-09-03 — Verifying the measurement, and finding it wrong twice

Set out to tick the first box on the #135 draft's checklist: re-verify the tag counts. The counts
reproduced exactly and the claim built on them was wrong anyway, in two independent ways.

## The counts reproduced; the denominator did not

Re-ran the sweep. Identical output: 3,206 `base_model:` tags across the top 4,000 models by
download, quantized 1,030, finetune 507, adapter 39, merge 27.

Then noticed the arithmetic. **1,030 + 507 + 39 + 27 = 1,603, which is exactly the count of bare
tags.** That is not a coincidence, and checking confirmed it: the registry emits *both* a bare tag
and a qualified tag for every reference. Of 1,603 distinct references, 1,603 appear in both forms.
Zero appear bare-only. Zero appear qualified-only.

So "3,206 tags" double-counts, and every figure I had framed against it was framed against a
denominator twice the real one. The distinct-reference count is 1,603.

This makes the underlying argument *stronger* rather than weaker — quantization is 64% of declared
derivations rather than 32% of an inflated total, and **every reference carries a qualifier**, so a
generic relation discards information that is always present rather than sometimes present. But the
number I published was wrong, and it was wrong in the direction of sounding more impressive.

## The headline claim did not survive a second sample

The draft said quantization is the most commonly declared derivation *in the ecosystem*. I had one
sample: the download-ranked head. Took a second, the 1,000 most recently modified models, and the
top two invert.

| Relation | Head (n=1,603) | Recent (n=186) |
|---|---:|---:|
| quantized | 1,030 (64.3%) | 63 (33.9%) |
| finetune | 507 (31.6%) | **84 (45.2%)** |
| adapter | 39 (2.4%) | 27 (14.5%) |
| merge | 27 (1.7%) | 12 (6.5%) |

Sensible in hindsight. Download-weighted popularity overrepresents GGUF republications of a small
number of popular models — one base model spawns dozens of quantizations, each accumulating
downloads. Recency measures what people are currently making, which is fine-tunes.

The instability turns out to be a better argument for the feature request than the original claim
was. "Quantization is most common" invites the reply that a tool could default to it. "Which kind
leads depends on how you slice the same registry" does not — it says no default is safe, which is
precisely why the qualifier has to be carried rather than inferred.

## What got corrected

DEC-015's decision is unchanged; all four kinds still need names and the reasoning holds. Its
*evidence* was rewritten, with an explicit correction paragraph rather than a silent edit, because
a decision log that quietly revises its own basis is worth less than one that shows the revision.

Also downgraded DEC-015's bare-declaration rule from load-bearing to **defensive**. It was written
to handle "the remainder" of bare tags, and there is no remainder — no bare-only reference exists in
either sample. The rule stays for other registries and for the possibility that this one's tagging
changes, but it is no longer justified by evidence from this registry, and saying so is more useful
than leaving it looking empirically grounded.

`withdrawn-base/scenario.md` carried the same numbers and was corrected. The 2026-09-03 journal
entry was annotated rather than rewritten — it is a dated record of what I believed at the time, and
editing it to look correct would defeat its purpose.

**The first commit's message carries the wrong figure and cannot be amended.** Recorded in DEC-015's
correction paragraph, which is where someone tracing the claim would land.

## What this says about the checklist

The checklist item was "verify the tag counts reproduce." They did. Reproducibility caught nothing,
because the error was not in the measurement but in what I claimed the measurement meant — a
denominator I never examined, and a generalisation from a single non-random sample.

Worth carrying forward: **re-running a query is not verification.** The questions that found both
errors were "what should these numbers sum to?" and "does this hold in a different slice?" Neither
requires new data collection and neither is a repeat of the original work.

That is the fourth instance of the pattern this project keeps hitting. DEC-013 was the
serialization boundary, DEC-014 the network boundary, #135 the assumption that a gap I found was
unfound — and this is the assumption that a number I computed correctly means what I said it means.

## Method note for next time

The `skip` parameter is deprecated and capped — deep offsets return an error directing callers to
the `links` response header. Both samples here are registry listings and neither reaches the long
tail, so no claim in the draft generalises past the sample it names.

That limit also blocks `deleted-namespace`, which needs a tail sample. Link-header pagination plus
an authenticated token is the prerequisite for both.

## Open next

- Owner decision on posting the #135 comment. Everything on its checklist is now closed except that.
- `deleted-namespace` still needs link-header pagination and a token.
- Pin the vendored schemas to their source commit.
