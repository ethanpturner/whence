# merge-lineage

A published mergekit merge, republished as a GGUF quantization:
`QuantFactory/ScaduTorrent1.1-8b-model_stock-GGUF`.

**Why this scenario exists.** A merge is the shape that makes a node-count ceiling necessary
(DEC-007, DEC-024). Depth does not bound it: every parent is one hop away, so a merge naming forty
of them is depth one and forty resolutions. Until this scenario the ceiling was exercised only by a
synthetic test, which is a check that the code does what the code does.

**What the card declares.** Ten `base_model` entries naming **six** distinct artifacts. The
registry's own qualifier tags say `base_model:merge:` for all six, so the relation is `merged-from`
rather than `derives-from` (DEC-015).

**The repetition is not an error and not six dependencies.** `failspy/Llama-3-8B-Instruct-MopeyMule`
is declared five times, because mergekit emits one `base_model` entry per merge slice. That is a
fact about the recipe — how much of the merge that parent accounts for — and the tool records it as
`declared_count: 5` on one edge. Emitting five identical edges, which is what it did before this
scenario was captured, overstates the graph: a reader counting dependencies gets ten where there
are six, and a BOM consumer diffing two of them sees phantom changes.

**Four of the six parents are LoRA adapters**, not full models: `kloodia/lora-8b-math`,
`Blackroot/Llama3-RP-Lora`, `Blackroot/Llama-3-8B-Abomination-LORA`,
`ResplendentAI/Llama3_RP_ORPO_LoRA`. The tool does not second-guess the declared relation — an
adapter genuinely can be merged into weights, so "this is an adapter" does not refute "it was
merged in". What it does instead is keep resolving: at depth two the adapters declare `adapts`
edges of their own, and the graph then shows what the card does not say.

**Those adapters adapt different bases.** `kloodia/lora-8b-math` adapts
`meta-llama/Meta-Llama-3-8B`; `ResplendentAI/Llama3_RP_ORPO_LoRA` adapts
`unsloth/llama-3-8b-bnb-4bit`, a 4-bit quantized variant. Whether merging adapters trained against
different bases is sound is not a question this tool answers. That the graph makes it visible is
the point, and it is visible only because resolution continued past the parents the card names.

**A generation is elided.** This artifact is a GGUF quantization, and the thing it quantizes is a
merge — but the card declares the merge's parents directly, skipping the un-quantized merge itself.
`QuantFactory/ScaduTorrent1.1-8b-model_stock` answers 401, so the intermediate can be neither
confirmed nor pinned. The tool emits no edge to it: a name assembled from a pattern is a guess, and
DEC-010 forbids it however obvious the guess looks.

**The ceiling.** `max_nodes: 10` is deliberately below this graph's fourteen nodes. The run stops,
reports the ceiling, and **names the five branches it did not follow**. It is not marked `partial`:
a ceiling is a stop the tool chose and can state, which is a different thing from a transient
failure that produced no answer.
