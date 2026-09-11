# Fingerprint evidence against lineagebench

**Measured:** 2026-09-10, modelDNA 0.1.0 and Cisco Model Provenance Kit 1.1.0 run as separate
processes; `lineagebench` revision `5f94189b3cd4922ac787df4e387f0c2622903b17`. Evidence files under
`docs/eval/fingerprints/evidence/`, the tools' raw outputs under `modeldna/` and `cisco/`, the
resolutions under `recorded/`, results in `results.json`, scripts `scripts/measure_fingerprints.py`,
`scripts/fingerprint_evidence.py`, `scripts/cisco_evidence.py`. Every figure below replays offline:
the resolutions from the recording, the verdicts from the evidence files. The fingerprinting itself
is not replayed — it read 100–460 MB per model from the registry and is recorded as what it
returned, with the driver that produced it beside it (`modeldna/driver.py.txt`, `modeldna/scenarios-driver.py.txt`).

## What was measured

DEC-029 admits an external weight-level verdict as evidence under a mapping the file declares;
DEC-030 says it attaches only to artifacts a resolution reached. This is the first run of that path
end to end: each of the fifteen `lineagebench` suspects is resolved through the ordinary resolver
(depth 2, structural check on), then the two evidence files are applied in turn, and what moved,
what abstained, and what attached nowhere is counted.

The verdicts are the tools'. Which effect each verdict class has is the operator's, stated in the
file, and stated here.

| modelDNA class | effect | Cisco label | effect |
|---|---|---|---|
| `EXACT_COPY`, `QUANTIZED_COPY`, `FINE_TUNE`, `SAME_LINEAGE` | establishes | `High-Confidence Match` | establishes |
| `LIKELY_MERGE`, `SAME_FAMILY_UNRESOLVED`, `NO_MATCH`, `INSUFFICIENT` | abstains | `Confirmed Match` | **abstains** |
| | | `Weak Match`, `Not Matched`, `Insufficient data` | abstains |

Two rows need a sentence. `NO_MATCH` abstains rather than contradicts because on the dataset's own
limitation case a documented depth up-scale of a Mistral model returns `NO_MATCH`; mapping it to
`contradicted` would have refuted a true derivation. The kit's `Confirmed Match` abstains because
it is not a weight verdict: the kit sets the pipeline score to 1.0 or 0.9 when the architecture or
family *hash* matches, before any weight is compared (`core/lookup.py`, MFI tier 1 and 2). That is
a metadata match, which DEC-020 already treats as necessary and not sufficient. Nothing from either
tool is mapped to `contradicts`.

## Coverage first

| | Pairs |
|---|---:|
| lineagebench pairs the structural check could compare (`lineagebench.md`) | 39 |
| modelDNA verdicts obtained | 39 |
| Cisco scans obtained | 4 suspects, top-5 matches each; 1 pairwise compare |

modelDNA fingerprinted all sixteen ungated models (13 in the 7B–14B range at 294–464 MB each; the
GPTQ repack at 9 MB). The seven gated models stay out of reach without credentials (DEC-009), so
the six positives touching them — the Llama-2, Llama-3, and Gemma derivations — have no fingerprint
verdict and remain `unverifiable` on exactly the ground `lineagebench.md` gave. The kit downloads
full weights (about 15 GB per 7–8B model), so it was run on four suspects and one pair, some
60 GB, and no further.

## modelDNA over the 39 pairs

| Pool | n | `FINE_TUNE` | `SAME_LINEAGE` | `SAME_FAMILY_UNRESOLVED` | `NO_MATCH` |
|---|---:|---:|---:|---:|---:|
| Positive | 7 | 6 | 1 | 0 | 0 |
| Negative | 30 | 0 | 0 | 2 | 28 |
| Limitation | 2 | 0 | 0 | 0 | 2 |

Every comparable positive is a positive class at p ≥ 0.9796; every negative is an abstaining
class. The two `SAME_FAMILY_UNRESOLVED` negatives are the two pairs the body check could not
separate — `dolphin-2.9-llama3-8b` against the two Mistral-7B bases, identical on all five
transformer-body fields — at p = 0.578 and 0.583, in the tool's abstention band. Where metadata
cannot tell two families apart, the weights place the pair in the gray zone rather than either
side of it. That is the cell DEC-029 was written for, and the answer is an honest abstention, not
a `verified`.

The GPTQ repack returned `NO_MATCH` at p = 0.13 rather than the abstention the tool's reference
results report for the same pair. Under the declared mapping the difference is invisible — both
abstain — but it is why `NO_MATCH` must not contradict: on a true quantization it would have.

## Applied to fifteen resolutions

Each resolution receives the verdicts whose subject is its root. A benchmark-wide file applied
whole would report every other suspect's verdicts as unattached, which measures the file's shape.

| Evidence file | verdicts about a root | established | created | abstained | unattached | contradicted |
|---|---:|---:|---:|---:|---:|---:|
| `lineagebench-modeldna.json` (39) | 35 | **5** | **1** | 28 | 1 | 0 |
| `lineagebench-cisco.json` (5) | 5 | 0 | 0 | 4 | 1 | 0 |

The four modelDNA verdicts about no root are the parent-versus-parent negatives, whose subjects
are bases and not suspects.

**Five declared edges moved `unverifiable → verified`**, each keeping the card's evidence beside
the fingerprint's:

| Edge | class | p |
|---|---|---:|
| `HuggingFaceH4/zephyr-7b-beta` → `mistralai/Mistral-7B-v0.1` | `FINE_TUNE` | 0.9985 |
| `teknium/OpenHermes-2.5-Mistral-7B` → `mistralai/Mistral-7B-v0.1` | `FINE_TUNE` | 0.9985 |
| `Qwen/Qwen2.5-7B-Instruct` → `Qwen/Qwen2.5-7B` | `FINE_TUNE` | 0.9985 |
| `Qwen/Qwen2.5-14B-Instruct` → `Qwen/Qwen2.5-14B` | `FINE_TUNE` | 0.9985 |
| `mistralai/Mistral-7B-Instruct-v0.3` → `mistralai/Mistral-7B-v0.3` | `FINE_TUNE` | 0.9985 |

**One edge was created.** `Qwen/Qwen2.5-Coder-7B-Instruct` declares `Qwen/Qwen2.5-Coder-7B`, which
declares `Qwen/Qwen2.5-7B`; the resolution reaches both. modelDNA's verdict is about the pair
(Coder-7B-Instruct, Qwen2.5-7B) — `SAME_LINEAGE`, p = 0.9796 — so the edge it establishes is the
direct one, `verified-by-weights`, beside the two-hop chain the cards give. A fingerprint is a
statement about two byte sequences; it establishes the relationship between them and says nothing
about the intermediate the cards name. Both are in the graph, and a reader sees a verified
grandparent and two asserted hops.

**One verdict attached nowhere.** `mlabonne/AlphaMonarch-7B` against `mistralai/Mistral-7B-v0.1`
returned `FINE_TUNE` at p = 0.9984, and Mistral-7B-v0.1 is not a node the depth-2 resolution
reaches: the card's chain runs AlphaMonarch → NeuralMonarch → Monarch and stops at the ceiling.
The evidence is real and the graph does not extend to meet it (DEC-030). It is also the one place
the tool's class and the documented kind disagree — the dataset calls this a merge chain, the
weights read as a fine-tune of the family base — and because the verdict did not attach, the
disagreement is recorded here and not on any edge.

**Kind disagreements on attached edges: 0 of 6.** Each established class is consistent with the
declared relation (`derives-from` with `FINE_TUNE` or `SAME_LINEAGE`).

## Two verifiers on the same pairs

| Pair | modelDNA | Cisco kit |
|---|---|---|
| zephyr-7b-beta → Mistral-7B-v0.1 | `FINE_TUNE` 0.9985 | `Confirmed Match` 1.0 — MFI tier 1; identity score 0.9032 |
| OpenHermes-2.5-Mistral-7B → Mistral-7B-v0.1 | `FINE_TUNE` 0.9985 | `Weak Match` 0.6854 |
| Qwen2.5-7B-Instruct → Qwen2.5-7B | `FINE_TUNE` 0.9985 | not in the kit's top 5 (five tier-1 `Confirmed Match` siblings, including NextCoder-7B at identity 0.6338, rank above it) |
| dolphin-2.9-llama3-8b → Mistral-7B-v0.1 | `SAME_FAMILY_UNRESOLVED` 0.578 | pairwise `Not Matched`, identity 0.4777 |
| dolphin-2.9-llama3-8b → Meta-Llama-3-8B | no verdict (gated) | not in the kit's top 5; `High-Confidence Match` to gpt2-medium at 0.8507 |

On the one pair where both tools gave a weight verdict about a documented derivation,
they disagree in label: OpenHermes is a `FINE_TUNE` at 0.9985 to one and a `Weak Match` at 0.6854
to the other. On the same-shape negative they agree: both decline. The kit's `Confirmed Match`
for zephyr is a metadata match, which is why the file maps it to `abstains`; its identity score
for the same pair, 0.90, would have crossed its own 0.75 threshold had the gate not fired first.
`gpt2-medium` as a `High-Confidence Match` for a Llama-3 fine-tune is a false positive on the kit's
own terms. The two-source conflict DEC-029 left open did not arise: no edge received an
`establishes` from both files, so no edge carries two fingerprint records.

The kit's evidence file established nothing here. Its one `establishes` verdict — zephyr against
`Mistral-7B-Instruct-v0.3`, a same-family wrong parent at 0.889 — named an artifact zephyr's
resolution does not reach, and was unattached (DEC-030) rather than becoming a `verified` edge to
the wrong base.

## Phase 4: the three recorded scenarios

Fingerprints were attempted for every model-to-model edge in `transferred-namespace`,
`quantized-republication`, and `merge-lineage`, at the recorded revisions. Raw records under
`modeldna/scenarios/`.

| Scenario | Pair | Result |
|---|---|---|
| merge-lineage | GGUF root → `failspy/Llama-3-8B-Instruct-MopeyMule` | **`QUANTIZED_COPY` 0.9985** |
| merge-lineage | GGUF root → `zementalist/llama-3-8B-chat-psychotherapist` | `NO_MATCH` 0.035 |
| merge-lineage | GGUF root → four LoRA adapters | no verdict: no safetensors or GGUF weights (adapter repositories) |
| quantized-republication | GGUF root → EXL2 source | no verdict: the EXL2 repository's index names `model-00001-of-000017.safetensors`, which answers 404 |
| transferred-namespace | archive → redirect target | no verdict: a diffusers checkpoint; one tensor appears in multiple shards and the reader stops |

The merge-lineage result is the kind disagreement in the wild. The card declares a six-parent
`model_stock` merge and names `MopeyMule` in five of ten slices; the weights of the GGUF read as
a **quantized copy of MopeyMule alone**, and the second full-model parent returns `NO_MATCH` at
p = 0.035. Applied to the scenario's replay
(`docs/eval/fingerprints/evidence/scenario-merge-lineage.json`), the `merged-from` edge to
MopeyMule moves to `verified` with class `QUANTIZED_COPY` verbatim on the evidence, its
`declared_count: 5` intact, the node-count ceiling still reported, and `compositions.aggregate:
incomplete` still emitted. Nothing relabels the relation (DEC-010): the BOM now says the card
asserted a merge and the weights established a quantized copy, in two records on one edge.
Whether a merge whose weights are indistinguishable from one parent is a merge is not this tool's
question; that the two statements differ is.

The two no-verdict rows are limits of the fingerprinter, recorded as such. EXL2 is a format it
does not read, and the failing HEAD is on a shard the repository's own index names; the diffusers
layout is outside its architecture support. Both edges stay `unverifiable` on the ground the
truth sets already give — and `transferred-namespace`'s own truth set says weight comparison could
not settle it anyway, since the original is no longer retrievable.

## What this changes

Nothing in the resolver, and one thing in what the tool can say. Before this measurement every
edge in every recorded scenario was `unverifiable`, and the README said no edge was ever verified.
Now five documented derivations and one undeclared grandparent carry `verified-by-weights` with
the file, tool, version, class, and probability on the evidence — and every one of them still
carries the card's assertion as a separate record. Six of thirteen positives remain out of reach
because their bases are gated, one because the graph stops before the evidence, and the two
same-shape negatives stay in the gray zone where they belong.

The mapping table above is the load-bearing artefact. Change one row and different edges verify;
that is why it is declared in the file, digested onto every record it produces, and printed here.
