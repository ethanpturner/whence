# Two records on one edge

The session that built DEC-029's ingest and ran it against `lineagebench`.

## What changed

`whence resolve --evidence FILE` exists. A `FingerprintEvidenceFile` is read as inert JSON, every
verdict class it uses must carry a declared effect, and each verdict is applied to the graph under
that effect: `establishes` moves a declared edge to `verified` with `verified-by-weights` and
appends the fingerprint as a second `Evidence` beside the card's; `contradicts` moves it down;
`abstains` does nothing. Where no card declares the pair and both artifacts are nodes the run
reached, `establishes` creates the edge. Anything naming an artifact the resolution did not reach,
or at another revision, is unattached and printed with its reason. `Evidence` grew four optional
fields — tool, version, class, probability — that travel together or not at all, and the BOM
carries them as `whence:fingerprint-*` data on the claim. The harness now fails a `verified`
edge that lacks a fingerprint record rather than every `verified` edge, and the test that pinned
"no edge is ever verified" pins "no edge is verified without an evidence file".

DEC-030 records the two rules the implementation forced: evidence attaches only to resolved nodes
at the pinned revision, and an edge the body check already contradicted is not raised by a
fingerprint that says otherwise.

Two converters turn tool output into evidence files — `scripts/fingerprint_evidence.py` for
modelDNA pair records, `scripts/cisco_evidence.py` for the kit's scan results — and each states
its mapping in its docstring. `scripts/measure_fingerprints.py` resolves the fifteen suspects,
applies both files, and records what moved. `docs/eval/fingerprints.md` is the result.

## What the measurement said

modelDNA returned a positive class on all seven comparable positives and an abstaining class on
all thirty comparable negatives, including the two same-shape pairs the body check could not
separate, which it put in its gray zone at p ≈ 0.58. Applied to real resolutions, five declared
edges moved to `verified` and one undeclared grandparent edge was created. One verdict — a
`FINE_TUNE` for AlphaMonarch against the Mistral base — attached nowhere, because the depth-2 graph
stops two hops short of the base it names. That is DEC-030 doing what it says, and it is the right
outcome: the evidence is about two byte sequences, and the graph does not extend to meet it.

The kit's scans were the surprise. Its `Confirmed Match` label is set by an architecture-hash gate
before any weight is read, so a Qwen2.5-7B-Instruct scan returns five `Confirmed Match` siblings
ranked above the documented parent; and it labels `gpt2-medium` a `High-Confidence Match` for a
Llama-3 fine-tune at 0.85. On the one documented derivation both tools scored from weights,
they disagreed — `FINE_TUNE` at 0.9985 against `Weak Match` at 0.685. On the same-shape negative
they agreed to decline. The mapping declared for the kit's file therefore treats `Confirmed Match`
as an abstention, and the file established nothing; its one `establishes` verdict named a
same-family wrong parent and was unattached.

## The finding that was not planned

The phase-4 run over the recorded scenarios read `merge-lineage`'s GGUF as a `QUANTIZED_COPY` of
the one parent its card declares five times, at p = 0.9985, and `NO_MATCH` for the other full-model
parent. The card says six-parent merge; the weights say quantized copy of one. The edge is now
`verified` with the class verbatim and the card's `merged-from` untouched — two records on one
edge, which is exactly the shape DEC-029 asked for and the reason nothing relabels a relation. It
is the first real instance of a declaration that is wrong about the *kind* of relationship rather
than its existence, and it was found by measuring, not by looking for it.

## What was decided and why

- `NO_MATCH` abstains. The GPTQ repack returned `NO_MATCH` at p = 0.13 where the tool's own
  reference results report an abstention; had `NO_MATCH` been mapped to `contradicts`, a true
  quantization would have been refuted. The mapping is in the file for exactly this reason.
- Per-root application. A benchmark-wide file applied to every resolution reported ninety-nine
  unattached verdicts, all of them other suspects' verdicts. The script now applies the verdicts
  whose subject is the root, which is what an operator would hand the tool, and the unattached
  count dropped to the one that means something.
- The subject of a verdict is the artifact fingerprinted, not the name the dataset used.
  `cognitivecomputations/dolphin-2.9-llama3-8b` redirects to `dphn/…`; the bytes read were
  `dphn`'s, so the verdict names `dphn` (DEC-017, again).

## Open

- Six positives are gated and have no fingerprint; a read-only token would close them and is
  outside DEC-009's default run.
- The two-source conflict DEC-029 left open still has no instance: no edge received `establishes`
  from both files.
- Whether a merge whose weights match one parent is a merge is a question for the card's author
  and the merge tool, not for this ledger. It is recorded, not adjudicated.
- The kit was run on four suspects because it downloads full weights; 60 GB for four scans and one
  compare. Its label semantics deserve their own note before a wider run.
