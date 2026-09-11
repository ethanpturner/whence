# The structural check against lineagebench

**Measured:** 2026-09-10, against `lineagebench` revision `5f94189b3cd4922ac787df4e387f0c2622903b17`
(Apache-2.0). Recording under `docs/eval/lineagebench/recorded/`, results in
`docs/eval/lineagebench/results.json`, script `scripts/measure_lineagebench.py`. Every figure below
replays offline from the recording and the replay is byte-identical to the live capture.

## What was measured, and what was not

DEC-020's structural check compares five transformer-body fields and can only `contradict` a
`derives-from` claim. Its false-positive rate was measured — 0 over 33 comparable real declared
fine-tunes — and its detection rate was not, because that sample held no mistaken declaration.

`lineagebench` labels 15 suspect models against 8 candidate parents from the publishing
organizations' own documentation. Its positive pool is 13 documented derivations. Its negative pool
is 107 pairs that are *not* derivations: each positive suspect against every cross-family wrong
parent, plus every cross-family parent-versus-parent pair. Two further cases — a depth up-scale and
a GPTQ repack — are out of its positive pool by design and are scored separately. The script
reconstructs those pools from the dataset's files and refuses to run if the sizes disagree with
the dataset's own `metrics.json`.

These negatives are the dataset's constructions. **No card on the registry declares any of them**,
so this measures the check against pairs it is handed, not against mistaken declarations in the
wild. That figure is still unmeasured, for the same reason as before: none has been found.

## Coverage first

| | Models |
|---|---:|
| In the dataset | 23 |
| Gated (`config.json` answers 401 without credentials) | 7 |

The seven are `meta-llama/Llama-2-7b-hf`, `meta-llama/Meta-Llama-3-8B`,
`meta-llama/Meta-Llama-3-8B-Instruct`, `google/gemma-2b`, `google/gemma-2b-it`,
`google/gemma-2-9b`, `google/gemma-2-9b-it`. The check runs unauthenticated (DEC-009), so every
pair touching one of them returns `unverifiable` with the configuration named as unavailable. That
is 77 of the 107 negatives and 6 of the 13 positives. A pair the check could not read is not a
pair it missed; it is a pair it did not reach, and the two are reported apart.

## Results

| Pool | n | Contradicted | Compatible | Configuration unavailable |
|---|---:|---:|---:|---:|
| Positive (documented derivations) | 13 | **0** | 7 | 6 |
| Negative (not derivations) | 107 | **28** | 2 | 77 |
| Limitation cases | 2 | 1 | 1 | 0 |

**Positives.** 0 contradictions over the 7 comparable pairs. With DEC-020's 33, the check has now
returned no false contradiction on 40 comparable real derivations.

**Negatives.** Of the 30 negatives that reached a comparison, the check contradicted 28. The two
it did not are `cognitivecomputations/dolphin-2.9-llama3-8b` — a Llama-3-8B fine-tune — against
`mistralai/Mistral-7B-v0.1` and `mistralai/Mistral-7B-v0.3`. Llama-3-8B and Mistral-7B carry an
identical body on all five fields: hidden size 4096, 32 layers, 32 heads, 8 key-value heads,
intermediate size 14336. This is the same-shape-independent case DEC-020 said the check cannot
separate, now observed on published models rather than argued. Had `meta-llama/Meta-Llama-3-8B`
itself not been gated, its two parent-versus-parent pairs with the Mistral bases would have
landed in the same cell.

So on labelled negatives the check reaches a comparison for 30 of 107 and contradicts 28 of those
30. Both denominators matter, and the second is the one that describes the instrument: where it
can read both files and the families differ in body, it says so; where two families share a body,
it cannot, and says `unverifiable`.

**Limitation cases.** `upstage/SOLAR-10.7B-v1.0` against `mistralai/Mistral-7B-v0.1` is
**contradicted** on `num_hidden_layers` (48 against 32). SOLAR is a documented depth up-scaling of
a Mistral-based model, so this is the first real instance of the class DEC-020's finding text
anticipates — "re-architecting is real and is sometimes tagged as fine-tuning" — and the check's
detail sentence is what it should be: the relationship is not the one a fine-tune declaration
would assert, and it does not follow that no relationship exists. SOLAR's own card declares no
`base_model`, so the resolver would emit no edge here; the contradiction appears only because the
dataset supplies the parent. `TheBloke/Mistral-7B-v0.1-GPTQ` against its base is compatible under
`derives-from`; as a `quantized-from` relation it is outside the check's scope (DEC-020) and the
verdict would be `unverifiable` on that ground instead.

## Two things seen on the way

**A cross-namespace redirect.** `cognitivecomputations/dolphin-2.9-llama3-8b` answers 307 to
`dphn/dolphin-2.9-llama3-8b`. Both organizations exist. Under DEC-017 a resolver following this
edge would flag `whence:redirect: cross-namespace`; here it is bookkeeping, because the dataset
names the suspect under its old namespace and the configuration is the same file. It is recorded
because a benchmark's own identifiers drift, and a tool that pins by name would be comparing
whatever the old name serves today.

**What was not run.** DEC-022's tensor-inventory comparison was rejected at a 21% false-positive
rate and its code is not in the tree. Re-implementing a rejected mechanism to produce a side figure
is not a measurement of anything the tool does; the safetensors index is one request per model if
that decision is ever reopened.

## What this changes

Nothing in the check. The two numbers it lacked are now stated with their denominators: 0 of 7
positives contradicted, 28 of 30 comparable negatives contradicted, with 77 of 107 negatives
unreachable without credentials. The compatible cell — two Llama-3 derivatives that the check
cannot tell from Mistral derivatives — is the exact gap DEC-029 admits an external
weight-fingerprint verdict to fill; modelDNA's reference results on this dataset separate those
pairs with a maximum negative score of 0.66 against a minimum positive of 0.94.
