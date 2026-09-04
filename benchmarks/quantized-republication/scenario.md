# quantized-republication

`PrunaAI/LoneStriker-DeepSeek-R1-Distill-Llama-70B-8.0bpw-h8-exl2-GGUF-smashed`: a GGUF
requantization of an EXL2 quantization of a distillation, across three namespaces.

**Why this scenario exists.** It is the hardest case any weight-level method will ever face
(DEC-005). Each step is lossy and irreversible: a distillation shares no tensors with its teacher at
all, an 8-bit EXL2 quantization discards precision, and requantizing that into GGUF discards more.
No digest matches anything upstream, and no structural check can bridge it — so whatever phase two
eventually verifies, it will not verify this. The chain is provenance metadata or it is nothing.

**And the metadata breaks at the second hop.** PrunaAI declares its base, with the registry's own
`base_model:quantized:` qualifier, so the first link is stated. `LoneStriker/…-exl2` declares
**nothing** — no `base_model`, no qualifier tag. The chain that the artifact's own name spells out in
full stops one step in.

**The invention trap is the strongest in the corpus.** The string
`DeepSeek-R1-Distill-Llama-70B` is right there in the repository name;
`deepseek-ai/DeepSeek-R1-Distill-Llama-70B` exists and answers 200; and the guess would be correct.
A tool that parses repository names to repair broken chains produces a graph that is right here and
wrong wherever a name is aspirational, a coincidence, or a lie — and nothing in the output would
distinguish the cases. DEC-010 forbids it, and this is where the forbidding costs the most.

**The copied card, and the tool's weakest output.** `LoneStriker/…-exl2` republishes DeepSeek's model
card verbatim, which is normal practice when publishing a quantization. That card contains
DeepSeek's own sentence about *their* family — "we have open-sourced DeepSeek-R1-Zero, DeepSeek-R1,
and six dense models distilled from DeepSeek-R1" — and the prose scanner reads it as a claim about
this artifact, emitting `LoneStriker/…-exl2 --distilled-from--> DeepSeek-R1`.

That edge is *approximately* true and *specifically* wrong. This artifact is a quantization of a
distillation, not a distillation; the sentence's subject is DeepSeek describing six models, one of
which this is a quantized copy of. The edge is emitted with `unresolvable` provenance,
`unverifiable` verdict, and the sentence attached, so a reader sees the family prose it came from —
which is the mitigation available, not a fix.

Narrowing the scanner to avoid it was tried and measured, and the results are in DEC-028: every
signal that suppresses this case also suppresses the six official DeepSeek distillations, which
carry the identical sentence on their own cards and are correct there. The limitation is recorded
rather than engineered around.

**What the chain is worth.** Two declared links out of three, one of them broken, and a prose edge
that is honest about being prose. That is a poor provenance record, and reporting it as one is the
job. A tool that filled the gap from the repository name would have produced a complete, plausible,
unverifiable chain — which is exactly the artifact an attacker republishing someone else's weights
under a familiar name would want it to produce.
