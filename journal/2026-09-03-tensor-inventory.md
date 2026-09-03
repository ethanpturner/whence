# 2026-09-03 — A fourth structural signal, rejected on measurement

Tried the obvious next increment after DEC-020 and did not ship it.

## The idea, and why it looked good

`safetensors` carries a JSON header listing every tensor's name, dtype and shape, and it is readable
with a byte-range request. **32 KB retrieves the full 290-tensor inventory of a 1 GB model.** Sharded
models publish an index that lists every tensor name outright, needing no range request at all.

So a far stronger fingerprint than configuration, at almost no cost, and much closer to the
weight-level comparison DEC-005 defers. I expected to ship it.

## What twenty real pairs said

Fourteen comparable, three differing — and all three were legitimate derivations:

- `Qwen3-0.6B` has one extra tensor, `lm_head.weight`: an **untied output head**, normal for an
  instruct variant.
- `Qwen3-Embedding-0.6B` differs on all 310, and the diff is a **`model.` prefix**. A wrapper class
  nests the module differently; the tensors are otherwise identical.
- `whisper-large-v3-turbo` has 672 fewer tensors: a **pruned decoder**, fewer layers by design, and
  correctly declared as derived from the full model.

21% false positives on real declared fine-tunes. The first configuration field set managed 26%.

## The intuition was wrong in three independent ways

"A fine-tune preserves the tensor inventory" fails because fine-tunes **add** tensors when a head is
untied, wrappers **rename** them wholesale, and distilled or pruned variants **remove** whole layers
while remaining honest derivations.

Any one of those would have been enough. I had thought of none of them.

## Why no weaker version

Normalising prefixes and comparing shapes of commonly-named tensors would fix the second case and
part of the first. At that point it is the configuration check with more steps and more places to go
wrong — DEC-020 already compares the dimensions those shapes derive from, more cheaply, at a
measured zero false-positive rate. A second path to the same conclusion buys nothing and doubles the
surface.

## The tally

Four attempts at a structural signal, three rejected on measurement:

1. config including `architectures` and `vocab_size` — 26% false positives
2. config body fields, absent treated as differing — one false positive, from a nested config
3. config body fields, comparing only fields present in both — **shipped**, 0 false positives
4. tensor inventory — 21% false positives, rejected here

Each rejected version was plausible, internally coherent, and wrong about real published models in a
way only contact with them revealed. The cost of finding out was minutes each time; the cost of
shipping any of them would have been a tool that cries wolf on a fifth of its inputs.

## Open next

- Weight-level comparison of tensor *values* is still unbuilt and DEC-005's bound still stands. This
  closes the cheap approximation, not the real thing.
