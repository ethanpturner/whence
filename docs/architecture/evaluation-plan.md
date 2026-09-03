# Evaluation plan

**Document version:** 0.1
**Status:** Proposed
**Last updated:** 2026-09-02

## 1. What is being measured

Two axes, reported separately. They answer different questions and combining them into one number
would hide the tradeoff between them.

**Coverage.** How much of a model's true dependency graph does `whence` recover, compared to a
hand-authored gold graph, and compared to the transcription baseline?

**Actionability.** Is the emitted BOM sufficient to answer a real supply-chain question without
returning to the network?

A third measurement runs across both: **abstention quality**. How often does the tool decline to
conclude when declining is correct, and how often does it decline when the answer was available?

## 2. The truth-set rule

**Nothing under `expected/` is supplied to the tool during a run.** A benchmark that hands the
system under test its own answer key measures nothing (DEC-008).

Each scenario is laid out as:

```
benchmarks/<slug>/
  input/           what the tool is given: an artifact reference, and nothing else
  recorded/        captured registry interactions, replayed offline (DEC-009)
  expected/        the authored truth set; never read by the tool
    expected-graph.yaml       every edge that genuinely exists, with its correct provenance class
    expected-absent.yaml      the negative set: relationships that do not exist
    expected-unresolvable.yaml edges that exist but cannot be established from available metadata
  scenario.md      what this scenario measures and why it was chosen
```

The three expected files are not interchangeable and the split is the instrument. `expected-graph`
scores recall. `expected-absent` scores invention. `expected-unresolvable` scores honesty — an edge
listed there is one where the *correct* output is `unverifiable`, and a tool that confidently
resolves it is wrong even though the edge is real.

## 3. The registry

Scenarios are listed in `benchmarks/scenarios.yaml` and are never discovered by scanning
directories. A registry makes the benchmark set a stated fact rather than a fact about the
filesystem.

## 4. Coverage

**Gold graph.** A hand-labelled dependency graph for a sample of published models, authored by
reading repositories directly rather than by running the tool. Target size is fifty models for the
gold subset, drawn to include the hard cases deliberately: merges, multi-hop derivations, quantized
republications, adapters whose base is named only in prose, and models whose declared base has been
deleted.

**Baseline.** The transcription approach — what a model-card reader recovers. The comparison is
head-to-head on the same sample. If `whence` does not substantially exceed it on edge recall, that
is the finding and it gets published as one.

**Metrics.** Edge recall and edge precision against the gold graph, reported per relation type
rather than pooled, because `derives-from` and `trained-on` have very different resolvability and a
pooled number hides that.

## 5. Actionability

Coverage measures whether the graph is right. Actionability measures whether it is useful. Two
replay scenarios, both drawn from documented events:

**Namespace reuse.** Given a BOM emitted before an upstream account was deleted, can a consumer
determine that a dependency is now unpinned and re-registrable? This is the Unit 42 scenario, and
it is the direct test of DEC-002.

**Advisory scope.** Given a BOM and a published advisory affecting a loader package or
configuration path — CVE-2026-4372 is the worked example, since it fires with
`trust_remote_code=False` and therefore will not be caught by the usual reasoning — can a consumer
answer "am I affected?" from the BOM alone?

This is the test most AI-BOMs fail, and it is the one an SBOM actually has to pass.

## 6. Abstention

Scored four ways, never two:

| | Edge exists | Edge does not exist |
|---|---|---|
| **Tool asserts** | correct assertion | **invention** |
| **Tool declines** | **missed** (or correct, if listed in `expected-unresolvable`) | correct abstention |

Reported as abstention precision, abstention recall, and the invention rate. The invention rate is a
headline number, not a footnote: a provenance tool that fabricates plausible edges is worse than no
tool, because it manufactures false confidence in exactly the place an operator has none of their
own.

## 7. Divergence handling

When a run disagrees with a truth set, the divergence is classified before anything is edited:

1. **Tool defect** — the tool is wrong. Fix the tool.
2. **Truth-set defect** — the authored expectation is wrong. Fix the expectation, and record why in
   the scenario's notes.
3. **Genuine ambiguity** — the relationship is not determinable from available evidence. It moves to
   `expected-unresolvable`.

**A run's output is never an argument for changing an expectation.** The classification happens
first, in writing, and the third category is not a disposal route for inconvenient failures.

## 8. What this plan does not measure

- Whether an artifact is malicious. Out of scope (see `project-scope.md` §3).
- Whether weight-level lineage verification works. That is phase two and needs its own plan,
  including an adversarial arm, before any claim is made (DEC-005).
- Performance. Resolution latency is worth recording but is not a success criterion.
