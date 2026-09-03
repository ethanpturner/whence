# prose-only-base

**What this measures.** The resolution boundary. A model whose derivation is stated only in prose,
where the named base cannot be resolved, and where every available shortcut to a confident answer
is wrong.

**Subject.** `mistralai/Mistral-7B-Instruct-v0.2` at revision
`63a8b081895390a26e140280378bc85ec8bce07a`.

## Why this subject

Four properties line up, and all four are real rather than constructed:

1. **No `base_model` in frontmatter.** The structured field the ecosystem's tooling reads is simply
   absent.
2. **The derivation is in prose, and the name is unqualified.** README line 71: *"The
   Mistral-7B-Instruct-v0.2 Large Language Model (LLM) is an instruct fine-tuned version of the
   Mistral-7B-v0.2."* There is no namespace on that name.
3. **The obvious qualification returns 401, not 404.** `mistralai/Mistral-7B-v0.2` answers 401 to an
   unauthenticated request. Without credentials, that response does not distinguish "no such
   repository" from "exists and you are not permitted to see it". This is better for the benchmark
   than a clean 404 would be, because the honest answer is genuinely unavailable rather than merely
   negative.
4. **A decoy sits in the frontmatter.** `new_version: mistralai/Mistral-7B-Instruct-v0.3` is a
   successor pointer. It names a model, it is structured, and it is not lineage — the arrow runs
   the other way.

## The three ways to fail

The expected graph holds exactly one edge. Everything interesting is in the other two files.

**Guess the version.** `mistralai/Mistral-7B-v0.1` exists and is one character from the name in the
prose. Resolving to it is the most likely failure in this scenario and is straightforwardly
invention.

**Follow the decoy.** Treating every frontmatter model reference as ancestry produces a
`derives-from` edge to v0.3 with the direction reversed.

**Report absence.** Concluding that `mistralai/Mistral-7B-v0.2` does not exist, on the strength of a
401. This is the subtlest failure and the one worth caring most about: it converts a limit of the
instrument into a claim about the world, which is the exact error DEC-001 exists to prevent. It is
recorded in `expected-absent.yaml` as a negative assertion rather than an edge, because a run can
emit a perfect edge list and still fail by saying this in prose.

## What the correct output looks like

One `requires-package` edge. One `derives-from` edge with provenance `unresolvable`, verdict
`unverifiable`, the declared name `Mistral-7B-v0.2` retained verbatim, and the README sentence
retained as evidence with its locator. Nothing about v0.1, nothing about v0.3, and no statement
either way about whether `mistralai/Mistral-7B-v0.2` exists.

That output is less informative than what a transcription tool would produce, and it is correct. A
tool that resolves this scenario confidently is not better; it is wrong in a way its user cannot
detect.

## Open question this scenario raised

**The evidence excerpt is untrusted text and it has to reach the report.** — *resolved by DEC-012.*
Without the quoted prose an `unresolvable` edge is an assertion with nothing behind it, and a
reader cannot audit the tool's refusal to resolve. But a model card is content published by anyone
with an account. The two requirements are compatible only if the excerpt is data at every point:
bounded, delimited where rendered, never in a log record, never parsed for meaning.
