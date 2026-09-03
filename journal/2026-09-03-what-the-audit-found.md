# 2026-09-03 — What an audit of the design documents found

Agents read every decision, data-model field and evaluation claim against the code. The pattern
across the findings is one thing, in several places: **an authored expectation that nothing reads
is indistinguishable from a passing one.**

## The scorer was the biggest of them

Six keys were authored across the corpus and read by nothing — `nodes`, `compositions`,
`compositions_absent`, `properties_absent`, `behaviour_absent`, `report` — and all seven scenarios
printed `ok`. `unresolvable` was near-vacuous too: it matched the substring "weight" and let every
subject naming a specific edge through unread.

Scoring them found three defects in `transferred-namespace`, all in the same place and all erasing
the scenario's finding. Following the redirect kept only the resolved target, so the BOM said the
model derives from `stable-diffusion-v1-5/stable-diffusion-v1-5` — an artifact its author never
named. Neither namespace was looked up, so the pair carried no `whence:redirect: cross-namespace`
and no `whence:risk: ownership-boundary-crossed`. And no `unknown` composition was emitted, so a
resolution that established something other than what was asked was presented as complete.

The scenario's own `omissions` block had described the first of these, precisely, as the mistake to
avoid. It had been sitting unread beside the code that made it.

A key in neither the scored nor the prose set now fails the scenario. That is the guard; everything
else was a consequence of not having it.

## Reading prose, and measuring before believing it

DEC-012 and `prose-only-base` were both unimplemented. The scenario's whole point is a card that
declares no `base_model` and says in words that the model is "an instruct fine-tuned version of the
Mistral-7B-v0.2". The README was recorded and never fetched, so the excerpt path, the DEC-018
`unresolvable` branch and the scenario's only real edge were all unexercised.

Implementing it meant writing a pattern over attacker-controlled English, which is the kind of thing
that should not be trusted without a number. `scripts/measure_prose.py` runs it against published
cards. **The first version produced ten claims across 91 cards and all ten were wrong** — "this",
"specialized", "Alibaba" — because the name shape asked only for four alphanumerics after a
derivation verb. Requiring a qualified name or a digit removed all ten.

What survived that came from markdown tables, in two shapes worth naming separately. A quantization
file inventory saying a build was "re-quantized from F16": a precision format read as a model. And a
model-family table saying a *sibling* was fine-tuned from this card's own model: a true sentence
whose arrow points the other way. Both dissolve into one rule — a card states its own lineage in
prose, and a table is a list about several things.

The remaining sample has one imprecise name: a card saying "distilled from Qwen3.8-Max-generated
outputs" yields `Qwen3.8-Max-generated` where the teacher is `Qwen3.8-Max`. It is recorded in
DEC-023 rather than rounded off, because the claim ships with its quotation attached and never
resolves, which is exactly the case the design is for — and it is still not a clean result.

A test found a second thing: the scan was line-based, so a claim wrapped across two lines was
silently missed. That failure looks identical to a card saying nothing, which is the worst shape a
miss can have here.

## Two smaller things, both the same shape as the first

DEC-007 specified a depth ceiling and a node-count ceiling. Only depth was built. Depth does not
bound a graph — one model naming forty parents is depth one and forty requests, which is what a
merge lineage looks like.

And a replay was not reproducible: the report was dated with the wall clock, and a claim's
`bom-ref` was its index in the edge list. Either alone defeats a byte comparison, which is most of
what a recorded scenario is for.

## What is open

Whether the prose pattern holds across the registry rather than three searches, and whether its verb
list misses common phrasings. `merged` is excluded deliberately — a merge names several parents and
a sentence naming one of them is not the lineage — but that is a judgement, not a measurement.
