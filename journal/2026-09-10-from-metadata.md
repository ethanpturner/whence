# 2026-09-10 — From metadata

Two things today, and the second is what made the first necessary.

## The world moved

The README's leading sentence was "no edge is ever `verified`". It was written as a fact about the
registry: cards name a base and stop, so nothing in metadata establishes that a derivation happened,
and the structural check can only contradict. That was true when it was written and it is still true
of metadata. It is no longer true of the world. In April Cisco shipped a Model Provenance Kit that
fingerprints weights against roughly 150 bases and reports 96.4% accuracy on a benchmark it has not
published; in July a single author shipped modelDNA, which fingerprints from 100–300 MB of range
reads, uses eight verdict classes two of which are abstentions, and publishes a labelled dataset on
which it reports zero false positives out of 107. Both are motivated by the sentence this project
rests on — the `base_model` tag is self-reported — and both do the thing the README said could not
be done.

A tool that kept saying `unverifiable` about an edge for which a measured verifier holds evidence
would be overclaiming in the direction nobody watches for: asserting ignorance where evidence exists.
So DEC-029 admits a fingerprint evidence file. The interesting part of the entry is not that it
admits one but the rule for how: the file declares what each of the tool's verdict classes *means*
to `whence` — establishes, contradicts, abstains — and a class without a declared effect is an
error. The reason is in modelDNA's own dataset. `upstage/SOLAR-10.7B-v1.0` is a documented depth
up-scaling of a Mistral model and the tool returns `NO_MATCH` on the layer-count mismatch. A mapping
that read a tool's negative as this tool's `contradicted` would refute a true derivation on its
first outing. That is `tearline`'s rule — the target states the predicate — arriving here for a
verifier rather than an index.

The claim therefore gains two words. "No edge is verified *from metadata*, and `whence` records
which evidence, if any, established it." What the project is, said plainly for the first time, is
the registry-integrity layer and the claim ledger: it decides what there is to fingerprint, whether
a name still resolves to what the card meant, and keeps the card's assertion and the verifier's
verdict as two records. It is not a rival verifier and should stop reading as one.

## The number the check never had

DEC-020 recorded the structural check's false-positive rate — zero over 33 real declared fine-tunes —
and said outright that its detection rate was unmeasured, because the sample contained no mistaken
declaration. lineagebench is the first set of labelled negatives it can be run against: 107 pairs
that are documented *not* to be derivations, built from cross-family wrong parents.

Reconstructing the pools was the first lesson. The dataset's README says same-family pairs are
excluded and does not say what a family is; my first grouping produced 110 negatives against the
dataset's 107, and the script refused to report. The three missing pairs were the two Gemma
generations, which the dataset treats as one family. A reconstructed benchmark that is quietly the
wrong size measures something other than what it names, so the size check stays in the script.

The results, with both denominators. Of 107 negatives, 77 touch one of seven gated models whose
`config.json` answers 401 to an unauthenticated request, and the check returns `unverifiable` on
every one — not a miss, a pair it did not reach. Of the 30 it did reach, it contradicted 28. The two
it did not are a Llama-3-8B fine-tune against the two Mistral-7B bases, and Llama-3-8B and
Mistral-7B share an identical body on all five fields. That is the same-shape-independent case
DEC-020 described as the check's ceiling, and it is now observed rather than argued. On the 13
documented derivations it contradicted none of the 7 it could read, which takes the cumulative
false-contradiction count to 0 of 40.

The limitation case was the surprise. SOLAR against Mistral is **contradicted** — 48 layers against
32 — and SOLAR is a documented derivation. The check's detail text already says the right thing,
that the relationship is not the one a fine-tune declaration asserts and it does not follow that no
relationship exists, and SOLAR's own card declares no base so the resolver would never emit the
edge. But it is the first real instance of the class DEC-020 anticipated in prose, and it is the
sharpest argument for DEC-029's declared mapping: on exactly this model both instruments return
their negative, and both negatives are wrong as contradictions.

One thing seen in passing. The dataset names a suspect as `cognitivecomputations/dolphin-2.9-llama3-8b`
and the registry answers 307 to `dphn/`. Both organizations exist. A benchmark's own identifiers
drift, which is the DEC-002 argument made against a benchmark rather than a pipeline.

## Open next

- The ingest for the evidence file is specified and unbuilt. Its first input should be modelDNA's
  `reference_results.jsonl` on these same pairs, with the SOLAR case as the test that `NO_MATCH`
  maps to abstention.
- Two verifiers on one edge. The agreement matrix between modelDNA and the Cisco kit on these pairs
  is the measurement that should settle DEC-029's open question.
- The seven gated configurations. A read token would reach them and change nothing about the
  method; whether the default run should ever carry one is a DEC-009 question, not a convenience.
