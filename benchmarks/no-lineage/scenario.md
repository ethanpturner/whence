# no-lineage

`google-bert/bert-base-uncased`: a model with no upstream artifact.

**Why this scenario exists.** Every other scenario grades what the tool says when there *is*
something to say. This one grades what it says when there is not, and that is the harder discipline:
a provenance tool with nothing to report has no output to be impressed by, and the temptation is to
find something.

**The graph is not empty, and that is the point.** The card declares two training corpora and a
library, so the tool emits three edges — `trained-on bookcorpus`, `trained-on wikipedia`,
`requires-package transformers`. What it emits is **no derivation edge at all**: no `derives-from`,
no `quantized-from`, no `distilled-from`, no `adapts`. "This model has no ancestor" and "nothing is
known about this model" are different statements, and a graph that collapsed them would make the
first unsayable.

**The datasets resolve to nothing, and stay.** `bookcorpus` and `wikipedia` are bare names with no
namespace, so `parse_ref` refuses them (DEC-010) and the edges are `unresolvable`. They are still
emitted: the card asserts them, and dropping an assertion because its target could not be pinned
would silently shorten the graph. `huggingface/wikipedia` and `wikimedia/wikipedia` both exist and
neither is what the card said.

**The prose trap.** The card contains derivation verbs — "can be fine-tuned on a downstream task",
"fine-tuned versions of a task that interests you". Both describe **descendants**, not ancestors: the
arrow points away from this model, and a scanner that reads any derivation verb as lineage emits an
edge backwards. It also says the model was "pretrained on a large corpus of English data in a
self-supervised fashion", which names an activity and a corpus and no parent artifact.

**What a reader should be able to conclude.** That bert-base-uncased asserts no ancestry, and that
the tool looked. Not that it has none — a model trained from scratch and a model whose publisher
omitted its base look identical from here, and DEC-001 keeps them on the same verdict.
